import json
import sys
import threading
import tempfile
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
import inference_adapter as adapter

TEST_KEYS = {"pydantic": "test-key-pydantic", "hermes": "test-key-hermes", "lean": "test-key-lean"}

seen = []
redirect_hits = []
class Sink(BaseHTTPRequestHandler):
    def do_GET(self):
        redirect_hits.append(self.path)
        self.send_response(200); self.end_headers()
    def log_message(self, *args): pass

sink = ThreadingHTTPServer(("127.0.0.1", 0), Sink)
class FakeOllama(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        seen.append((self.path, body))
        if self.path != "/api/chat":
            self.send_response(404); self.end_headers(); return
        if body["messages"][-1].get("content") == "TEST_REDIRECT":
            self.send_response(307); self.send_header("Location", f"http://127.0.0.1:{sink.server_port}/collect"); self.end_headers(); return
        value = {"message": {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "inventory_read", "arguments": {"query": "x"}}}]},
            "prompt_eval_count": 17, "eval_count": 4, "prompt_eval_duration": 1_000_000_000,
            "eval_duration": 2_000_000_000}
        data = json.dumps(value).encode(); self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *args): pass

fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
class AdapterTestServer(ThreadingHTTPServer):
    daemon_threads = True


def request(base, path, method="GET", body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(base + path, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=2) as res:
            return res.status, json.loads(res.read())
    except HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        finally:
            exc.close()


class AdapterIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adapter._harness_tokens = {key: harness for harness, key in TEST_KEYS.items()}
        adapter._generation_counts = {harness: 0 for harness in TEST_KEYS}
        adapter.UPSTREAM = f"http://127.0.0.1:{fake.server_port}"
        cls.server = AdapterTestServer(("127.0.0.1", 0), adapter.Handler)
        for server in (sink, fake, cls.server):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        for server in (cls.server, fake, sink): server.shutdown(); server.server_close()

    def test_tool_call_translation_and_forced_inference_configuration(self):
        upstream_before = len(seen)
        status, models = request(self.base, "/v1/models", token=TEST_KEYS["lean"])
        self.assertEqual(status, 200); self.assertEqual(models["data"][0]["id"], adapter.MODEL)
        self.assertEqual(len(seen), upstream_before)
        status, response = request(self.base, "/v1/chat/completions", "POST", {
            "model": adapter.MODEL, "messages": [{"role": "user", "content": "hello"}],
            "temperature": 1.8, "max_tokens": 4,
            "tools": [{"type": "function", "function": {"name": "inventory_read", "parameters": {"type": "object"}}}],
        }, token=TEST_KEYS["lean"])
        self.assertEqual(status, 200)
        upstream_path, payload = seen[-1]
        self.assertEqual(upstream_path, "/api/chat")
        self.assertEqual(payload["options"], {"num_ctx": 65536, "temperature": 0, "num_predict": 1024})
        self.assertEqual(payload["tools"][0]["function"]["name"], "inventory_read")
        call = response["choices"][0]["message"]["tool_calls"][0]
        self.assertEqual(call["function"]["name"], "inventory_read")
        self.assertEqual(json.loads(call["function"]["arguments"]), {"query": "x"})
        self.assertEqual(response["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(response["usage"], {"prompt_tokens": 17, "completion_tokens": 4, "total_tokens": 21})
        self.assertEqual(adapter.generation_metrics({
            "prompt_eval_count": 17, "eval_count": 4, "prompt_eval_duration": 1_000_000_000,
            "eval_duration": 2_000_000_000}), {
                "prompt_tokens": 17, "completion_tokens": 4, "prompt_eval_ms": 1000.0,
                "generation_ms": 2000.0, "generation_tokens_per_second": 2.0})

    def test_streaming_tool_call_translation(self):
        before = len(seen)
        body = {"model": adapter.MODEL, "messages": [{"role": "user", "content": "stream"}], "stream": True,
                "tools": [{"type": "function", "function": {"name": "inventory_read", "parameters": {"type": "object"}}}]}
        req = Request(self.base + "/v1/chat/completions", data=json.dumps(body).encode(), method="POST",
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + TEST_KEYS["hermes"]})
        with urlopen(req, timeout=3) as response:
            self.assertEqual(response.headers.get_content_type(), "text/event-stream")
            stream = response.read().decode()
        self.assertIn('"finish_reason":"tool_calls"', stream)
        self.assertIn('"name":"inventory_read"', stream)
        self.assertIn('"arguments":"{\\"query\\":\\"x\\"}"', stream)
        self.assertTrue(stream.endswith("data: [DONE]\n\n"))
        self.assertEqual(len(seen), before + 1)
        self.assertFalse(seen[-1][1]["stream"])

    def test_destination_routes_methods_model_and_redirect_are_rejected(self):
        before = len(seen)
        for body in ({"model": adapter.MODEL, "messages": [{"role": "user", "content": "x"}], "upstream": "http://127.0.0.1:1"},
                     {"model": "other", "messages": [{"role": "user", "content": "x"}]},
                     {"model": adapter.MODEL, "messages": [{"role": "user", "content": "x"}], "stream": True}):
            self.assertNotEqual(request(self.base, "/v1/chat/completions", "POST", body)[0], 200)
        self.assertEqual(len(seen), before)
        self.assertEqual(request(self.base, "/api/pull", "POST", {})[0], 404)
        self.assertEqual(request(self.base, "/v1/chat/completions", "PUT", {})[0], 405)
        status, _ = request(self.base, "/v1/chat/completions", "POST", {
            "model": adapter.MODEL, "messages": [{"role": "user", "content": "TEST_REDIRECT"}]}, token=TEST_KEYS["lean"])
        self.assertEqual(status, 502)
        self.assertEqual(redirect_hits, [])

    def test_unknown_authorization_and_exhausted_budget_are_rejected(self):
        body = {"model": adapter.MODEL, "messages": [{"role": "user", "content": "x"}]}
        self.assertEqual(request(self.base, "/v1/models")[0], 401)
        self.assertEqual(request(self.base, "/v1/chat/completions", "POST", body, token="other")[0], 401)
        for _ in range(2):
            self.assertEqual(adapter._reserve_generation(TEST_KEYS["pydantic"]) is not None, True)
        self.assertIsNone(adapter._reserve_generation(TEST_KEYS["pydantic"]))

    def test_generation_budget_survives_adapter_process_reload(self):
        old_path, old_counts, old_deadline = adapter._state_path, adapter._generation_counts, adapter._deadline_epoch
        with tempfile.TemporaryDirectory() as directory:
            adapter._state_path = str(Path(directory) / "budget.json")
            adapter._generation_counts = {name: 0 for name in adapter._harness_tokens.values()}
            adapter._deadline_epoch = time.time() + 60
            adapter._persist_budget()
            self.assertEqual(adapter._reserve_generation(TEST_KEYS["pydantic"]), ("pydantic", 1))
            adapter._generation_counts = {name: 0 for name in adapter._harness_tokens.values()}
            adapter._load_budget()
            self.assertEqual(adapter._generation_counts["pydantic"], 1)
        adapter._state_path, adapter._generation_counts, adapter._deadline_epoch = old_path, old_counts, old_deadline


if __name__ == "__main__": unittest.main()
