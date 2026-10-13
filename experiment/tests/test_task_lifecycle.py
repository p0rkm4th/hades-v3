import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contracts.task_lifecycle import decide_turn_finalization, validate_finalization


class TaskLifecycleContract(unittest.TestCase):
    def test_successful_read_response_completes_with_read_evidence(self):
        claim = {"completed": ["read source and report result"], "pending": []}
        state, reason = decide_turn_finalization(
            "RUNNING", "The source reports unavailable.",
            [{"tool": "infrastructure_read", "status": "ok"}],
            claim,
        )
        self.assertEqual((state, reason), ("COMPLETED", "successful_read_response"))
        self.assertEqual(
            decide_turn_finalization("RUNNING", "The source reports unavailable.", [{"tool": "infrastructure_read", "status": "ok"}], None)[0],
            "FAILED",
        )

    def test_successful_write_requires_claim_and_verified_write(self):
        evidence = [{
            "tool": "shopping_list_change", "status": "ok", "state": "CONFIRMED",
            "verified_after": [{"name": "Eggs", "amount": 2}],
        }]
        state, reason = decide_turn_finalization("RUNNING", "Updated.", evidence, None)
        self.assertEqual((state, reason), ("FAILED", "write_completion_not_claimed"))
        state, reason = decide_turn_finalization(
            "RUNNING", "Updated.", evidence, {"completed": ["list change verified"], "pending": []},
        )
        self.assertEqual((state, reason), ("COMPLETED", "verified_write_and_explicit_completion"))
        proof = {
            "response_nonempty": True, "completion_claim": True,
            "tool_evidence": evidence,
        }
        self.assertIsNone(validate_finalization(proof, {"completed": ["change"], "pending": []}, ["CONFIRMED"]))
        read_only_proof = {
            "response_nonempty": True, "completion_claim": True,
            "tool_evidence": [{"tool": "inventory_read", "status": "ok"}],
        }
        self.assertIn(
            "each task effect requires corresponding write evidence",
            validate_finalization(read_only_proof, {"completed": ["change"], "pending": []}, ["CONFIRMED"]),
        )

    def test_partial_completion_keeps_authorized_work_running(self):
        state, reason = decide_turn_finalization(
            "RUNNING", "The first step is done.",
            [{"tool": "infrastructure_read", "status": "ok"}],
            {"completed": ["read source"], "pending": ["verify second source"]},
        )
        self.assertEqual((state, reason), ("RUNNING", "authorized_steps_remain"))

    def test_tool_error_and_interruption_do_not_complete(self):
        state, reason = decide_turn_finalization(
            "RUNNING", "I could not read it.",
            [{"tool": "infrastructure_read", "status": "error"}], None,
        )
        self.assertEqual((state, reason), ("FAILED", "tool_error_prevents_completion"))
        self.assertEqual(
            decide_turn_finalization("RUNNING", None, [], None),
            ("FAILED", "no_final_model_response"),
        )

    def test_approval_and_uncertain_effects_wait_for_resolution(self):
        self.assertEqual(
            decide_turn_finalization("RUNNING", "Needs approval.", [{"approval_pending": True}], None)[0],
            "WAITING",
        )
        self.assertEqual(
            decide_turn_finalization("RUNNING", "Checking outcome.", [{"uncertain": True}], None)[0],
            "WAITING",
        )
        self.assertEqual(
            decide_turn_finalization("RUNNING", "Done.", [{"tool": "shopping_list_read", "status": "ok"}], None, ["QUARANTINED"])[0],
            "WAITING",
        )

    def test_existing_terminal_and_waiting_states_are_preserved(self):
        for state in ("WAITING", "FAILED", "COMPLETED", "CANCELLED"):
            with self.subTest(state=state):
                self.assertEqual(
                    decide_turn_finalization(state, "Done.", [{"tool": "infrastructure_read", "status": "ok"}], None)[0],
                    state,
                )

    def test_resumed_task_needs_fresh_evidence_and_completion_claim(self):
        claim = {"completed": ["second step verified"], "pending": []}
        self.assertEqual(
            decide_turn_finalization("RUNNING", "Resumed and checked.", [{"tool": "infrastructure_read", "status": "ok"}], claim, ["CONFIRMED"])[0],
            "COMPLETED",
        )
        self.assertEqual(
            decide_turn_finalization("RUNNING", "Still checking.", [], claim, ["QUARANTINED"])[0],
            "WAITING",
        )

    def test_gateway_completion_requires_orchestrator_evidence(self):
        reason = validate_finalization(
            {"response_nonempty": True, "tool_evidence": []},
            {"completed": ["read"], "pending": []}, [],
        )
        self.assertEqual(reason, "a completion claim is required")
        proof = {
            "response_nonempty": True, "completion_claim": True,
            "tool_evidence": [{"tool": "infrastructure_read", "status": "ok"}],
        }
        self.assertIsNone(validate_finalization(proof, {"completed": ["read"], "pending": []}, []))


if __name__ == "__main__":
    unittest.main()
