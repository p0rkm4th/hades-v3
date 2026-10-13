import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contracts.task_lifecycle import decide_turn_finalization, validate_finalization


class TaskLifecycleContract(unittest.TestCase):
    def test_read_only_response_completes_from_verified_read_without_model_claim(self):
        evidence = [{"tool": "infrastructure_read", "status": "ok"}]
        self.assertEqual(decide_turn_finalization("RUNNING", "Health is unknown.", evidence, None),
                         ("COMPLETED", "successful_read_response"))

    def test_claim_without_read_or_write_evidence_is_rejected(self):
        claim = {"completed": ["answer"], "pending": []}
        self.assertEqual(decide_turn_finalization("RUNNING", "Done.", [], claim),
                         ("FAILED", "completion_without_verified_outcome"))
        self.assertEqual(validate_finalization(
            {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True, "tool_evidence": []},
            claim, []), "completion requires verified read or write evidence")

    def test_effectful_completion_requires_explicit_claim_and_matching_identity(self):
        claim = {"completed": ["write verified"], "pending": []}
        evidence = [{"tool": "shopping_list_change", "status": "ok", "state": "CONFIRMED",
                     "effect_id": "effect-a", "verified_after": [{"name": "Eggs", "amount": 2}]}]
        self.assertEqual(decide_turn_finalization("RUNNING", "Updated.", evidence, None),
                         ("FAILED", "write_completion_not_claimed"))
        effect = {"effect_id": "effect-a", "effect_kind": "GROCERY_LIST", "state": "CONFIRMED"}
        proof = {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True, "tool_evidence": evidence}
        self.assertIsNone(validate_finalization(proof, claim, [effect]))

    def test_memory_write_waits_for_task_linked_durable_effect_record(self):
        claim = {"completed": ["memory stored"], "pending": []}
        evidence = [{"tool": "memory_write", "status": "ok", "state": "CONFIRMED", "memory_key": "x"}]
        self.assertEqual(decide_turn_finalization("RUNNING", "Stored.", evidence, claim),
                         ("WAITING", "memory_effect_evidence_unproven"))
        self.assertEqual(validate_finalization(
            {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
             "tool_evidence": evidence}, claim, []),
            "memory write completion is unproven without a task-linked durable effect record")
        self.assertEqual(decide_turn_finalization(
            "RUNNING", "provider failed", evidence, claim, turn_error="upstream_http_400"),
            ("WAITING", "memory_effect_evidence_unproven"))

    def test_wrong_or_missing_effect_id_is_rejected_even_when_counts_match(self):
        claim = {"completed": ["write"], "pending": []}
        effect = {"effect_id": "persisted-1", "effect_kind": "GROCERY_LIST", "state": "CONFIRMED"}
        base = {"tool": "shopping_list_change", "status": "ok", "state": "CONFIRMED",
                "verified_after": [{"name": "Eggs"}]}
        for item in (dict(base, effect_id="different"), base):
            with self.subTest(effect_id=item.get("effect_id")):
                self.assertEqual(validate_finalization(
                    {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
                     "tool_evidence": [item]}, claim, [effect]),
                    ("write evidence must identify its persisted effect" if not item.get("effect_id") else "write evidence must match each persisted effect ID exactly"))

    def test_extra_effect_evidence_and_wrong_tool_are_rejected(self):
        claim = {"completed": ["write"], "pending": []}
        effect = {"effect_id": "a", "effect_kind": "GROCERY_LIST", "state": "CONFIRMED"}
        item = {"tool": "workspace_exec", "status": "ok", "state": "CONFIRMED", "effect_id": "a", "exit_code": 0}
        proof = {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
                 "tool_evidence": [item, dict(item, effect_id="extra")]}
        self.assertEqual(validate_finalization(proof, claim, [effect]), "write evidence must match each persisted effect ID exactly")
        proof["tool_evidence"] = [item]
        self.assertEqual(validate_finalization(proof, claim, [effect]), "persisted effect lacks matching verified write evidence")

    def test_partial_errors_interruption_and_uncertain_or_approval_states(self):
        self.assertEqual(decide_turn_finalization("RUNNING", "First done.",
            [{"kind": "progress_checkpoint", "checkpoint": {"pending": ["second"]}},
             {"tool": "infrastructure_read", "status": "ok"}], None)[0], "RUNNING")
        self.assertEqual(decide_turn_finalization("RUNNING", "provider failed",
            [{"kind": "progress_checkpoint", "checkpoint": {"pending": ["second"]}},
             {"tool": "infrastructure_read", "status": "ok"}], None,
            turn_error="upstream_http_400"), ("RUNNING", "authorized_steps_remain"))
        self.assertEqual(decide_turn_finalization("RUNNING", "Failed.", [{"tool": "infrastructure_read", "status": "error"}], None)[0], "FAILED")
        self.assertEqual(decide_turn_finalization("RUNNING", None, [], None), ("FAILED", "no_final_model_response"))
        self.assertEqual(decide_turn_finalization("RUNNING", "Need approval.", [{"approval_pending": True}], None)[0], "WAITING")
        self.assertEqual(decide_turn_finalization("RUNNING", "Unsure.", [{"uncertain": True}], None)[0], "WAITING")
        self.assertEqual(decide_turn_finalization("RUNNING", "Rejected.", [], None,
                         effect_records=[{"state": "REJECTED"}]), ("FAILED", "effect_failed"))
        reconciled = [
            {"tool": "commitment_submit", "status": "error", "state": "QUARANTINED", "effect_id": "commit-1", "uncertain": True},
            {"tool": "commitment_reconcile", "status": "ok", "state": "CONFIRMED", "effect_id": "commit-1"},
        ]
        self.assertEqual(decide_turn_finalization("RUNNING", "Confirmed.", reconciled,
                         {"completed": ["commitment confirmed"], "pending": []},
                         effect_records=[{"state": "CONFIRMED"}]),
                         ("COMPLETED", "verified_write_and_explicit_completion"))

    def test_existing_states_and_resumed_task(self):
        for state in ("WAITING", "FAILED", "COMPLETED", "CANCELLED"):
            self.assertEqual(decide_turn_finalization(state, "Done.", [{"tool": "infrastructure_read", "status": "ok"}], None)[0], state)
        self.assertEqual(decide_turn_finalization("RUNNING", "Resumed.",
            [{"tool": "infrastructure_read", "status": "ok"}], None), ("COMPLETED", "successful_read_response"))
        self.assertEqual(decide_turn_finalization("RUNNING", "Done.", [], None, ["QUARANTINED"])[0], "WAITING")


if __name__ == "__main__":
    unittest.main()
