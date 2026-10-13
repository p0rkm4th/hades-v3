"""Protocol-strict deterministic Ollama peer for isolated CP69 integration tests."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()
ATTEMPTS = []


def _read_observation(messages):
    for message in messages:
        pending = [message.get("content")]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                if isinstance(item.get("observations"), list):
                    return item
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, str):
                try:
                    pending.append(json.loads(item))
                    continue
                except json.JSONDecodeError:
                    pass
                decoder = json.JSONDecoder()
                for index, char in enumerate(item):
                    if char != "{":
                        continue
                    try:
                        value, _ = decoder.raw_decode(item[index:])
                    except json.JSONDecodeError:
                        continue
                    pending.append(value)
    return None


def _tool_calls(messages):
    calls = []
    for message in messages:
        if message.get("role") == "assistant":
            calls.extend(message.get("tool_calls") or [])
    return calls


def _validate_native_history(messages):
    """Independent peer-side schema check; do not reuse the adapter translator."""
    allowed = {"role", "content", "thinking", "images", "tool_calls", "tool_name", "tool_call_id"}
    outstanding = {}
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or set(message) - allowed:
            return False, f"message_{index}_has_non_native_fields"
        role = message.get("role")
        if role not in {"system", "user", "assistant", "tool"}:
            return False, f"message_{index}_has_invalid_role"
        if not isinstance(message.get("content", ""), str):
            return False, f"message_{index}_content_is_not_string"
        if outstanding and role != "tool":
            return False, "assistant_tool_call_not_followed_by_tool_result"
        if role == "assistant":
            calls = message.get("tool_calls", [])
            if not isinstance(calls, list):
                return False, f"message_{index}_tool_calls_not_array"
            for call in calls:
                if not isinstance(call, dict) or set(call) - {"id", "function"}:
                    return False, f"message_{index}_tool_call_not_native"
                call_id = call.get("id")
                function = call.get("function")
                if not isinstance(function, dict) or set(function) - {"name", "arguments"}:
                    return False, f"message_{index}_function_not_native"
                if (not isinstance(call_id, str) or not call_id or call_id in outstanding
                        or not isinstance(function.get("name"), str)
                        or not isinstance(function.get("arguments"), dict)):
                    return False, f"message_{index}_function_arguments_must_be_object"
                outstanding[call_id] = function["name"]
        elif role == "tool":
            call_id = message.get("tool_call_id")
            if not isinstance(call_id, str) or call_id not in outstanding:
                return False, f"message_{index}_tool_result_has_no_matching_call_id"
            if message.get("tool_name") != outstanding[call_id]:
                return False, f"message_{index}_tool_name_mismatch"
            del outstanding[call_id]
    if outstanding:
        return False, "history_has_unanswered_tool_calls"
    return True, None


def _validate_native_tools(tools):
    if tools is None:
        return True, None
    if not isinstance(tools, list):
        return False, "tools_not_array"
    for index, tool in enumerate(tools):
        if (not isinstance(tool, dict) or set(tool) != {"type", "function"}
                or tool.get("type") != "function"):
            return False, f"tool_{index}_not_native"
        function = tool.get("function")
        if (not isinstance(function, dict) or set(function) - {"name", "description", "parameters"}
                or not isinstance(function.get("name"), str)
                or not isinstance(function.get("parameters"), dict)):
            return False, f"tool_{index}_function_not_native"
    return True, None


def _search_result(messages):
    searched = any(
        ((call.get("function") or {}).get("name") == "tool_search")
        for call in _tool_calls(messages)
    )
    if not searched:
        return None
    for message in messages:
        if message.get("role") != "tool":
            continue
        content = message.get("content") or ""
        matches = re.findall(r"(?:mcp__)?[A-Za-z0-9_-]+__infrastructure_read", content)
        if matches:
            return matches[0]
        if re.search(r"\binfrastructure_read\b", content):
            return "infrastructure_read"
    return None


def _answer(observation):
    rows = {row.get("subject"): row for row in observation["observations"] if isinstance(row, dict)}
    router = rows.get("synthetic-router")
    backup = rows.get("synthetic-backup")
    host = rows.get("synthetic-lab-host")
    if not all((router, backup, host)):
        return "The observation is incomplete; I cannot report all three infrastructure states."
    router_health = (router.get("value") or {}).get("health", "unknown")
    backup_health = (backup.get("value") or {}).get("health", "unknown")
    host_value = host.get("value")
    host_health = (host_value or {}).get("health") if isinstance(host_value, dict) else None
    host_clause = f"health {host_health}" if host_health else "no health value was observed"
    return (
        f"Synthetic router: {router.get('observation_state')}; health {router_health}. "
        f"Synthetic backup: {backup.get('observation_state')}; reported health {backup_health}. "
        f"Synthetic lab host: {host.get('observation_state')}; {host_clause}."
    )


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def _send(self, status, value):
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/__test/state":
            return self._send(404, {"error": "not found"})
        with LOCK:
            return self._send(200, {"attempts": list(ATTEMPTS)})

    def do_POST(self):
        if self.path != "/api/chat":
            return self._send(404, {"error": "not found"})
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "invalid JSON"})
        messages = payload.get("messages")
        if not isinstance(messages, list):
            return self._send(400, {"error": "messages required"})
        history_valid, history_error = _validate_native_history(messages)
        if not history_valid:
            return self._send(400, {"error": "invalid native Ollama chat history", "detail": history_error})
        tools_valid, tools_error = _validate_native_tools(payload.get("tools"))
        if not tools_valid:
            return self._send(400, {"error": "invalid native Ollama tool declaration", "detail": tools_error})
        tool_names = [
            ((tool.get("function") or {}).get("name"))
            for tool in payload.get("tools", []) if isinstance(tool, dict)
        ]
        observation = _read_observation(messages)
        prior_calls = _tool_calls(messages)
        search_name = _search_result(messages)
        harness = self.headers.get("X-Experiment-Harness", "unknown")
        options = payload.get("options") or {}
        config_matches = (
            payload.get("model") == "cp68-scripted-model"
            and options.get("num_ctx") == 65536
            and options.get("temperature") == 0
            and options.get("num_predict") == 1024
        )
        record = {
            "harness": harness,
            "stage": "answer" if observation else "tool_request",
            "available_tools": tool_names,
            "message_roles": [message.get("role") for message in messages],
            "assistant_tool_calls": [
                (call.get("function") or {}).get("name") for call in prior_calls
            ],
            "configuration_matches": config_matches,
            "genuine_observation_received": observation is not None,
            "native_history_valid": history_valid,
            "native_tools_valid": tools_valid,
            "tool_result_names": [message.get("tool_name") for message in messages if message.get("role") == "tool"],
            "tool_result_ids": [message.get("tool_call_id") for message in messages if message.get("role") == "tool"],
            "observation_sha256": hashlib.sha256(
                json.dumps(observation, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest() if observation is not None else None,
        }
        with LOCK:
            ATTEMPTS.append(record)

        if not config_matches:
            return self._send(400, {"error": "offline inference configuration mismatch"})

        if observation is None:
            if "infrastructure_read" in tool_names:
                message = {"role": "assistant", "content": "", "tool_calls": [{
                    "function": {"name": "infrastructure_read", "arguments": {}}
                }]}
                record["stage"] = "tool_request"
            elif "tool_search" in tool_names and not any(
                (call.get("function") or {}).get("name") == "tool_search" for call in prior_calls
            ):
                message = {"role": "assistant", "content": "", "tool_calls": [{
                    "function": {"name": "tool_search", "arguments": {"queries": ["infrastructure_read"], "limit": 5}}
                }]}
                record["stage"] = "tool_search"
            elif "tool_call" in tool_names and search_name and not any(
                (call.get("function") or {}).get("name") == "tool_call" for call in prior_calls
            ):
                message = {"role": "assistant", "content": "", "tool_calls": [{
                    "function": {"name": "tool_call", "arguments": {
                        "calls": [{"name": search_name, "arguments": {}}]
                    }}
                }]}
                record["stage"] = "tool_dispatch"
                record["selected_tool"] = search_name
            else:
                message = {"role": "assistant", "content": "I could not verify the infrastructure observation because the tool did not return usable data."}
        else:
            message = {"role": "assistant", "content": _answer(observation)}
        return self._send(200, {
            "message": message,
            "done": True,
            "prompt_eval_count": 128,
            "eval_count": 32,
            "prompt_eval_duration": 4_000_000,
            "eval_duration": 8_000_000,
            "total_duration": 12_000_000,
        })


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 11434), Handler).serve_forever()
