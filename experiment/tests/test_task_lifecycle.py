import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contracts.task_lifecycle import (
    commitment_digest,
    decide_turn_finalization,
    normalize_completion_contract,
    validate_finalization,
    validate_trusted_effect_contract,
)


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
                         ("WAITING", "completion_review_required"))
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
            "write evidence must identify its persisted effect")
        self.assertEqual(decide_turn_finalization(
            "RUNNING", "provider failed", evidence, claim, turn_error="upstream_http_400"),
            ("WAITING", "memory_effect_evidence_unproven"))

    def test_task_linked_memory_effect_requires_exact_canonical_value(self):
        claim = {"completed": ["preference corrected"], "pending": []}
        task = {"task_id": "task-a", "user_id": "user-a", "domain_id": "domain-a"}
        effect = {
            "effect_id": "memory-effect-1", "task_id": "task-a", "user_id": "user-a",
            "domain_id": "domain-a", "effect_kind": "MEMORY_MUTATION", "resource_key": "memory:answer_style",
            "state": "CONFIRMED", "request": {
                "operation": "memory_correct", "memory_key": "answer_style",
                "expected_revision": 3, "expected_value": {"style": "paragraphs"},
                "value": {"style": "short bullets"},
            }, "result": {"memory_key": "answer_style", "value": {"style": "short bullets"}, "revision": 4},
        }
        proof = {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
                 "tool_evidence": [{"tool": "memory_correct", "status": "ok", "state": "CONFIRMED",
                                    "effect_id": "memory-effect-1", "memory_key": "answer_style",
                                    "memory_revision": 4}]}
        canonical = {"memory-effect-1": {"memory_key": "answer_style", "value": {"style": "short bullets"},
                                         "revision": 4}}
        self.assertIsNone(validate_finalization(proof, claim, [effect], task, canonical))
        wrong_identity = {**effect, "user_id": "user-b"}
        self.assertEqual(validate_finalization(proof, claim, [wrong_identity], task, canonical),
                         "persisted effect lacks matching verified write evidence")
        wrong_value = {"memory-effect-1": {"memory_key": "answer_style", "value": {"style": "paragraphs"},
                                            "revision": 4}}
        self.assertEqual(validate_finalization(proof, claim, [effect], task, wrong_value),
                         "persisted effect lacks matching verified write evidence")

    def test_memory_write_requires_task_linked_canonical_effect(self):
        claim = {"completed": ["save preference"], "pending": []}
        task = {"task_id": "task-a", "user_id": "user-a", "domain_id": "domain-a"}
        effect = {
            "effect_id": "memory-effect-write", "task_id": "task-a", "user_id": "user-a",
            "domain_id": "domain-a", "effect_kind": "MEMORY_MUTATION",
            "resource_key": "memory:answer_style", "state": "CONFIRMED",
            "request": {"operation": "memory_write", "memory_key": "answer_style",
                        "value": {"style": "short bullets"}},
            "result": {"memory_key": "answer_style", "value": {"style": "short bullets"}, "revision": 1},
        }
        proof = {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
                 "tool_evidence": [{"tool": "memory_write", "status": "ok", "state": "CONFIRMED",
                                    "effect_id": "memory-effect-write", "memory_key": "answer_style",
                                    "memory_revision": 1}]}
        canonical = {"memory-effect-write": {"memory_key": "answer_style",
                                              "value": {"style": "short bullets"}, "revision": 1}}
        self.assertIsNone(validate_finalization(proof, claim, [effect], task, canonical))
        self.assertEqual(validate_finalization(proof, claim, [effect], task, {}),
                         "persisted effect lacks matching verified write evidence")

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

    def test_missing_effectful_claim_is_recoverable_not_terminal_failure(self):
        state, reason = decide_turn_finalization(
            "RUNNING", "Confirmed.", [], None,
            effect_records=[{"state": "CONFIRMED"}],
        )
        self.assertEqual((state, reason), ("WAITING", "completion_review_required"))

    def test_confirmed_effect_with_provider_failure_waits_for_user_response(self):
        state, reason = decide_turn_finalization(
            "RUNNING", "", [], None,
            effect_records=[{"state": "CONFIRMED"}], turn_error="upstream_http_400",
        )
        self.assertEqual((state, reason), ("WAITING", "final_response_pending"))

    def test_trusted_exact_contract_matches_task_effect_approval_and_canonical_state(self):
        target, details, task_id, effect_id, approval_id = (
            "unit-target", "Reserve the exact synthetic appointment", "task-1", "effect-1", "approval-1"
        )
        contract = normalize_completion_contract({
            "version": 1, "kind": "external_commitment_set",
            "required": [{"effect_kind": "EXTERNAL_COMMITMENT", "target_id": target, "details": details}],
        })
        digest = commitment_digest(target, details)
        effect = {
            "effect_id": effect_id, "task_id": task_id, "user_id": "user-amber", "domain_id": "domain-amber",
            "effect_kind": "EXTERNAL_COMMITMENT", "resource_key": f"commitment:{target}", "state": "CONFIRMED",
            "request": {"target_id": target, "details": details, "effect_digest": digest, "approval_id": approval_id},
        }
        approval = {
            "task_id": task_id, "user_id": "user-amber", "domain_id": "domain-amber", "target_id": target,
            "effect_digest": digest, "created_at": 1, "expires_at": 3, "consumed_at": 2,
        }
        canonical = {effect_id: {"state": "ACCEPTED", "effect_id": effect_id,
                                 "target_id": target, "receive_count": 1}}
        identity = {"task_id": task_id, "user_id": "user-amber", "domain_id": "domain-amber"}
        approvals = {approval_id: approval}
        self.assertIsNone(validate_trusted_effect_contract(contract, identity, [effect], approvals, canonical))

        for changed in (
            dict(effect, task_id="other-task"),
            dict(effect, user_id="user-cobalt"),
            dict(effect, request={**effect["request"], "target_id": "other-target"}),
        ):
            self.assertIsNotNone(validate_trusted_effect_contract(contract, identity, [changed], approvals, canonical))
        self.assertIsNotNone(validate_trusted_effect_contract(
            contract, identity, [dict(effect, effect_id="other-effect")], approvals, canonical,
        ))
        self.assertIsNotNone(validate_trusted_effect_contract(
            contract, identity, [effect], {approval_id: {**approval, "user_id": "user-cobalt"}}, canonical,
        ))
        self.assertIsNotNone(validate_trusted_effect_contract(
            contract, identity, [effect], approvals,
            {effect_id: {**canonical[effect_id], "state": "NOT_RECEIVED"}},
        ))

    def test_trusted_contract_requires_every_effect_and_rejects_unapproved_operations(self):
        target = "unit-target"
        contract = normalize_completion_contract({
            "version": 1, "kind": "external_commitment_set",
            "required": [
                {"effect_kind": "EXTERNAL_COMMITMENT", "target_id": target, "details": "one"},
                {"effect_kind": "EXTERNAL_COMMITMENT", "target_id": "unit-target-two", "details": "two"},
            ],
        })
        self.assertIsNotNone(validate_trusted_effect_contract(contract, {
            "task_id": "task-1", "user_id": "user-amber", "domain_id": "domain-amber",
        }, [], {}, {}))


if __name__ == "__main__":
    unittest.main()
