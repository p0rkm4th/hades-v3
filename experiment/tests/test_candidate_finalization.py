import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "candidates"))
sys.path.insert(0, str(ROOT))
import api


class CandidateFinalization(unittest.TestCase):
    def run_finalizer(self, initial, result):
        state = dict(initial)
        writes = []

        def fake_gateway_call(name, arguments, token, task_id, evidence=None):
            if name == "task_resume":
                return dict(state)
            if name == "task_checkpoint":
                writes.append(dict(arguments))
                state.update({"state": arguments["state"], "checkpoint": arguments["checkpoint"]})
                return dict(state)
            raise AssertionError(name)

        with patch.object(api, "gateway_call", side_effect=fake_gateway_call):
            final = api.finalize_turn("fixture-token-amber", "task-1", result)
        return final, writes

    def test_read_completes_from_verified_evidence_without_model_claim(self):
        initial = {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}
        result = {
            "text": "The source is unavailable.", "tool_calls": ["infrastructure_read"],
            "tool_evidence": [
                {"kind": "tool_evidence", "tool": "infrastructure_read", "status": "ok"},
            ],
        }
        final, writes = self.run_finalizer(initial, result)
        self.assertEqual(final["state"], "COMPLETED")
        self.assertFalse(writes[0]["_orchestrator_finalization"]["completion_claim"])
        self.assertEqual(writes[0]["_orchestrator_finalization"]["task_type"], "READ_ONLY")

    def test_http_success_without_completion_evidence_fails_closed(self):
        final, _ = self.run_finalizer(
            {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []},
            {"text": "A response exists.", "tool_calls": [], "tool_evidence": []},
        )
        self.assertEqual(final["state"], "FAILED")

    def test_partial_turn_stays_running_and_waiting_is_preserved(self):
        initial = {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}
        result = {
            "text": "First step done.", "tool_calls": ["infrastructure_read"],
            "tool_evidence": [
                {"kind": "progress_checkpoint", "checkpoint": {"completed": ["read"], "pending": ["verify" ]}},
                {"kind": "tool_evidence", "tool": "infrastructure_read", "status": "ok"},
            ],
        }
        final, writes = self.run_finalizer(initial, result)
        self.assertEqual(final["state"], "RUNNING")
        self.assertEqual(writes, [])
        waiting = {"task_id": "task-1", "state": "WAITING", "checkpoint": {}, "effects": []}
        final, writes = self.run_finalizer(waiting, result)
        self.assertEqual(final["state"], "WAITING")
        self.assertEqual(writes, [])

    def test_confirmed_write_needs_completion_claim(self):
        initial = {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": [{"effect_id": "fx-1", "effect_kind": "GROCERY_LIST", "state": "CONFIRMED"}]}
        result = {
            "text": "Updated and verified.", "tool_calls": ["shopping_list_change"],
            "tool_evidence": [
                {"kind": "completion_claim", "checkpoint": {"summary": "Read-back matched", "completed": ["change"], "pending": []}},
                {"kind": "tool_evidence", "tool": "shopping_list_change", "status": "ok", "state": "CONFIRMED", "effect_id": "fx-1", "verified_after": [{"name": "Eggs", "amount": 2}]},
            ],
        }
        final, _ = self.run_finalizer(initial, result)
        self.assertEqual(final["state"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
