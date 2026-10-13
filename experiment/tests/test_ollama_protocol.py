import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "tests"))
from ollama_protocol import ProtocolError, translate_messages
from scripted_ollama import _validate_native_history


class OllamaNativeHistory(unittest.TestCase):
    def setUp(self):
        self.openai_history = [
            {"role": "system", "content": "Use only authorized fixtures."},
            {"role": "user", "content": "Read the synthetic router health."},
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": "infrastructure_read", "arguments": "{}"},
            }]},
            {"role": "tool", "tool_call_id": "call-1", "content": "{\"observations\":[{\"subject\":\"synthetic-router\"}]}"},
        ]

    def test_openai_string_arguments_and_result_id_map_to_native_shape(self):
        native = translate_messages(self.openai_history)
        self.assertEqual(_validate_native_history(native), (True, None))
        self.assertEqual(native[2], {
            "role": "assistant", "content": "", "tool_calls": [{
                "id": "call-1", "function": {"name": "infrastructure_read", "arguments": {}},
            }],
        })
        self.assertEqual(native[3], {
            "role": "tool", "content": "{\"observations\":[{\"subject\":\"synthetic-router\"}]}",
            "tool_call_id": "call-1", "tool_name": "infrastructure_read",
        })

    def test_strict_peer_rejects_the_cp68_openai_shape_before_translation(self):
        self.assertEqual(_validate_native_history(self.openai_history),
                         (False, "message_2_content_is_not_string"))
        # The native request shape has no OpenAI call type and arguments must be an object.
        broken = json.loads(json.dumps(self.openai_history))
        broken[2]["content"] = ""
        broken[2]["tool_calls"][0].pop("type")
        broken[3]["tool_name"] = "infrastructure_read"
        self.assertIn("function_arguments_must_be_object", _validate_native_history(broken)[1])

    def test_multi_call_results_preserve_order_and_identity(self):
        messages = [
            {"role": "user", "content": "Read both."},
            {"role": "assistant", "content": "checking", "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "inventory_read", "arguments": "{}"}},
                {"id": "c2", "type": "function", "function": {"name": "infrastructure_read", "arguments": "{\"scope\":\"synthetic\"}"}},
            ]},
            {"role": "tool", "tool_call_id": "c1", "content": "inventory"},
            {"role": "tool", "tool_call_id": "c2", "name": "infrastructure_read", "content": "health"},
        ]
        native = translate_messages(messages)
        self.assertEqual(_validate_native_history(native), (True, None))
        self.assertEqual([m["tool_name"] for m in native if m["role"] == "tool"],
                         ["inventory_read", "infrastructure_read"])
        self.assertEqual([m["tool_call_id"] for m in native if m["role"] == "tool"], ["c1", "c2"])

    def test_incomplete_or_mismatched_tool_history_is_rejected(self):
        for update in (
            {"messages": self.openai_history[:-1]},
            {"messages": [*self.openai_history[:3], {**self.openai_history[3], "tool_call_id": "wrong"}]},
            {"messages": [*self.openai_history[:3], {**self.openai_history[3], "name": "wrong_tool"}]},
        ):
            with self.subTest(update=update):
                with self.assertRaises(ProtocolError):
                    translate_messages(update["messages"])

    def test_malformed_arguments_and_unsupported_content_fail_closed(self):
        for arguments in ("not json", "[]", {"already": "decoded"}):
            messages = json.loads(json.dumps(self.openai_history))
            messages[2]["tool_calls"][0]["function"]["arguments"] = arguments
            with self.subTest(arguments=arguments), self.assertRaises(ProtocolError):
                translate_messages(messages)
        messages = json.loads(json.dumps(self.openai_history))
        messages[1]["content"] = [{"type": "text", "text": "must not be discarded"}]
        with self.assertRaisesRegex(ProtocolError, "multipart content"):
            translate_messages(messages)
        messages = json.loads(json.dumps(self.openai_history))
        messages[1]["annotations"] = [{"type": "citation"}]
        with self.assertRaisesRegex(ProtocolError, "unsupported fields"):
            translate_messages(messages)

    def test_developer_and_reasoning_fields_have_explicit_native_mappings(self):
        native = translate_messages([
            {"role": "developer", "content": "Policy."},
            {"role": "assistant", "content": "answer", "reasoning_content": "brief internal note"},
        ])
        self.assertEqual(native, [
            {"role": "system", "content": "Policy."},
            {"role": "assistant", "content": "answer", "thinking": "brief internal note"},
        ])


if __name__ == "__main__":
    unittest.main()
