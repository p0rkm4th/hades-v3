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

    def test_read_then_provider_http_400_fails_instead_of_completing(self):
        result = {
            "text": "", "provider_error": "upstream_http_400", "tool_calls": ["infrastructure_read"],
            "tool_evidence": [{"kind": "tool_evidence", "tool": "infrastructure_read", "status": "ok"}],
        }
        final, writes = self.run_finalizer(
            {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}, result,
        )
        self.assertEqual(final["state"], "FAILED")
        self.assertEqual(writes[0]["checkpoint"]["candidate_turn"]["error_type"], "model_generation_failed")

    def test_read_then_generation_budget_exhaustion_fails(self):
        result = {
            "text": "I read the source.", "provider_error": "generation_budget_exhausted",
            "tool_calls": ["infrastructure_read"],
            "tool_evidence": [{"kind": "tool_evidence", "tool": "infrastructure_read", "status": "ok"}],
        }
        final, _ = self.run_finalizer(
            {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}, result,
        )
        self.assertEqual(final["state"], "FAILED")

    def test_memory_write_followed_by_provider_failure_stays_waiting(self):
        result = {
            "text": "", "provider_error": "upstream_http_400", "tool_calls": ["memory_write"],
            "tool_evidence": [{"kind": "tool_evidence", "tool": "memory_write", "status": "ok",
                               "state": "CONFIRMED", "memory_key": "preference"}],
        }
        final, writes = self.run_finalizer(
            {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}, result,
        )
        self.assertEqual(final["state"], "WAITING")
        self.assertEqual(writes[0]["_orchestrator_finalization"]["reason"],
                         "memory_effect_evidence_unproven")

    def test_hermes_provider_diagnostic_cannot_be_final_answer(self):
        self.assertTrue(api.provider_diagnostic(
            "⏱️ The model provider is rate-limiting requests. Please wait and try again."
        ))
        self.assertFalse(api.provider_diagnostic(
            "The synthetic API returned a healthy response with a rate limit header."
        ))
        result = {
            "text": "⏱️ The model provider is rate-limiting requests. Please wait and try again.",
            "tool_calls": ["infrastructure_read"],
            "tool_evidence": [{"kind": "tool_evidence", "tool": "infrastructure_read", "status": "ok"}],
        }
        final, _ = self.run_finalizer(
            {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}, result,
        )
        self.assertEqual(final["state"], "FAILED")

    def test_read_then_useful_answer_completes_from_trusted_read(self):
        result = {
            "text": "The router is fresh and healthy; backup is stale and lab health is unknown.",
            "tool_calls": ["infrastructure_read"],
            "tool_evidence": [{"kind": "tool_evidence", "tool": "infrastructure_read", "status": "ok"}],
        }
        final, _ = self.run_finalizer(
            {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}, result,
        )
        self.assertEqual(final["state"], "COMPLETED")

    def test_partial_effect_with_superficially_successful_answer_stays_running(self):
        initial = {"task_id": "task-1", "state": "RUNNING", "checkpoint": {},
                   "effects": [{"effect_id": "fx-1", "effect_kind": "GROCERY_LIST", "state": "CONFIRMED"}]}
        result = {
            "text": "Done, everything is updated.", "tool_calls": ["shopping_list_change"],
            "tool_evidence": [
                {"kind": "progress_checkpoint", "checkpoint": {"completed": ["first change"], "pending": ["second change"]}},
                {"kind": "tool_evidence", "tool": "shopping_list_change", "status": "ok", "state": "CONFIRMED",
                 "effect_id": "fx-1", "verified_after": [{"name": "Eggs", "amount": 2}]},
            ],
        }
        final, writes = self.run_finalizer(initial, result)
        self.assertEqual(final["state"], "RUNNING")
        self.assertEqual(writes, [])

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
