"""Narrow, fixed-destination Ollama to OpenAI chat adapter."""
import json
import os
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
TIMEOUT = 45
_slots = threading.BoundedSemaphore(MAX_ACTIVE)
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


class Handler(BaseHTTPRequestHandler):
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
        return self.send_json(200, {"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "ollama"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.send_json(404, {"error": "route not allowed"})
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or int(length) > MAX_BODY:
            return self.send_json(413, {"error": "request body too large or invalid"})
        try:
            request = json.loads(self.rfile.read(int(length)))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json(400, {"error": "invalid JSON"})
        if not isinstance(request, dict) or request.get("model") != MODEL:
            return self.send_json(400, {"error": "configured model required"})
        if request.get("stream") is True:
            return self.send_json(400, {"error": "streaming is not supported"})
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
        if not _slots.acquire(blocking=False):
            return self.send_json(429, {"error": "inference capacity reached"})
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
            return self.send_json(200, convert_response(value))
        finally:
            _slots.release()

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
