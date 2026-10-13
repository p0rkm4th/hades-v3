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
from unittest.mock import patch

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
        marker = body["messages"][-1].get("content")
        if marker == "TEST_HTTP_503":
            self.send_response(503); self.send_header("Content-Length", "0"); self.end_headers(); return
        if marker == "TEST_MALFORMED":
            data = b"not-json"; self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        if marker == "TEST_INVALID_TOOL_OUTPUT":
            value = {"message": {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "inventory_read", "arguments": ["not", "an", "object"]}}
            ]}}
            data = json.dumps(value).encode(); self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        if marker == "TEST_TIMEOUT":
            time.sleep(0.1)
            data = b"{}"; self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers()
            try:
                self.wfile.write(data)
            except BrokenPipeError:
                pass
            return
        if marker == "TEST_REDIRECT":
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

    def setUp(self):
        adapter._generation_counts = {harness: 0 for harness in TEST_KEYS}

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

    def test_complete_openai_tool_exchange_is_translated_before_native_dispatch(self):
        history = [
            {"role": "system", "content": "Use only authorized fixtures."},
            {"role": "user", "content": "Read the router."},
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-native", "type": "function",
                "function": {"name": "infrastructure_read", "arguments": "{\"scope\":\"synthetic\"}"},
            }]},
            {"role": "tool", "tool_call_id": "call-native", "content": "trusted gateway result"},
        ]
        tools = [{"type": "function", "function": {
            "name": "infrastructure_read", "description": "read fixture",
            "parameters": {"type": "object", "properties": {}}, "strict": False,
        }}]
        before = len(seen)
        status, _ = request(self.base, "/v1/chat/completions", "POST", {
            "model": adapter.MODEL, "messages": history, "tools": tools,
        }, token=TEST_KEYS["lean"])
        self.assertEqual(status, 200)
        native = seen[before][1]
        self.assertEqual(native["messages"][2]["tool_calls"][0]["function"]["arguments"], {"scope": "synthetic"})
        self.assertNotIn("type", native["messages"][2]["tool_calls"][0])
        self.assertEqual(native["messages"][3], {
            "role": "tool", "content": "trusted gateway result",
            "tool_call_id": "call-native", "tool_name": "infrastructure_read",
        })
        self.assertNotIn("strict", native["tools"][0]["function"])
        self.assertEqual(native["messages"][1]["content"], "Read the router.")

    def test_malformed_tool_history_is_rejected_before_reservation_or_dispatch(self):
        before = len(seen)
        body = {"model": adapter.MODEL, "messages": [
            {"role": "user", "content": "read"},
            {"role": "assistant", "content": "", "tool_calls": [{
                "id": "call-bad", "type": "function",
                "function": {"name": "infrastructure_read", "arguments": "not-json"},
            }]},
            {"role": "tool", "tool_call_id": "call-bad", "content": "result"},
        ]}
        status, response = request(self.base, "/v1/chat/completions", "POST", body, token=TEST_KEYS["lean"])
        self.assertEqual(status, 400)
        self.assertEqual(response["error"], "invalid chat history")
        self.assertEqual(len(seen), before)
        self.assertEqual(adapter._generation_counts["lean"], 0)

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

    def test_capacity_rejection_does_not_reserve_or_dispatch(self):
        before_seen = len(seen)
        with patch.object(adapter._slots, "acquire", return_value=False):
            status, _ = request(self.base, "/v1/chat/completions", "POST", {
                "model": adapter.MODEL, "messages": [{"role": "user", "content": "capacity"}],
            }, token=TEST_KEYS["lean"])
        self.assertEqual(status, 429)
        self.assertEqual(adapter._generation_counts["lean"], 0)
        self.assertEqual(len(seen), before_seen)

    def test_rejections_are_logged_without_reservation_or_request_content(self):
        before_seen = len(seen)
        events = []
        body = {"model": adapter.MODEL, "messages": [{"role": "user", "content": "private prompt"}]}
        with patch.object(adapter, "_attempt_event",
                          side_effect=lambda *args, **kwargs: events.append((args, kwargs))):
            self.assertEqual(request(self.base, "/v1/chat/completions", "POST", body, token="wrong")[0], 401)
            self.assertEqual(request(self.base, "/api/ps", "GET", token=TEST_KEYS["lean"])[0], 404)
            self.assertEqual(request(self.base, "/v1/chat/completions", "PUT", body, token=TEST_KEYS["lean"])[0], 405)
            self.assertEqual(request(self.base, "/v1/chat/completions", "POST",
                                     {**body, "upstream": "http://invalid"}, token=TEST_KEYS["lean"])[0], 400)
            old_upstream = adapter.UPSTREAM
            adapter.UPSTREAM = "http://127.0.0.1:1/not-an-upstream"
            try:
                self.assertEqual(request(self.base, "/v1/chat/completions", "POST", body,
                                         token=TEST_KEYS["lean"])[0], 502)
            finally:
                adapter.UPSTREAM = old_upstream
        events_only = [(event[0][2], event[1].get("reason")) for event in events]
        self.assertEqual(events_only, [
            ("rejected_before_reservation", "authorization"),
            ("rejected_before_reservation", "route"),
            ("rejected_before_reservation", "method"),
            ("rejected_before_reservation", "destination_override"),
            ("rejected_before_reservation", "fixed_upstream_configuration"),
        ])
        self.assertEqual(adapter._generation_counts["lean"], 0)
        self.assertEqual(len(seen), before_seen)
        self.assertTrue(all("private prompt" not in json.dumps(event) for event in events))

    def test_budget_rejection_does_not_dispatch_upstream(self):
        before_seen = len(seen)
        adapter._generation_counts["lean"] = adapter.MAX_GENERATIONS_PER_HARNESS
        status, _ = request(self.base, "/v1/chat/completions", "POST", {
            "model": adapter.MODEL, "messages": [{"role": "user", "content": "budget"}],
        }, token=TEST_KEYS["lean"])
        self.assertEqual(status, 429)
        self.assertEqual(len(seen), before_seen)

    def test_dispatched_http_malformed_and_timeout_outcomes_are_distinct(self):
        for marker, expected_event, timeout in (
            ("TEST_HTTP_503", "upstream_http_error", None),
            ("TEST_MALFORMED", "upstream_outcome_uncertain", None),
            ("TEST_TIMEOUT", "upstream_outcome_uncertain", 0.01),
        ):
            events = []
            with patch.object(adapter, "_attempt_event", side_effect=lambda *args, **kwargs: events.append((args, kwargs))), \
                 patch.object(adapter, "TIMEOUT", timeout or adapter.TIMEOUT), \
                 patch.object(adapter, "MAX_GENERATIONS_PER_HARNESS", 3):
                status, _ = request(self.base, "/v1/chat/completions", "POST", {
                    "model": adapter.MODEL, "messages": [{"role": "user", "content": marker}],
                }, token=TEST_KEYS["pydantic"])
            self.assertEqual(status, 502)
            statuses = [event[0][2] for event in events]
            self.assertIn("reserved", statuses)
            self.assertIn("dispatch_started", statuses)
            self.assertIn(expected_event, statuses)
        self.assertEqual(adapter._generation_counts["pydantic"], 3)

    def test_invalid_native_tool_output_is_not_recorded_as_a_successful_generation(self):
        events = []
        with patch.object(adapter, "_attempt_event",
                          side_effect=lambda *args, **kwargs: events.append((args, kwargs))), \
             patch.object(adapter, "MAX_GENERATIONS_PER_HARNESS", 3):
            status, response = request(self.base, "/v1/chat/completions", "POST", {
                "model": adapter.MODEL, "messages": [{"role": "user", "content": "TEST_INVALID_TOOL_OUTPUT"}],
            }, token=TEST_KEYS["lean"])
        self.assertEqual(status, 502)
        self.assertEqual(response["error"], "invalid upstream response")
        statuses = [event[0][2] for event in events]
        self.assertEqual(statuses, ["reserved", "dispatch_started", "invalid_upstream_response"])
        self.assertEqual(adapter._generation_counts["lean"], 1)

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

    def test_cp71_context_probe_counts_toward_durable_budget_and_starts_deadline_once(self):
        attributes = ("_state_path", "_generation_counts", "_deadline_epoch", "_harness_tokens",
                      "TRIAL_SECONDS", "MAX_GENERATIONS_PER_HARNESS", "MAX_GENERATIONS_TOTAL")
        old = {name: getattr(adapter, name) for name in attributes}
        with tempfile.TemporaryDirectory() as directory:
            try:
                adapter._state_path = str(Path(directory) / "budget.json")
                adapter._harness_tokens = {**adapter._harness_tokens, "test-context-key": "context"}
                adapter._generation_counts = {**adapter._generation_counts, "context": 0}
                adapter._deadline_epoch = None
                adapter.TRIAL_SECONDS = 1200
                adapter.MAX_GENERATIONS_PER_HARNESS = 3
                adapter.MAX_GENERATIONS_TOTAL = 10
                adapter._persist_budget()
                initial = json.loads(Path(adapter._state_path).read_text())
                self.assertIsNone(initial["deadline_epoch"])

                reservation = adapter._reserve_generation("test-context-key")
                self.assertEqual(reservation, ("context", 1))
                started = json.loads(Path(adapter._state_path).read_text())
                self.assertIsNotNone(started["deadline_epoch"])
                self.assertEqual(started["generation_counts"]["context"], 1)
                self.assertEqual(sum(started["generation_counts"].values()), 1)

                adapter._generation_counts = {name: 0 for name in adapter._generation_counts}
                adapter._deadline_epoch = None
                adapter._load_budget()
                self.assertEqual(adapter._generation_counts["context"], 1)
                self.assertEqual(adapter._deadline_epoch, started["deadline_epoch"])
                self.assertIsNone(adapter._reserve_generation("test-context-key"))
            finally:
                for name, value in old.items():
                    setattr(adapter, name, value)


if __name__ == "__main__": unittest.main()
