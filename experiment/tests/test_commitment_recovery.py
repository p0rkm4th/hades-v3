"""Fault-injected recovery test for a dispatch whose acknowledgment was lost."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
import unittest
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contracts.task_lifecycle import normalize_completion_contract


BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
DATABASE_URL = os.environ["DATABASE_URL"]
AMBER = "fixture-token-amber"
DETAILS = "Reserve the synthetic appointment slot for Amber at 16:00"


def request(method: str, path: str, token: str | None = None, body: dict | None = None,
            orchestrator: bool = False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if orchestrator:
        headers["X-Hades-Orchestrator"] = os.environ["ORCHESTRATOR_SECRET"]
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


class CommitmentRecovery(unittest.TestCase):
    def create_bounded_task(self, target_details):
        contract = {"version": 1, "kind": "external_commitment_set", "required": [
            {"effect_kind": "EXTERNAL_COMMITMENT", "target_id": target, "details": details}
            for target, details in target_details
        ]}
        status, task = request("POST", "/v1/tasks", AMBER, {
            "goal": "Reserve the explicitly approved synthetic appointment operation",
            "completion_contract": contract,
        })
        self.assertEqual(status, 403, task)
        status, task = request("POST", "/v1/tasks", AMBER, {
            "goal": "Reserve the explicitly approved synthetic appointment operation",
            "completion_contract": contract,
        }, orchestrator=True)
        self.assertEqual(status, 201, task)
        return task, contract

    def approve(self, task_id, target, details, behavior="ACCEPT_ACK_LOST"):
        digest = hashlib.sha256(json.dumps(
            {"target_id": target, "details": details}, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT domain_id FROM tasks WHERE task_id=%s", (task_id,))
            domain_id = cur.fetchone()[0]
            cur.execute("INSERT INTO commitment_targets (target_id,behavior) VALUES (%s,%s)",
                        (target, behavior))
            cur.execute(
                "INSERT INTO commitment_approvals "
                "(user_id,domain_id,task_id,target_id,effect_digest,approved_by,expires_at) "
                "VALUES ('user-amber',%s,%s,%s,%s,'cp73-test',now()+interval '5 minutes') "
                "RETURNING approval_id",
                (domain_id, task_id, target, digest),
            )
            approval_id = str(cur.fetchone()[0])
        return approval_id, digest

    def complete_without_model_trace(self, task_id, response="The appointment is confirmed.", provider_error=None):
        proof = {
            "task_type": "EFFECTFUL", "response_nonempty": bool(response),
            "completion_claim": False, "tool_evidence": [], "response": response,
            "provider_error": provider_error,
        }
        return request("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED",
            "checkpoint": {"summary": "Trusted required actions verified", "completed": ["bounded success criteria"], "pending": []},
            "_orchestrator_finalization": proof,
        }, orchestrator=True)

    def test_canonical_recovery_completes_with_persisted_contract_not_model_claim(self):
        target = "cp73-complete-" + uuid.uuid4().hex[:12]
        task, contract = self.create_bounded_task([(target, DETAILS)])
        task_id = task["task_id"]
        status, tamper = request("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "RUNNING", "checkpoint": {
                "summary": "attempt to replace objective", "completed": [], "pending": [],
                "trusted_completion_contract": {"version": 1, "kind": "external_commitment_set", "required": []},
            },
        })
        self.assertEqual(status, 409)
        self.assertIn("immutable", tamper["error"])
        approval_id, _ = self.approve(task_id, target, DETAILS)
        status, submitted = request("POST", "/v1/commitments", AMBER, {
            "task_id": task_id, "target_id": target, "details": DETAILS,
            "approval_id": approval_id,
        })
        self.assertEqual(status, 202, submitted)
        effect_id = submitted["effect_id"]
        status, recovered = request("POST", f"/v1/commitments/{effect_id}/reconcile", AMBER, {})
        self.assertEqual(status, 200, recovered)
        self.assertEqual(recovered["effect_id"], effect_id)
        for _ in range(2):
            status, replayed = request("POST", "/v1/commitments", AMBER, {
                "task_id": task_id, "target_id": target, "details": DETAILS,
                "approval_id": approval_id,
            })
            self.assertEqual(status, 200, replayed)
            self.assertEqual(replayed["effect_id"], effect_id)
            self.assertTrue(replayed["already_recorded"])

        # No model tool trace survives this simulated restart. The gateway must
        # use the immutable task criterion, effect/approval rows, and canonical target.
        status, before_finalize = request("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(before_finalize["state"], "RUNNING")
        status, rejected_delivery = self.complete_without_model_trace(
            task_id, "The appointment is confirmed.", provider_error="upstream_http_400",
        )
        self.assertEqual(status, 409)
        self.assertIn("successful final response", rejected_delivery["error"])
        status, completed = self.complete_without_model_trace(task_id)
        self.assertEqual(status, 200, completed)
        self.assertEqual(completed["state"], "COMPLETED")
        self.assertEqual(completed["checkpoint"]["trusted_completion_contract"],
                         normalize_completion_contract(contract))
        self.assertEqual(completed["checkpoint"]["final_response"], "The appointment is confirmed.")
        self.assertEqual(completed["checkpoint"]["response_delivery"], "PERSISTED_PENDING_DELIVERY")

        status, replay = self.complete_without_model_trace(task_id, "A contradictory replacement answer.")
        self.assertEqual(status, 200)
        self.assertEqual(replay["checkpoint"]["final_response"], "The appointment is confirmed.")
        status, terminal_replay = request("POST", "/v1/commitments", AMBER, {
            "task_id": task_id, "target_id": target, "details": DETAILS,
            "approval_id": approval_id,
        })
        self.assertEqual(status, 409)
        status, denied_resume = request("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "RUNNING", "checkpoint": {"summary": "resume", "completed": [], "pending": []},
            "_orchestrator_resume": True,
        }, orchestrator=True)
        self.assertEqual(status, 409)
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT accepted_effect_id,receive_count FROM commitment_targets WHERE target_id=%s", (target,))
            accepted_id, count = cur.fetchone()
        self.assertEqual(str(accepted_id), effect_id)
        self.assertEqual(count, 1)

    def test_one_of_two_confirmed_effects_cannot_complete_trusted_task(self):
        target1, target2 = "cp73-part-a-" + uuid.uuid4().hex[:8], "cp73-part-b-" + uuid.uuid4().hex[:8]
        details1, details2 = "First requested appointment", "Second requested appointment"
        task, _ = self.create_bounded_task([(target1, details1), (target2, details2)])
        task_id = task["task_id"]
        approval_id, _ = self.approve(task_id, target1, details1)
        status, submitted = request("POST", "/v1/commitments", AMBER, {
            "task_id": task_id, "target_id": target1, "details": details1,
            "approval_id": approval_id,
        })
        self.assertEqual(status, 202, submitted)
        effect_id = submitted["effect_id"]
        status, _ = request("POST", f"/v1/commitments/{effect_id}/reconcile", AMBER, {})
        self.assertEqual(status, 200)
        status, rejected = self.complete_without_model_trace(task_id, "Both appointments are complete.")
        self.assertEqual(status, 409)
        self.assertIn("exactly match required operations", rejected["error"])
        status, unchanged = request("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(unchanged["state"], "RUNNING")

    def test_uncertain_or_unreceived_operation_cannot_complete(self):
        target = "cp73-uncertain-" + uuid.uuid4().hex[:10]
        task, _ = self.create_bounded_task([(target, DETAILS)])
        task_id = task["task_id"]
        approval_id, digest = self.approve(task_id, target, DETAILS)
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT domain_id FROM tasks WHERE task_id=%s", (task_id,))
            domain_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO effects "
                "(task_id,user_id,domain_id,effect_kind,resource_key,state,request) "
                "VALUES (%s,'user-amber',%s,'EXTERNAL_COMMITMENT',%s,'DISPATCHED',%s) "
                "RETURNING effect_id",
                (task_id, domain_id, f"commitment:{target}", Jsonb({
                    "target_id": target, "details": DETAILS,
                    "effect_digest": digest, "approval_id": approval_id,
                })),
            )
            effect_id = str(cur.fetchone()[0])
        status, pending = request("POST", f"/v1/commitments/{effect_id}/reconcile", AMBER, {})
        self.assertEqual(status, 202, pending)
        self.assertEqual(pending["state"], "QUARANTINED")
        status, finalization = self.complete_without_model_trace(task_id)
        self.assertEqual(status, 409)
        self.assertIn("exact required operation", finalization["error"])
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT receive_count FROM commitment_targets WHERE target_id=%s", (target,))
            self.assertEqual(cur.fetchone()[0], 0)

    def test_not_yet_visible_effect_stays_quarantined_without_replay(self):
        target = "cp72-pending-" + uuid.uuid4().hex[:16]
        status, task = request("POST", "/v1/tasks", AMBER, {
            "goal": "CP72 synthetic recovery: keep unobservable dispatch pending"
        })
        self.assertEqual(status, 201, task)
        task_id = task["task_id"]
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT domain_id FROM tasks WHERE task_id=%s", (task_id,))
            domain_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO commitment_targets (target_id,behavior) VALUES (%s,'ACCEPT_ACK_LOST')",
                (target,),
            )
            cur.execute(
                "INSERT INTO effects "
                "(task_id,user_id,domain_id,effect_kind,resource_key,state,request) "
                "VALUES (%s,'user-amber',%s,'EXTERNAL_COMMITMENT',%s,'DISPATCHED',%s) "
                "RETURNING effect_id",
                (task_id, domain_id, f"commitment:{target}", Jsonb({"target_id": target})),
            )
            effect_id = str(cur.fetchone()[0])

        status, pending = request(
            "POST", f"/v1/commitments/{urllib.parse.quote(effect_id, safe='')}/reconcile",
            AMBER, {},
        )
        self.assertEqual(status, 202, pending)
        self.assertEqual(pending["state"], "QUARANTINED")
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT state FROM effects WHERE effect_id=%s", (effect_id,))
            self.assertEqual(cur.fetchone()[0], "QUARANTINED")
            cur.execute(
                "SELECT accepted_effect_id,receive_count FROM commitment_targets WHERE target_id=%s",
                (target,),
            )
            self.assertEqual(cur.fetchone(), (None, 0))

        # A later reconciliation still cannot dispatch the operation.
        status, repeated = request(
            "POST", f"/v1/commitments/{urllib.parse.quote(effect_id, safe='')}/reconcile",
            AMBER, {},
        )
        self.assertEqual(status, 202, repeated)
        self.assertEqual(repeated["state"], "QUARANTINED")
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT receive_count FROM commitment_targets WHERE target_id=%s", (target,))
            self.assertEqual(cur.fetchone()[0], 0)

    def test_dispatch_and_reconciliation_failures_recover_without_redispatch(self):
        target = "cp72-recovery-" + uuid.uuid4().hex[:16]
        status, task = request("POST", "/v1/tasks", AMBER, {
            "goal": "CP72 synthetic recovery: reconcile the one authorized appointment commitment"
        })
        self.assertEqual(status, 201, task)
        task_id = task["task_id"]
        digest = hashlib.sha256(json.dumps(
            {"target_id": target, "details": DETAILS}, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()

        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT domain_id FROM tasks WHERE task_id=%s AND user_id='user-amber'",
                (task_id,),
            )
            domain_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO commitment_targets (target_id,behavior) VALUES (%s,'ACCEPT_ACK_LOST')",
                (target,),
            )
            cur.execute(
                "INSERT INTO commitment_approvals "
                "(user_id,domain_id,task_id,target_id,effect_digest,approved_by,expires_at) "
                "VALUES ('user-amber',%s,%s,%s,%s,'cp72-test',now()+interval '5 minutes') "
                "RETURNING approval_id",
                (domain_id, task_id, target, digest),
            )
            approval_id = str(cur.fetchone()[0])

        status, submitted = request("POST", "/v1/commitments", AMBER, {
            "task_id": task_id, "target_id": target, "details": DETAILS,
            "approval_id": approval_id,
        })
        self.assertEqual(status, 202, submitted)
        self.assertEqual(submitted["state"], "QUARANTINED")
        effect_id = submitted["effect_id"]

        # Model the crash window after the simulator committed and before the
        # gateway durably changed DISPATCHED to QUARANTINED.
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE effects SET state='DISPATCHED' WHERE effect_id=%s AND task_id=%s",
                (effect_id, task_id),
            )
            self.assertEqual(cur.rowcount, 1)

        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE commitment_targets SET reconcile_failures_remaining=1 WHERE target_id=%s",
                (target,),
            )
        status, interrupted_reconciliation = request(
            "POST", f"/v1/commitments/{urllib.parse.quote(effect_id, safe='')}/reconcile",
            AMBER, {},
        )
        self.assertEqual(status, 202, interrupted_reconciliation)
        self.assertEqual(interrupted_reconciliation["state"], "QUARANTINED")
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT state FROM effects WHERE effect_id=%s", (effect_id,))
            self.assertEqual(cur.fetchone()[0], "QUARANTINED")

        # Repeated resume/reconciliation settles the same ledger row after the
        # one-shot upstream response failure. No tool call is replayed here.
        status, recovered = request(
            "POST", f"/v1/commitments/{urllib.parse.quote(effect_id, safe='')}/reconcile",
            AMBER, {},
        )
        self.assertEqual(status, 200, recovered)
        self.assertEqual(recovered["effect_id"], effect_id)
        self.assertEqual(recovered["state"], "CONFIRMED")
        self.assertEqual(recovered["reconciled_target_state"]["receive_count"], 1)

        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT state,task_id FROM effects WHERE effect_id=%s", (effect_id,)
            )
            self.assertEqual(cur.fetchone(), ("CONFIRMED", uuid.UUID(task_id)))
            cur.execute(
                "SELECT accepted_effect_id,receive_count FROM commitment_targets WHERE target_id=%s",
                (target,),
            )
            accepted_id, receive_count = cur.fetchone()
        self.assertEqual(str(accepted_id), effect_id)
        self.assertEqual(receive_count, 1)

        status, same_operation = request("POST", "/v1/commitments", AMBER, {
            "task_id": task_id, "target_id": target, "details": DETAILS,
            "approval_id": approval_id,
        })
        self.assertEqual(status, 200, same_operation)
        self.assertEqual(same_operation["effect_id"], effect_id)
        self.assertTrue(same_operation["already_recorded"])
        self.assertEqual(same_operation["state"], "CONFIRMED")

        # Repeated recovery observes a terminal effect; it cannot redispatch it.
        status, rejected = request(
            "POST", f"/v1/commitments/{urllib.parse.quote(effect_id, safe='')}/reconcile",
            AMBER, {},
        )
        self.assertEqual(status, 409, rejected)
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("SELECT receive_count FROM commitment_targets WHERE target_id=%s", (target,))
            self.assertEqual(cur.fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
