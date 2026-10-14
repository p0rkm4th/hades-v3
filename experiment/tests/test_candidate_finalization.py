import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "candidates"))
sys.path.insert(0, str(ROOT))
import api
from contracts.task_lifecycle import commitment_digest


class CandidateFinalization(unittest.TestCase):
    def run_finalizer(self, initial, result):
        state = dict(initial)
        writes = []

        def fake_gateway_call(name, arguments, token, task_id, evidence=None, trusted_internal=False):
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

    def test_quarantined_workspace_exception_is_recoverable_waiting(self):
        decision = api.classify_turn_exception(
            {"state": "RUNNING", "effects": [{"effect_kind": "WORKSPACE_COMMAND",
                                                "state": "QUARANTINED"}]},
            [{"tool": "workspace_exec", "uncertain": True}],
        )
        self.assertEqual(decision, ("WAITING", "effect_outcome_uncertain_after_error"))

    def test_confirmed_workspace_effect_exception_waits_for_final_response(self):
        decision = api.classify_turn_exception(
            {"state": "RUNNING", "effects": [{"effect_kind": "WORKSPACE_COMMAND",
                                                "state": "CONFIRMED"}]},
            [{"tool": "workspace_exec", "state": "CONFIRMED"}],
        )
        self.assertEqual(decision, ("WAITING", "final_response_pending"))

    def test_unaffected_runtime_error_remains_failed(self):
        decision = api.classify_turn_exception(
            {"state": "RUNNING", "effects": []}, [],
        )
        self.assertEqual(decision, ("FAILED", "candidate_runtime_error"))

    def test_candidate_cannot_request_orchestrator_header_with_reserved_fields(self):
        cases = (
            ("_orchestrator_resume", "RUNNING"),
            ("_orchestrator_finalization", "COMPLETED"),
        )
        for reserved, state in cases:
            with self.subTest(field=reserved), patch.object(api.urllib.request, "urlopen") as request:
                with self.assertRaisesRegex(ValueError, "orchestrator-only task fields"):
                    api.gateway_call(
                        "task_checkpoint",
                        {
                            "state": state,
                            "checkpoint": {"summary": "forged", "completed": ["x"], "pending": []},
                            reserved: True,
                        },
                        "fixture-token-amber", "task-1",
                    )
                request.assert_not_called()

    def test_exception_does_not_override_existing_waiting_or_terminal_state(self):
        self.assertIsNone(api.classify_turn_exception({"state": "WAITING", "effects": []}, []))
        self.assertIsNone(api.classify_turn_exception({"state": "COMPLETED", "effects": []}, []))

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

    def test_rejected_memory_mutation_is_not_left_waiting_as_if_effect_uncertain(self):
        result = {
            "text": "The requested memory correction did not match an existing value.",
            "tool_calls": ["memory_correct"],
            "tool_evidence": [{"kind": "tool_evidence", "tool": "memory_correct",
                               "status": "error", "http_status": 404}],
        }
        final, _ = self.run_finalizer(
            {"task_id": "task-1", "state": "RUNNING", "checkpoint": {}, "effects": []}, result,
        )
        self.assertEqual(final["state"], "FAILED")

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

    def test_trusted_bounded_contract_completes_without_model_checkpoint(self):
        contract = {
            "version": 1, "kind": "external_commitment_set", "required": [{
                "effect_kind": "EXTERNAL_COMMITMENT", "target_id": "appointment-1",
                "details": "Reserve the exact appointment for Amber",
                "effect_digest": commitment_digest(
                    "appointment-1", "Reserve the exact appointment for Amber"
                ),
            }],
        }
        result = {"text": "The requested appointment was confirmed.",
                  "tool_calls": ["commitment_submit", "commitment_reconcile"],
                  "tool_evidence": []}
        final, writes = self.run_finalizer({
            "task_id": "task-1", "state": "RUNNING",
            "checkpoint": {"trusted_completion_contract": contract},
            "effects": [{"effect_id": "effect-1", "effect_kind": "EXTERNAL_COMMITMENT", "state": "CONFIRMED"}],
        }, result)
        self.assertEqual(final["state"], "COMPLETED")
        proof = writes[0]["_orchestrator_finalization"]
        self.assertFalse(proof["completion_claim"])
        self.assertEqual(proof["response"], result["text"])
        self.assertEqual(proof["reason"], "trusted_success_criteria_satisfied")

    def test_trusted_memory_correction_completes_from_durable_effect_without_model_checkpoint(self):
        contract = {
            "version": 1, "kind": "memory_correction", "required": [{
                "effect_kind": "MEMORY_MUTATION", "memory_key": "weekly_format",
                "expected_revision": 2, "value": {"format": "short bullets"},
            }],
        }
        effect = {"effect_id": "memory-fx", "effect_kind": "MEMORY_MUTATION", "state": "CONFIRMED"}
        result = {"text": "Your weekly summary preference is now short bullets.",
                  "tool_calls": ["memory_search", "memory_correct"], "tool_evidence": []}
        final, writes = self.run_finalizer({
            "task_id": "task-1", "state": "RUNNING",
            "checkpoint": {"trusted_completion_contract": contract}, "effects": [effect],
        }, result)
        self.assertEqual(final["state"], "COMPLETED")
        proof = writes[0]["_orchestrator_finalization"]
        self.assertFalse(proof["completion_claim"])
        self.assertEqual(proof["response"], result["text"])
        self.assertEqual(proof["reason"], "trusted_success_criteria_satisfied")

    def test_trusted_memory_contract_cannot_complete_without_persisted_mutation(self):
        contract = {"version": 1, "kind": "memory_correction", "required": [{
            "effect_kind": "MEMORY_MUTATION", "memory_key": "weekly_format",
            "expected_revision": 2, "value": {"format": "short bullets"},
        }]}
        final, writes = self.run_finalizer({
            "task_id": "task-1", "state": "RUNNING",
            "checkpoint": {"trusted_completion_contract": contract}, "effects": [],
        }, {"text": "I changed the preference.", "tool_calls": [], "tool_evidence": [
            {"kind": "completion_claim", "checkpoint": {
                "summary": "Preference updated", "completed": ["correction"], "pending": [],
            }},
        ]})
        self.assertEqual(final["state"], "WAITING")
        self.assertEqual(writes[0]["_orchestrator_finalization"]["reason"], "completion_review_required")

    def test_trusted_memory_contract_does_not_fall_back_to_read_only_completion(self):
        contract = {"version": 1, "kind": "memory_correction", "required": [{
            "effect_kind": "MEMORY_MUTATION", "memory_key": "weekly_format",
            "expected_revision": 2, "value": {"format": "short bullets"},
        }]}
        final, writes = self.run_finalizer({
            "task_id": "task-1", "state": "RUNNING",
            "checkpoint": {"trusted_completion_contract": contract}, "effects": [],
        }, {"text": "I found the saved preference; it is updated.",
            "tool_calls": ["memory_search"], "tool_evidence": [
                {"kind": "tool_evidence", "tool": "memory_search", "status": "ok"},
            ]})
        self.assertEqual(final["state"], "WAITING")
        self.assertEqual(writes[0]["_orchestrator_finalization"]["reason"], "completion_review_required")

    def test_trusted_memory_contract_does_not_hide_failed_final_generation(self):
        contract = {"version": 1, "kind": "memory_correction", "required": [{
            "effect_kind": "MEMORY_MUTATION", "memory_key": "weekly_format",
            "expected_revision": 2, "value": {"format": "short bullets"},
        }]}
        final, writes = self.run_finalizer({
            "task_id": "task-1", "state": "RUNNING",
            "checkpoint": {"trusted_completion_contract": contract},
            "effects": [{"effect_id": "memory-fx", "effect_kind": "MEMORY_MUTATION",
                         "state": "CONFIRMED"}],
        }, {"text": "", "provider_error": "upstream_timeout",
            "tool_calls": ["memory_correct"], "tool_evidence": []})
        self.assertEqual(final["state"], "WAITING")
        self.assertTrue(writes[0]["checkpoint"]["final_response_pending"])

    def test_provider_failure_after_confirmed_effect_waits_for_response_recovery(self):
        result = {"text": "", "provider_error": "upstream_http_400",
                  "tool_calls": ["commitment_submit"], "tool_evidence": []}
        final, writes = self.run_finalizer({
            "task_id": "task-1", "state": "RUNNING", "checkpoint": {},
            "effects": [{"effect_id": "effect-1", "effect_kind": "EXTERNAL_COMMITMENT", "state": "CONFIRMED"}],
        }, result)
        self.assertEqual(final["state"], "WAITING")
        self.assertTrue(writes[0]["checkpoint"]["final_response_pending"])

    def test_missing_claim_keeps_confirmed_write_recoverable_for_review(self):
        result = {"text": "The operation was confirmed.", "tool_calls": ["commitment_submit"],
                  "tool_evidence": [{"kind": "tool_evidence", "tool": "commitment_submit",
                                     "status": "ok", "state": "CONFIRMED", "effect_id": "fx-1"}]}
        final, writes = self.run_finalizer({
            "task_id": "task-1", "state": "RUNNING", "checkpoint": {},
            "effects": [{"effect_id": "fx-1", "effect_kind": "EXTERNAL_COMMITMENT", "state": "CONFIRMED"}],
        }, result)
        self.assertEqual(final["state"], "WAITING")
        self.assertTrue(writes[0]["checkpoint"]["completion_review_required"])

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

    def test_reconciled_waiting_task_can_resume_after_fresh_terminal_effect_read(self):
        state = {
            "task_id": "task-1", "state": "WAITING",
            "checkpoint": {"summary": "Outcome needs reconciliation", "completed": [],
                           "pending": [], "effect_outcome_uncertain": True},
            "effects": [{"effect_id": "fx-1", "effect_kind": "EXTERNAL_COMMITMENT",
                         "state": "CONFIRMED"}],
        }
        saved = []

        def fake_gateway_call(name, arguments, token, task_id, evidence=None, trusted_internal=False):
            if name == "task_resume":
                return dict(state)
            if name == "task_checkpoint":
                saved.append(arguments)
                state.update({"state": arguments["state"], "checkpoint": arguments["checkpoint"]})
                return dict(state)
            raise AssertionError(name)

        with patch.object(api, "gateway_call", side_effect=fake_gateway_call):
            result = api.transition_task("fixture-token-amber", "task-1", "RUNNING", [], resume=True)
        self.assertEqual(result["state"], "RUNNING")
        self.assertNotIn("effect_outcome_uncertain", saved[0]["checkpoint"])
        self.assertTrue(saved[0]["_orchestrator_resume"])

    def test_uncertain_effect_marker_is_preserved_until_effect_is_terminal(self):
        state = {
            "task_id": "task-1", "state": "WAITING",
            "checkpoint": {"summary": "Outcome needs reconciliation", "completed": [],
                           "pending": [], "effect_outcome_uncertain": True},
            "effects": [{"effect_id": "fx-1", "effect_kind": "EXTERNAL_COMMITMENT",
                         "state": "QUARANTINED"}],
        }
        saved = []

        def fake_gateway_call(name, arguments, token, task_id, evidence=None, trusted_internal=False):
            if name == "task_resume":
                return dict(state)
            if name == "task_checkpoint":
                saved.append(arguments)
                state.update({"state": arguments["state"], "checkpoint": arguments["checkpoint"]})
                return dict(state)
            raise AssertionError(name)

        with patch.object(api, "gateway_call", side_effect=fake_gateway_call):
            api.transition_task("fixture-token-amber", "task-1", "RUNNING", [], resume=True)
        self.assertTrue(saved[0]["checkpoint"]["effect_outcome_uncertain"])


if __name__ == "__main__":
    unittest.main()
