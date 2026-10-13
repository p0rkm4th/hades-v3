"""Narrow, fixed-destination Ollama to OpenAI chat adapter."""
import json
import os
from pathlib import Path
import threading
import time
import uuid
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

UPSTREAM = os.environ.get("OLLAMA_UPSTREAM", "http://ollama.invalid:11434").rstrip("/")
MODEL = os.environ.get("MODEL_ID", "gemma4:12b")
MAX_BODY = 256 * 1024
MAX_ACTIVE = 4
TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT_SECONDS", "120"))
_slots = threading.BoundedSemaphore(MAX_ACTIVE)
_budget_lock = threading.Lock()
_harness_keys = {
    "pydantic": os.environ.get("CP67_PYDANTIC_KEY"),
    "hermes": os.environ.get("CP67_HERMES_KEY"),
    "lean": os.environ.get("CP67_LEAN_KEY"),
}
if any(_harness_keys.values()) and (any(not value for value in _harness_keys.values())
                                    or len(set(_harness_keys.values())) != len(_harness_keys)):
    raise RuntimeError("CP67 harness keys must all be set and unique")
_harness_tokens = {key: harness for harness, key in _harness_keys.items() if key}
_generation_counts = {name: 0 for name in _harness_tokens.values()}
TRIAL_SECONDS = 900
_state_path = os.environ.get("TRIAL_STATE_FILE")
_deadline_epoch = time.time() + TRIAL_SECONDS
MAX_GENERATIONS_PER_HARNESS = 2
MAX_GENERATIONS_TOTAL = 6


def _load_budget():
    global _generation_counts, _deadline_epoch
    if not _state_path:
        return
    state = json.loads(Path(_state_path).read_text(encoding="utf-8"))
    counts = state.get("generation_counts")
    deadline = state.get("deadline_epoch")
    if (not isinstance(counts, dict) or set(counts) != set(_generation_counts)
            or any(type(value) is not int or value < 0 or value > MAX_GENERATIONS_PER_HARNESS
                   for value in counts.values())
            or sum(counts.values()) > MAX_GENERATIONS_TOTAL
            or not isinstance(deadline, (int, float))):
        raise RuntimeError("invalid persisted trial budget; refusing inference")
    _generation_counts = counts
    _deadline_epoch = float(deadline)


def _persist_budget():
    if not _state_path:
        return
    path = Path(_state_path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps({"deadline_epoch": _deadline_epoch,
                                "generation_counts": _generation_counts}, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


if _state_path:
    _load_budget()


def _reserve_generation(token):
    harness = _harness_tokens.get(token)
    if harness is None:
        return None
    with _budget_lock:
        if time.time() >= _deadline_epoch:
            return None
        if _generation_counts[harness] >= MAX_GENERATIONS_PER_HARNESS:
            return None
        if sum(_generation_counts.values()) >= MAX_GENERATIONS_TOTAL:
            return None
        _generation_counts[harness] += 1
        try:
            _persist_budget()
        except OSError:
            _generation_counts[harness] -= 1
            return None
        return harness, _generation_counts[harness]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def convert_response(value):
    message = value.get("message") or {}
    calls = []
    for tool in message.get("tool_calls") or []:
        function = tool.get("function") or {}
        args = function.get("arguments") or {}
        calls.append({"id": "call_" + uuid.uuid4().hex, "type": "function", "function": {
            "name": function.get("name", ""),
            "arguments": args if isinstance(args, str) else json.dumps(args, separators=(",", ":")),
        }})
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": message.get("content") or "",
                      **({"tool_calls": calls} if calls else {})},
                      "finish_reason": "tool_calls" if calls else "stop"}],
        "usage": {"prompt_tokens": int(value.get("prompt_eval_count") or 0),
                  "completion_tokens": int(value.get("eval_count") or 0),
                  "total_tokens": int(value.get("prompt_eval_count") or 0) + int(value.get("eval_count") or 0)},
    }


def generation_metrics(value):
    prompt_tokens = int(value.get("prompt_eval_count") or 0)
    output_tokens = int(value.get("eval_count") or 0)
    prompt_ns = int(value.get("prompt_eval_duration") or 0)
    output_ns = int(value.get("eval_duration") or 0)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": output_tokens,
        "prompt_eval_ms": round(prompt_ns / 1_000_000, 2) if prompt_ns else None,
        "generation_ms": round(output_ns / 1_000_000, 2) if output_ns else None,
        "generation_tokens_per_second": round(output_tokens * 1_000_000_000 / output_ns, 2) if output_ns else None,
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def send_json(self, code, value):
        body = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/v1/models":
            return self.send_json(404, {"error": "route not allowed"})
        authorization = self.headers.get("Authorization", "")
        token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
        if token not in _harness_tokens:
            return self.send_json(401, {"error": "trial authorization required"})
        return self.send_json(200, {"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "ollama"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.send_json(404, {"error": "route not allowed"})
        authorization = self.headers.get("Authorization", "")
        if authorization not in {"Bearer " + token for token in _harness_tokens}:
            return self.send_json(401, {"error": "trial authorization required"})
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or int(length) > MAX_BODY:
            return self.send_json(413, {"error": "request body too large or invalid"})
        try:
            request = json.loads(self.rfile.read(int(length)))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json(400, {"error": "invalid JSON"})
        if not isinstance(request, dict) or request.get("model") != MODEL:
            return self.send_json(400, {"error": "configured model required"})
        streaming = request.get("stream", False)
        if not isinstance(streaming, bool):
            return self.send_json(400, {"error": "stream must be a boolean"})
        if "upstream" in request or "url" in request or "base_url" in request:
            return self.send_json(400, {"error": "destination override is not allowed"})
        messages = request.get("messages")
        if not isinstance(messages, list) or not messages or any(not isinstance(m, dict) for m in messages):
            return self.send_json(400, {"error": "messages array required"})
        payload = {"model": MODEL, "messages": messages, "stream": False,
                   "options": {"num_ctx": 65536, "temperature": 0, "num_predict": 1024}}
        if request.get("tools") is not None:
            if not isinstance(request["tools"], list):
                return self.send_json(400, {"error": "tools must be an array"})
            payload["tools"] = request["tools"]
        token = authorization.removeprefix("Bearer ")
        reservation = _reserve_generation(token)
        if reservation is None:
            return self.send_json(429, {"error": "trial authorization, time, or generation budget exhausted"})
        harness, generation_number = reservation
        if not _slots.acquire(blocking=False):
            return self.send_json(429, {"error": "inference capacity reached"})
        started = time.monotonic()
        try:
            url = urlsplit(UPSTREAM)
            if url.scheme != "http" or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
                return self.send_json(502, {"error": "invalid fixed upstream configuration"})
            req = urllib.request.Request(UPSTREAM + "/api/chat", data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
            try:
                with _opener.open(req, timeout=TIMEOUT) as response:
                    raw = response.read(MAX_BODY + 1)
                    if len(raw) > MAX_BODY:
                        return self.send_json(502, {"error": "inference response too large"})
                    value = json.loads(raw)
            except urllib.error.HTTPError as exc:
                exc.close()
                return self.send_json(502, {"error": "fixed inference upstream failed"})
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                return self.send_json(502, {"error": "fixed inference upstream failed"})
            if not isinstance(value, dict) or not isinstance(value.get("message"), dict):
                return self.send_json(502, {"error": "invalid upstream response"})
            metrics = generation_metrics(value)
            print(f"inference_generation harness={harness} generation={generation_number} status=ok elapsed_ms={round((time.monotonic() - started) * 1000)} metrics={json.dumps(metrics, sort_keys=True, separators=(',', ':'))}", flush=True)
            if streaming:
                return self.send_stream(convert_response(value), request.get("stream_options"))
            return self.send_json(200, convert_response(value))
        finally:
            _slots.release()

    def send_stream(self, completion, stream_options):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        choice = completion["choices"][0]
        message = choice["message"]
        common = {"id": completion["id"], "object": "chat.completion.chunk",
                  "created": completion["created"], "model": MODEL}
        chunks = [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
        if message.get("content"):
            chunks.append({"index": 0, "delta": {"content": message["content"]}, "finish_reason": None})
        for index, call in enumerate(message.get("tool_calls", [])):
            chunks.append({"index": 0, "delta": {"tool_calls": [{
                "index": index, "id": call["id"], "type": "function",
                "function": call["function"],
            }]}, "finish_reason": None})
        chunks.append({"index": 0, "delta": {}, "finish_reason": choice["finish_reason"]})
        try:
            for item in chunks:
                body = json.dumps({**common, "choices": [item]}, separators=(",", ":"))
                self.wfile.write(f"data: {body}\n\n".encode())
                self.wfile.flush()
            if isinstance(stream_options, dict) and stream_options.get("include_usage") is True:
                body = json.dumps({**common, "choices": [], "usage": completion["usage"]}, separators=(",", ":"))
                self.wfile.write(f"data: {body}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_PUT(self):
        self.send_json(405, {"error": "method not allowed"})

    def do_DELETE(self):
        self.send_json(405, {"error": "method not allowed"})

    def do_PATCH(self):
        self.send_json(405, {"error": "method not allowed"})


def main():
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8098"))), Handler).serve_forever()


if __name__ == "__main__":
    main()
