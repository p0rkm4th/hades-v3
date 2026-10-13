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

import psycopg
from psycopg.types.json import Jsonb


BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
DATABASE_URL = os.environ["DATABASE_URL"]
AMBER = "fixture-token-amber"
DETAILS = "Reserve the synthetic appointment slot for Amber at 16:00"


def request(method: str, path: str, token: str | None = None, body: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


class CommitmentRecovery(unittest.TestCase):
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

    def test_dispatched_effect_reconciles_after_ack_persistence_interruption(self):
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
