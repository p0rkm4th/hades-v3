from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
try:
    from task_lifecycle import decide_turn_finalization
except ModuleNotFoundError:
    from contracts.task_lifecycle import decide_turn_finalization


ROOT = Path(__file__).resolve().parent
TOOLS = json.loads((ROOT.parent / "contracts" / "tools.json").read_text())["tools"]
GATEWAY = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
MODEL_URL = os.environ.get("MODEL_URL", "http://model-server-8b:8080/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen3-8B")
MODEL_API_KEY = os.environ.get("MODEL_API_KEY", "no-secret")
MODEL_API_KEYS = {
    "pydantic": MODEL_API_KEY,
    "lean": os.environ.get("MODEL_API_KEY_LEAN", "no-secret"),
}
MODEL_REQUEST_TIMEOUT_SECONDS = float(os.environ.get("MODEL_REQUEST_TIMEOUT_SECONDS", "50"))
MAX_MODEL_REQUESTS = int(os.environ.get("MODEL_MAX_REQUESTS", "16"))
MAX_TOOL_CALLS = 18
MAX_COMPLETION_TOKENS = int(os.environ.get("MODEL_MAX_TOKENS", "1024"))
MODEL_TEMPERATURE = float(os.environ.get("MODEL_TEMPERATURE", "0"))
ORCHESTRATOR_SECRET = os.environ.get("ORCHESTRATOR_SECRET", "")
MAX_BODY = 128 * 1024
_PROVIDER_DIAGNOSTICS = (
    re.compile(r"\b(?:model|inference|llm) provider\b.{0,100}\b(?:rate[- ]?limit(?:ing|ed)?|retry|error|unavailable|failed)\b", re.I),
    re.compile(r"\bprovider\b.{0,100}\b(?:rate[- ]?limit(?:ing|ed)?|429|too many requests|temporarily unavailable)\b", re.I),
    re.compile(r"\b(?:rate[- ]?limit(?:ing|ed)?)\b.{0,100}\b(?:provider|retry|try again|request)\b", re.I),
)


class ProviderFailure(RuntimeError):
    """A provider/runtime diagnostic must not be treated as a final answer."""


def provider_diagnostic(text: str) -> bool:
    return isinstance(text, str) and any(pattern.search(text) for pattern in _PROVIDER_DIAGNOSTICS)


HERMES_ENDPOINT = {
    "fixture-token-amber": (os.environ.get("HERMES_AMBER_ENDPOINT", "http://hermes-amber:8642/v1/chat/completions"), "fixture-hermes-amber"),
    "fixture-token-cobalt": (os.environ.get("HERMES_COBALT_ENDPOINT", "http://hermes-cobalt:8642/v1/chat/completions"), "fixture-hermes-cobalt"),
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
matching canonical name. For consequential external operations, use commitment_submit only
with a current exact-effect approval issued by the protected operator. Without one, say the
action is awaiting approval; do not claim the capability is unavailable, and continue any
harmless authorized work in the same request. Never invent approval IDs or repeat an
uncertain operation. If commitment_submit reports a missing or mismatched approval, explain
that the external action was not submitted and still needs protected approval; do not ask
the user for internal target or approval IDs, and do not retry without a newly issued exact
approval. Keep user-facing language natural; never ask for fixture-internal IDs.
If commitment_submit returns state QUARANTINED or reconcile_required=true, call
commitment_reconcile with its returned effect_id before reporting the outcome. Never submit
the commitment again after an uncertain acknowledgment, and claim confirmation only when
reconciliation returns CONFIRMED.
Treat personal-continuity
questions as memory questions even when the user does not explicitly mention memory: when
asked what the user prefers, previously requested, decided, or uses as a standing choice,
retrieve relevant memory with memory_search when the exact key is unknown, or memory_read
when it is known, before answering. Do not infer a saved preference from the current
conversation alone. Use only returned memories; if no relevant memory is found, say so after
searching. Memory is not a source of live operational truth. For code work, use
workspace_exec runs one shell command in the root of the already checked-out repository.
Do not clone, fetch, pull or push external remotes; workspace network egress is
disabled. Inspect the existing files, run their tests, inspect the result and
diff, and commit only when asked. Plan a short sequence of commands; batch
related read-only checks into one bounded command and avoid repeated inspections
or temporary patch files when a direct edit is practical. After the requested
change, tests, final diff review, and commit are complete, stop using tools and
report the verified outcome. For durable multi-step work, call task_resume before
continuing so you can use the canonical task identity and checkpoint. Persist
progress with task_checkpoint using state RUNNING and a concise, nonempty checkpoint
that records verified completed steps and remaining steps. Candidate agents cannot
suspend canonical work: WAITING is an orchestrator-owned state for external
interruption, missing input, approval, or dependency. Do not claim a checkpoint was
saved unless the tool returns successfully. On a later turn, read the saved
checkpoint, verify workspace state, and continue the same task; never claim
completion from a prior task summary alone.
Every checkpoint must include `summary` (nonempty string), `completed` (string list),
and `pending` (string list); retain any additional task-specific fields.
When pending steps are already authorized and executable with available tools, do
them in the current turn instead of asking whether to continue or merely restating
the plan. The orchestrator manages WAITING state; candidates should report a blocker
in the checkpoint and leave the task RUNNING or FAILED.
After all requested steps are independently verified, persist task_checkpoint with
state COMPLETED, a concise summary, the completed step list, and an empty pending list.
Do not leave a finished task RUNNING.
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
    if (name == "task_checkpoint" and arguments.get("state") == "WAITING"
            and "_orchestrator_finalization" not in arguments):
        return {"http_status": 400, "error": "WAITING is an orchestrator-owned task state"}
    if (name == "task_checkpoint" and arguments.get("state") == "COMPLETED"
            and "_orchestrator_finalization" not in arguments):
        claim = arguments.get("checkpoint") or {}
        if evidence is not None:
            evidence.append({"kind": "completion_claim", "checkpoint": claim})
        return {"state": "RUNNING", "completion_claim_recorded": True}
    if name == "task_checkpoint" and arguments.get("state") == "RUNNING" and evidence is not None:
        evidence.append({"kind": "progress_checkpoint", "checkpoint": arguments.get("checkpoint") or {}})
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
    if name in {"workspace_exec", "commitment_submit", "shopping_list_change",
                "memory_write", "memory_correct"}:
        payload["task_id"] = task_id
    if name in {"task_checkpoint", "commitment_reconcile"}:
        payload = {} if name == "commitment_reconcile" else payload
    data = json.dumps(payload).encode() if contract["method"] == "POST" else None
    req = urllib.request.Request(
        GATEWAY + path, data=data, method=contract["method"],
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    if name == "task_checkpoint" and any(
        key in arguments for key in ("_orchestrator_finalization", "_orchestrator_resume")
    ):
        if not ORCHESTRATOR_SECRET:
            raise RuntimeError("orchestrator credential is not configured")
        req.add_header("X-Hades-Orchestrator", ORCHESTRATOR_SECRET)
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            observation = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            observation = {"http_status": exc.code, **json.loads(exc.read())}
        except json.JSONDecodeError:
            observation = {"http_status": exc.code, "error": "tool request failed"}
    if name == "commitment_submit" and observation.get("http_status") in {400, 403}:
        status = observation["http_status"]
        observation = {
            "http_status": status,
            "error": (
                "The protected service did not receive this commitment. A complete exact-effect "
                "request and current operator approval are required. Do not ask the user for "
                "internal target or approval IDs, and do not retry without a newly issued approval. "
                "Continue other harmless authorized work."
            ),
        }
    if (name == "task_resume" and not observation.get("http_status")
            and observation.get("state") in {"RUNNING", "WAITING"}
            and (observation.get("checkpoint") or {}).get("pending")):
        observation["continuation_directive"] = (
            "This task is active and has authorized pending steps. Verify the workspace, "
            "then perform the next pending step now. Do not pause just to restate the plan; "
            "use WAITING only for a genuine missing input, approval, or external dependency."
        )
    if evidence is not None and name not in {"task_resume", "task_checkpoint"}:
        item = {
            "kind": "tool_evidence",
            "tool": name,
            "status": "error" if observation.get("http_status") else "ok",
            "http_status": observation.get("http_status", 200),
        }
        for key in ("state", "effect_id", "exit_code", "verified_after", "reconcile_required"):
            if key in observation:
                item[key] = observation[key]
        if name in {"memory_write", "memory_correct"} and item["status"] == "ok":
            item["state"] = "CONFIRMED"
        if name == "commitment_submit" and observation.get("http_status") in {400, 403}:
            item["approval_pending"] = True
        if observation.get("state") in {"QUARANTINED", "UNRESOLVED", "DISPATCHED"} or observation.get("reconcile_required"):
            item["uncertain"] = True
        if name in {"memory_search", "memory_read", "memory_correct", "memory_write"}:
            if name == "memory_search":
                memories = observation.get("memories", [])
                item["result_count"] = len(memories)
                item["memory_keys"] = [row.get("memory_key") for row in memories]
            else:
                item["memory_key"] = observation.get("memory_key")
        evidence.append(item)
    return observation


def chat_openai(messages: list[dict], tools_enabled: bool, token: str, task_id: str, tools_used: list[str], evidence: list[dict] | None = None, harness_id: str = "lean"):
    history = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    tool_trace = tools_used
    tool_evidence = evidence if evidence is not None else []
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0}
    started = time.monotonic()
    for _ in range(MAX_MODEL_REQUESTS):
        body = {
            "model": MODEL_NAME, "messages": history, "temperature": MODEL_TEMPERATURE,
            "max_tokens": MAX_COMPLETION_TOKENS, "stream": False,
        }
        if tools_enabled:
            body["tools"] = [{"type": "function", "function": t} for t in VISIBLE_TOOLS]
            body["tool_choice"] = "auto"
        model_api_key = MODEL_API_KEYS.get(harness_id)
        if not model_api_key:
            raise RuntimeError("candidate model authorization is not configured")
        request = urllib.request.Request(
            MODEL_URL.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {model_api_key}"},
        )
        with urllib.request.urlopen(request, timeout=MODEL_REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read())
        if not isinstance(result, dict) or not isinstance(result.get("choices"), list) or not result["choices"]:
            raise ProviderFailure("model provider returned an invalid completion")
        if result["choices"][0].get("finish_reason") in {"error", "length", "content_filter"}:
            raise ProviderFailure("model provider did not return a complete assistant turn")
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


def chat_pydantic(messages: list[dict], token: str, task_id: str, tools_used: list[str], evidence: list[dict] | None = None):
    from pydantic_ai import Agent, FunctionToolset, Tool, UsageLimits
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    started = time.monotonic()
    trace = tools_used
    tool_evidence = evidence if evidence is not None else []
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
    provider = OpenAIProvider(base_url=MODEL_URL, api_key=MODEL_API_KEY)
    # Ollama's native /api/chat tool schema has no OpenAI `strict` extension.
    # Pydantic AI otherwise advertises strict tool definitions by default.
    # Tool arguments remain validated by the declared JSON schemas and gateway.
    model = OpenAIChatModel(
        MODEL_NAME,
        provider=provider,
        profile={"openai_supports_strict_tool_definition": False},
    )
    agent = Agent(model, system_prompt=SYSTEM_PROMPT, toolsets=[toolset], retries=1)
    prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    result = agent.run_sync(
        prompt,
        model_settings={
            "timeout": MODEL_REQUEST_TIMEOUT_SECONDS,
            "temperature": MODEL_TEMPERATURE,
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
    evidence_file = trace_file.with_name("tool-evidence.jsonl")
    with HERMES_LOCKS[token]:
        task_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temp_task_file = task_file.with_suffix(".tmp")
        temp_task_file.write_text(task_id)
        temp_task_file.replace(task_file)
        trace_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        trace_file.write_text("")
        evidence_file.write_text("")
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            "temperature": MODEL_TEMPERATURE,
            "max_tokens": MAX_COMPLETION_TOKENS,
        }
        started = time.monotonic()
        request = urllib.request.Request(
            endpoint, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=MODEL_REQUEST_TIMEOUT_SECONDS) as response:
            value = json.loads(response.read())
        if not isinstance(value, dict) or value.get("error"):
            raise ProviderFailure("Hermes returned a provider error")
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ProviderFailure("Hermes returned an invalid completion")
        choice = choices[0]
        if choice.get("finish_reason") in {"error", "length", "content_filter"}:
            raise ProviderFailure("Hermes did not return a complete assistant turn")
        message = choice.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content", ""), str):
            raise ProviderFailure("Hermes returned an invalid assistant message")
        content = message.get("content") or ""
        if provider_diagnostic(content):
            raise ProviderFailure("Hermes returned a provider diagnostic instead of a final answer")
        usage = value.get("usage") or {}
        trace = [line for line in trace_file.read_text().splitlines() if line]
        tools_used.extend(trace)
        tool_evidence = [json.loads(line) for line in evidence_file.read_text().splitlines() if line]
    return {
        "text": content,
        "tool_calls": trace,
        "tool_evidence": tool_evidence,
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
        result = json.loads(response.read())
    print("task_transition " + json.dumps({
        "task_id": result.get("task_id"), "state": result.get("state", "RUNNING"),
        "reason": "task_created",
    }, sort_keys=True, separators=(",", ":")), flush=True)
    return result


def transition_task(
    token: str, task_id: str, state: str, tools_used: list[str], error_type: str | None = None,
    finalization: dict | None = None, resume: bool = False, annotations: dict | None = None,
):
    current = gateway_call("task_resume", {}, token, task_id)
    if current.get("http_status") or current.get("task_id") != task_id:
        raise RuntimeError("task state could not be read")
    checkpoint = dict(current.get("checkpoint") or {})
    if resume and checkpoint.get("effect_outcome_uncertain"):
        effects = current.get("effects") or []
        if effects and all(item.get("state") in {"CONFIRMED", "REJECTED", "FAILED"}
                           for item in effects):
            # A trusted reconciliation may settle the effect after the task was
            # parked. Clear the stale uncertainty marker only after a fresh
            # task read proves every recorded effect is terminal.
            checkpoint.pop("effect_outcome_uncertain", None)
    if resume:
        checkpoint.pop("final_response_pending", None)
        checkpoint.pop("completion_review_required", None)
    checkpoint.setdefault("summary", "Candidate turn state update")
    checkpoint.setdefault("completed", [])
    checkpoint.setdefault("pending", [])
    candidate_turn = {"state": state, "tools": tools_used}
    if error_type is not None:
        candidate_turn["error_type"] = error_type
        candidate_turn["operator_review_required"] = True
        if error_type in {"effect_outcome_uncertain", "write_outcome_not_confirmed"}:
            candidate_turn["effect_outcome_uncertain"] = True
    checkpoint["candidate_turn"] = candidate_turn
    if annotations:
        checkpoint.update(annotations)
    arguments = {"state": state, "checkpoint": checkpoint}
    if finalization is not None:
        arguments["_orchestrator_finalization"] = finalization
    if resume:
        arguments["_orchestrator_resume"] = True
    updated = gateway_call("task_checkpoint", arguments, token, task_id)
    if updated.get("http_status") or updated.get("state") != state:
        raise RuntimeError("task state could not be saved")
    transition = {"task_id": task_id, "state": state, "resume": resume}
    if isinstance(finalization, dict) and finalization.get("reason"):
        transition["reason"] = finalization["reason"]
    elif error_type:
        transition["reason"] = error_type
    print("task_transition " + json.dumps(transition, sort_keys=True, separators=(",", ":")), flush=True)
    return updated


def finalize_turn(token: str, task_id: str, result: dict):
    current = gateway_call("task_resume", {}, token, task_id)
    if current.get("http_status") or current.get("task_id") != task_id:
        raise RuntimeError("task state could not be read after candidate turn")
    if current.get("state") in {"COMPLETED", "FAILED", "CANCELLED", "WAITING"}:
        return current
    evidence = result.get("tool_evidence", [])
    claim_entry = next((item for item in reversed(evidence) if item.get("kind") == "completion_claim"), None)
    claim = claim_entry.get("checkpoint") if claim_entry else None
    if claim is None:
        progress = next((item for item in reversed(evidence) if item.get("kind") == "progress_checkpoint"), None)
        if progress and (progress.get("checkpoint") or {}).get("pending"):
            claim = progress["checkpoint"]
    state, reason = decide_turn_finalization(
        current.get("state"), result.get("text"),
        [item for item in evidence if item.get("kind") == "tool_evidence"], claim,
        [],
        current.get("effects", []),
        turn_error=result.get("provider_error") or provider_diagnostic(result.get("text", "")),
        trusted_completion_contract=(current.get("checkpoint") or {}).get("trusted_completion_contract"),
    )
    if state == "RUNNING":
        return current
    tools = result.get("tool_calls", [])
    finalization = None
    if state == "COMPLETED":
        checkpoint = dict(claim or {})
        checkpoint.setdefault("summary", "Model response completed from verified tool evidence")
        checkpoint.setdefault("completed", [reason])
        checkpoint.setdefault("pending", [])
        finalization = {
            "response_nonempty": bool((result.get("text") or "").strip()),
            "task_type": "EFFECTFUL" if current.get("effects") or any(
                item.get("tool") in {"shopping_list_change", "workspace_exec", "commitment_submit", "commitment_reconcile", "memory_write", "memory_correct"}
                for item in evidence if item.get("kind") == "tool_evidence"
            ) else "READ_ONLY",
            "completion_claim": claim is not None,
            "tool_evidence": [item for item in evidence if item.get("kind") == "tool_evidence"],
            "reason": reason,
        }
        if (current.get("checkpoint") or {}).get("trusted_completion_contract") is not None:
            finalization["response"] = result.get("text", "")
            finalization["provider_error"] = result.get("provider_error")
        return transition_task(
            token, task_id, state, tools, finalization=finalization,
            annotations={**checkpoint, "task_finalization": {"reason": reason}},
        )
    if state == "WAITING":
        finalization = {
            "response_nonempty": bool((result.get("text") or "").strip()),
            "tool_evidence": [item for item in evidence if item.get("kind") == "tool_evidence"],
            "reason": reason,
        }
        if reason in {"approval_pending", "approval_required"}:
            annotations = {"approval_pending": True}
        elif reason in {"final_response_pending", "completion_review_required"}:
            annotations = {reason: True}
        else:
            annotations = {"effect_outcome_uncertain": True}
        annotations["task_finalization"] = {"reason": reason}
        return transition_task(token, task_id, state, tools, finalization=finalization, annotations=annotations)
    return transition_task(token, task_id, state, tools, error_type=reason)


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
        turn_evidence = []
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
                current = gateway_call("task_resume", {}, token, task_id)
                if current.get("http_status") or current.get("task_id") != task_id:
                    return self.send_json(404, {"error": "task not found"})
                if current.get("state") in {"COMPLETED", "FAILED", "CANCELLED"}:
                    return self.send_json(409, {"error": "terminal task cannot be resumed", "task_state": current.get("state")})
                if current.get("state") == "WAITING":
                    checkpoint = current.get("checkpoint") or {}
                    effects = current.get("effects") or []
                    effects_settled = bool(effects) and all(
                        item.get("state") in {"CONFIRMED", "REJECTED", "FAILED"}
                        for item in effects
                    )
                    if checkpoint.get("approval_pending") or (
                        checkpoint.get("effect_outcome_uncertain") and not effects_settled
                    ):
                        return self.send_json(409, {"error": "task requires approval or effect reconciliation before resume", "task_state": "WAITING"})
                    transition_task(token, task_id, "RUNNING", [], resume=True)
            active_token = token
            active_task_id = task_id
            if candidate == "pydantic":
                result = chat_pydantic(messages, token, task_id, tools_used, turn_evidence)
            elif candidate == "hermes":
                result = chat_hermes(messages, token, task_id, tools_used)
            else:
                result = chat_openai(messages, True, token, task_id, tools_used, turn_evidence, "lean")
            current = finalize_turn(token, task_id, result)
            result["task_id"] = task_id
            result["task_state"] = current["state"]
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
                _, trace_file = HERMES_STATE[active_token]
                evidence_file = trace_file.with_name("tool-evidence.jsonl")
                try:
                    turn_evidence.extend(json.loads(line) for line in evidence_file.read_text().splitlines() if line)
                except (OSError, json.JSONDecodeError) as evidence_exc:
                    print(f"Could not read Hermes tool evidence: {type(evidence_exc).__name__}")
            if active_token and active_task_id:
                try:
                    current = gateway_call("task_resume", {}, active_token, active_task_id)
                    if current.get("state") == "RUNNING":
                        approval_pending = any(item.get("approval_pending") for item in turn_evidence)
                        effect_states = [item.get("state") for item in current.get("effects", [])]
                        uncertain = any(state in {"INTENDED", "DISPATCHED", "QUARANTINED", "UNRESOLVED"}
                                        for state in effect_states) or any(
                                            item.get("uncertain") for item in turn_evidence
                                        )
                        if any(item.get("tool") in {"memory_write", "memory_correct"}
                               for item in turn_evidence):
                            transition_task(
                                active_token, active_task_id, "WAITING", tools_used,
                                finalization={"response_nonempty": False, "tool_evidence": turn_evidence},
                                annotations={"memory_effect_evidence_unproven": True,
                                             "task_finalization": {"reason": "memory_effect_evidence_unproven"}},
                            )
                        elif approval_pending:
                            transition_task(
                                active_token, active_task_id, "WAITING", tools_used,
                                finalization={"response_nonempty": False, "tool_evidence": turn_evidence},
                                annotations={"approval_pending": True, "task_finalization": {"reason": "approval_pending_after_error"}},
                            )
                        elif uncertain:
                            transition_task(
                                active_token, active_task_id, "WAITING", tools_used,
                                finalization={"response_nonempty": False, "tool_evidence": []},
                                annotations={"effect_outcome_uncertain": True, "task_finalization": {"reason": "effect_outcome_uncertain_after_error"}},
                            )
                        elif effect_states and all(state == "CONFIRMED" for state in effect_states):
                            transition_task(
                                active_token, active_task_id, "WAITING", tools_used,
                                finalization={"response_nonempty": False, "tool_evidence": turn_evidence},
                                annotations={"final_response_pending": True,
                                             "task_finalization": {"reason": "final_response_pending"}},
                            )
                        else:
                            transition_task(active_token, active_task_id, "FAILED", tools_used, type(exc).__name__)
                except Exception as checkpoint_exc:
                    print(f"Could not close failed task: {type(checkpoint_exc).__name__}")
            print(f"Candidate request rejected: {type(exc).__name__}: {exc}")
            failure = {"error": f"candidate request failed: {type(exc).__name__}"}
            if active_task_id:
                failure["task_id"] = active_task_id
            return self.send_json(502, failure)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
