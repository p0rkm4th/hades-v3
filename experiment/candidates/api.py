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
MODEL_REQUEST_TIMEOUT_SECONDS = float(os.environ.get("MODEL_REQUEST_TIMEOUT_SECONDS", "50"))
MAX_MODEL_REQUESTS = 6
MAX_TOOL_CALLS = 4
MAX_COMPLETION_TOKENS = 1024
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
write memory unless explicitly asked. For an explicitly requested correction to an existing
memory, use memory_correct with a query, the exact expected current value, and the new value.
Do not use memory_write for a correction. Claim success only when the returned canonical
value matches the requested value. Read tool results as evidence, and report unknown, stale or unavailable
data honestly. Never invent factual values in an update or example; use placeholders when
the fixture has no value. For changes, use the compound tool and report success
only when its result says CONFIRMED. Before a shopping-list change, call inventory_read in
this turn unless canonical product names were already returned in this turn. Use those names
exactly. If a name is rejected, make no success claim; read inventory and retry only with a
matching canonical name. Never invent approval IDs or repeat an uncertain operation. Keep
user-facing language natural; never ask for fixture-internal IDs. Treat personal-continuity
questions as memory questions even when the user does not explicitly mention memory: when
asked what the user prefers, previously requested, decided, or uses as a standing choice,
retrieve relevant memory with memory_search when the exact key is unknown, or memory_read
when it is known, before answering. Do not infer a saved preference from the current
conversation alone. Use only returned memories; if no relevant memory is found, say so after
searching. Memory is not a source of live operational truth. For code work, inspect the
repository, run its tests, inspect the result and commit only when asked.
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
        elif name in {"workspace_exec", "commitment_submit", "shopping_list_change"}:
            schema = dict(schema)
            schema["properties"] = {k: v for k, v in schema["properties"].items() if k != "task_id"}
            schema["required"] = [k for k in schema.get("required", []) if k != "task_id"]
        visible.append({"name": name, "description": tool["description"], "parameters": schema})
    return visible


VISIBLE_TOOLS = tool_contracts()


def gateway_call(name: str, arguments: dict, token: str, task_id: str, evidence: list | None = None):
    contract = next((item for item in TOOLS if item["name"] == name), None)
    if contract is None:
        raise ValueError("unknown shared tool")
    path = contract["path"]
    if name == "memory_read":
        path = path.replace("{key}", urllib.parse.quote(str(arguments.get("key", "")), safe=""))
    if name == "memory_search":
        path += "?" + urllib.parse.urlencode({"q": str(arguments.get("query", ""))})
    if name == "task_resume":
        path = path.replace("{task_id}", urllib.parse.quote(task_id, safe=""))
    if name in {"task_checkpoint", "commitment_reconcile"}:
        path = path.replace("{task_id}", urllib.parse.quote(task_id, safe=""))
        if name == "commitment_reconcile":
            effect_id = urllib.parse.quote(str(arguments.get("effect_id", "")), safe="")
            path = path.replace("{effect_id}", effect_id)
    payload = dict(arguments)
    if name in {"workspace_exec", "commitment_submit", "shopping_list_change"}:
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
            observation = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            observation = {"http_status": exc.code, **json.loads(exc.read())}
        except json.JSONDecodeError:
            observation = {"http_status": exc.code, "error": "tool request failed"}
    if evidence is not None and name in {"memory_search", "memory_read", "memory_correct"}:
        item = {
            "tool": name,
            "status": "error" if observation.get("http_status") else "ok",
        }
        if name == "memory_search":
            memories = observation.get("memories", [])
            item["result_count"] = len(memories)
            item["memory_keys"] = [row.get("memory_key") for row in memories]
        else:
            item["memory_key"] = observation.get("memory_key")
        evidence.append(item)
    return observation


def chat_openai(messages: list[dict], tools_enabled: bool, token: str, task_id: str, tools_used: list[str]):
    history = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    tool_trace = tools_used
    tool_evidence = []
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0}
    started = time.monotonic()
    for _ in range(MAX_MODEL_REQUESTS):
        body = {
            "model": MODEL_NAME, "messages": history, "temperature": 0,
            "max_tokens": MAX_COMPLETION_TOKENS, "stream": False,
        }
        if tools_enabled:
            body["tools"] = [{"type": "function", "function": t} for t in VISIBLE_TOOLS]
            body["tool_choice"] = "auto"
        request = urllib.request.Request(
            MODEL_URL.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer no-secret"},
        )
        with urllib.request.urlopen(request, timeout=MODEL_REQUEST_TIMEOUT_SECONDS) as response:
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
                "tool_evidence": tool_evidence,
                "usage": usage_totals, "duration_ms": round((time.monotonic() - started) * 1000),
            }
        if len(tool_trace) + len(calls) > MAX_TOOL_CALLS:
            raise RuntimeError("tool-call limit reached before dispatch")
        for call in calls:
            function = call["function"]
            args = json.loads(function.get("arguments") or "{}")
            tool_trace.append(function["name"])
            observation = gateway_call(function["name"], args, token, task_id, tool_evidence)
            history.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(observation)})
    raise RuntimeError("model request limit reached before a final response")


def chat_pydantic(messages: list[dict], token: str, task_id: str, tools_used: list[str]):
    from pydantic_ai import Agent, FunctionToolset, Tool, UsageLimits
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    started = time.monotonic()
    trace = tools_used
    tool_evidence = []
    toolset = FunctionToolset()
    for spec in VISIBLE_TOOLS:
        name = spec["name"]
        def invoke(_name=name, **kwargs):
            trace.append(_name)
            return gateway_call(_name, kwargs, token, task_id, tool_evidence)
        toolset.add_tool(Tool.from_schema(
            function=invoke, name=name, description=spec["description"],
            json_schema=spec["parameters"],
        ))
    provider = OpenAIProvider(base_url=MODEL_URL, api_key="no-secret")
    model = OpenAIChatModel(MODEL_NAME, provider=provider)
    agent = Agent(model, system_prompt=SYSTEM_PROMPT, toolsets=[toolset], retries=1)
    prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    result = agent.run_sync(
        prompt,
        model_settings={
            "timeout": MODEL_REQUEST_TIMEOUT_SECONDS,
            "temperature": 0,
            "max_tokens": MAX_COMPLETION_TOKENS,
        },
        usage_limits=UsageLimits(
            request_limit=MAX_MODEL_REQUESTS,
            tool_calls_limit=MAX_TOOL_CALLS,
        ),
    )
    usage = result.usage
    return {
        "text": str(result.output), "tool_calls": trace,
        "tool_evidence": tool_evidence,
        "usage": {"prompt_tokens": usage.input_tokens, "completion_tokens": usage.output_tokens},
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def chat_hermes(messages: list[dict], token: str, task_id: str, tools_used: list[str]):
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
        with urllib.request.urlopen(request, timeout=MODEL_REQUEST_TIMEOUT_SECONDS) as response:
            value = json.loads(response.read())
        usage = value.get("usage") or {}
        trace = [line for line in trace_file.read_text().splitlines() if line]
        tools_used.extend(trace)
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


def transition_task(
    token: str, task_id: str, state: str, tools_used: list[str], error_type: str | None = None
):
    current = gateway_call("task_resume", {}, token, task_id)
    if current.get("http_status") or current.get("task_id") != task_id:
        raise RuntimeError("task state could not be read")
    checkpoint = dict(current.get("checkpoint") or {})
    candidate_turn = {"state": state, "tools": tools_used}
    if error_type is not None:
        candidate_turn["error_type"] = error_type
        candidate_turn["operator_review_required"] = True
        candidate_turn["effect_outcome_uncertain"] = True
    checkpoint["candidate_turn"] = candidate_turn
    updated = gateway_call(
        "task_checkpoint", {"state": state, "checkpoint": checkpoint}, token, task_id
    )
    if updated.get("http_status") or updated.get("state") != state:
        raise RuntimeError("task state could not be saved")
    return updated


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
        active_token = None
        active_task_id = None
        candidate = None
        tools_used = []
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
            else:
                transition_task(token, task_id, "RUNNING", [])
            active_token = token
            active_task_id = task_id
            if candidate == "pydantic":
                result = chat_pydantic(messages, token, task_id, tools_used)
            elif candidate == "hermes":
                result = chat_hermes(messages, token, task_id, tools_used)
            else:
                result = chat_openai(messages, True, token, task_id, tools_used)
            current = gateway_call("task_resume", {}, token, task_id)
            if current.get("http_status") or current.get("task_id") != task_id:
                raise RuntimeError("task state could not be read")
            if current.get("state") in {"RUNNING", "COMPLETED"}:
                transition_task(token, task_id, "COMPLETED", result.get("tool_calls", []))
            else:
                raise RuntimeError("candidate turn ended in an unexpected task state")
            result["task_id"] = task_id
            return self.send_json(200, result)
        except Exception as exc:
            if candidate == "hermes" and active_token:
                _, trace_file = HERMES_STATE[active_token]
                try:
                    if trace_file.exists():
                        tools_used.extend(
                            line for line in trace_file.read_text().splitlines()
                            if line and line not in tools_used
                        )
                except OSError as trace_exc:
                    print(f"Could not read Hermes tool trace: {type(trace_exc).__name__}")
            if active_token and active_task_id:
                try:
                    transition_task(
                        active_token,
                        active_task_id,
                        "FAILED",
                        tools_used,
                        type(exc).__name__,
                    )
                except Exception as checkpoint_exc:
                    print(f"Could not close failed task: {type(checkpoint_exc).__name__}")
            print(f"Candidate request rejected: {type(exc).__name__}: {exc}")
            failure = {"error": f"candidate request failed: {type(exc).__name__}"}
            if active_task_id:
                failure["task_id"] = active_task_id
            return self.send_json(502, failure)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
