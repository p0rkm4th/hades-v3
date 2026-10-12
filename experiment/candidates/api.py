from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TOOLS = json.loads((ROOT.parent / "contracts" / "tools.json").read_text())["tools"]
GATEWAY = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
MODEL_URL = os.environ.get("MODEL_URL", "http://model-server-8b:8080/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen3-8B")
MAX_BODY = 128 * 1024
HERMES_ENDPOINT = {
    "fixture-token-amber": ("http://hermes-amber:8642/v1/chat/completions", "fixture-hermes-amber"),
    "fixture-token-cobalt": ("http://hermes-cobalt:8642/v1/chat/completions", "fixture-hermes-cobalt"),
}
HERMES_STATE = {
    "fixture-token-amber": (Path("/hermes/amber-task/current"), Path("/hermes/amber-trace/tool-trace.jsonl")),
    "fixture-token-cobalt": (Path("/hermes/cobalt-task/current"), Path("/hermes/cobalt-trace/tool-trace.jsonl")),
}
HERMES_LOCKS = {token: threading.Lock() for token in HERMES_ENDPOINT}
SYSTEM_PROMPT = """You are a prototype assistant using the supplied shared HADES fixture tools.
Use live fixture tools for current inventory, shopping lists and infrastructure. Do not
write memory unless explicitly asked. Read tool results as evidence, and report unknown,
stale or unavailable data honestly. For changes, use the compound tool and report success
only when its result says CONFIRMED. Never invent approval IDs or repeat an uncertain
operation. Keep user-facing language natural; never ask for fixture-internal IDs. For code
work, inspect the repository, run its tests, inspect the result and commit only when asked.
"""


def tool_contracts():
    visible = []
    for tool in TOOLS:
        name = tool["name"]
        schema = tool.get("input", {"type": "object", "properties": {}, "additionalProperties": False})
        if name == "task_start":
            continue
        if name == "task_resume":
            schema = {"type": "object", "properties": {}, "additionalProperties": False}
        elif name == "memory_read":
            schema = {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"], "additionalProperties": False}
        elif name == "commitment_reconcile":
            schema = {"type": "object", "properties": {"effect_id": {"type": "string", "format": "uuid"}}, "required": ["effect_id"], "additionalProperties": False}
        elif name == "task_checkpoint":
            schema = {
                "type": "object", "properties": schema["properties"],
                "required": ["state", "checkpoint"], "additionalProperties": False,
            }
        elif name in {"workspace_exec", "commitment_submit"}:
            schema = dict(schema)
            schema["properties"] = {k: v for k, v in schema["properties"].items() if k != "task_id"}
            schema["required"] = [k for k in schema["required"] if k != "task_id"]
        visible.append({"name": name, "description": tool["description"], "parameters": schema})
    return visible


VISIBLE_TOOLS = tool_contracts()


def gateway_call(name: str, arguments: dict, token: str, task_id: str):
    contract = next((item for item in TOOLS if item["name"] == name), None)
    if contract is None:
        raise ValueError("unknown shared tool")
    path = contract["path"]
    if name == "memory_read":
        path = path.replace("{key}", urllib.parse.quote(str(arguments.get("key", "")), safe=""))
    if name == "task_resume":
        path = path.replace("{task_id}", urllib.parse.quote(task_id, safe=""))
    if name in {"task_checkpoint", "commitment_reconcile"}:
        path = path.replace("{task_id}", urllib.parse.quote(task_id, safe=""))
        if name == "commitment_reconcile":
            effect_id = urllib.parse.quote(str(arguments.get("effect_id", "")), safe="")
            path = path.replace("{effect_id}", effect_id)
    payload = dict(arguments)
    if name in {"workspace_exec", "commitment_submit"}:
        payload["task_id"] = task_id
    if name in {"task_checkpoint", "commitment_reconcile"}:
        payload = {} if name == "commitment_reconcile" else payload
    data = json.dumps(payload).encode() if contract["method"] == "POST" else None
    req = urllib.request.Request(
        GATEWAY + path, data=data, method=contract["method"],
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            return {"http_status": exc.code, **json.loads(exc.read())}
        except json.JSONDecodeError:
            return {"http_status": exc.code, "error": "tool request failed"}


def chat_openai(messages: list[dict], tools_enabled: bool, token: str, task_id: str):
    history = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    tool_trace = []
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0}
    started = time.monotonic()
    for _ in range(8):
        body = {"model": MODEL_NAME, "messages": history, "temperature": 0, "stream": False}
        if tools_enabled:
            body["tools"] = [{"type": "function", "function": t} for t in VISIBLE_TOOLS]
            body["tool_choice"] = "auto"
        request = urllib.request.Request(
            MODEL_URL.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer no-secret"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read())
        usage = result.get("usage", {})
        usage_totals["prompt_tokens"] += usage.get("prompt_tokens", 0)
        usage_totals["completion_tokens"] += usage.get("completion_tokens", 0)
        choice = result["choices"][0]["message"]
        history.append(choice)
        calls = choice.get("tool_calls") or []
        if not calls:
            return {
                "text": choice.get("content") or "", "tool_calls": tool_trace,
                "usage": usage_totals, "duration_ms": round((time.monotonic() - started) * 1000),
            }
        for call in calls:
            function = call["function"]
            args = json.loads(function.get("arguments") or "{}")
            tool_trace.append(function["name"])
            observation = gateway_call(function["name"], args, token, task_id)
            history.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(observation)})
    return {
        "text": "I could not complete this turn within the tool-call limit.",
        "tool_calls": tool_trace, "usage": usage_totals,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def chat_pydantic(messages: list[dict], token: str, task_id: str):
    from pydantic_ai import Agent, FunctionToolset, Tool
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    started = time.monotonic()
    trace = []
    toolset = FunctionToolset()
    for spec in VISIBLE_TOOLS:
        name = spec["name"]
        def invoke(_name=name, **kwargs):
            trace.append(_name)
            return gateway_call(_name, kwargs, token, task_id)
        toolset.add_tool(Tool.from_schema(
            function=invoke, name=name, description=spec["description"],
            json_schema=spec["parameters"],
        ))
    provider = OpenAIProvider(base_url=MODEL_URL, api_key="no-secret")
    model = OpenAIChatModel(MODEL_NAME, provider=provider)
    agent = Agent(model, system_prompt=SYSTEM_PROMPT, toolsets=[toolset], retries=1)
    prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    result = agent.run_sync(prompt)
    usage = result.usage
    return {
        "text": str(result.output), "tool_calls": trace,
        "usage": {"prompt_tokens": usage.input_tokens, "completion_tokens": usage.output_tokens},
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def chat_hermes(messages: list[dict], token: str, task_id: str):
    endpoint, api_key = HERMES_ENDPOINT[token]
    task_file, trace_file = HERMES_STATE[token]
    with HERMES_LOCKS[token]:
        task_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temp_task_file = task_file.with_suffix(".tmp")
        temp_task_file.write_text(task_id)
        temp_task_file.replace(task_file)
        trace_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        trace_file.write_text("")
        payload = {"model": MODEL_NAME, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages]}
        started = time.monotonic()
        request = urllib.request.Request(
            endpoint, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=600) as response:
            value = json.loads(response.read())
        usage = value.get("usage") or {}
        trace = [line for line in trace_file.read_text().splitlines() if line]
    message = value["choices"][0]["message"]
    content = message.get("content") or ""
    return {
        "text": content if isinstance(content, str) else json.dumps(content),
        "tool_calls": trace,
        "usage": {"prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0)},
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def start_task(token: str, goal: str):
    data = json.dumps({"goal": goal[:1000]}).encode()
    req = urllib.request.Request(
        GATEWAY + "/v1/tasks", data=data, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path.split('?')[0]}")

    def send_json(self, status: int, value: dict):
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            return self.send_json(200, {"status": "ok"})
        if self.path == "/":
            page = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            return self.wfile.write(page)
        return self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/turn":
            return self.send_json(404, {"error": "not found"})
        try:
            if int(self.headers.get("Content-Length", "0")) > MAX_BODY:
                return self.send_json(413, {"error": "request too large"})
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            messages = body["messages"]
            if not isinstance(messages, list) or not messages or len(messages) > 24:
                raise ValueError("messages must contain 1 to 24 entries")
            token = body.get("user_token")
            if token not in {"fixture-token-amber", "fixture-token-cobalt"}:
                return self.send_json(401, {"error": "known synthetic user required"})
            candidate = body.get("candidate", "lean")
            if candidate not in {"lean", "pydantic", "hermes"}:
                return self.send_json(400, {"error": "unknown candidate"})
            user_messages = [m for m in messages if m.get("role") == "user"]
            task_id = body.get("task_id")
            if not task_id:
                task_id = start_task(token, str(user_messages[0]["content"]))["task_id"]
            if candidate == "pydantic":
                result = chat_pydantic(messages, token, task_id)
            elif candidate == "hermes":
                result = chat_hermes(messages, token, task_id)
            else:
                result = chat_openai(messages, True, token, task_id)
            result["task_id"] = task_id
            return self.send_json(200, result)
        except (KeyError, TypeError, ValueError, urllib.error.URLError) as exc:
            print(f"Candidate request rejected: {type(exc).__name__}: {exc}")
            return self.send_json(502, {"error": f"candidate request failed: {type(exc).__name__}"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
