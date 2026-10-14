import json
import hashlib
import os
import unittest
import urllib.error
import urllib.request
import uuid
import psycopg
from memory_diagnostics import correction_diagnostic_class, json_shape
from memory_schema import ensure_memory_revision


BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
AMBER = "fixture-token-amber"
COBALT = "fixture-token-cobalt"


def call(method, path, token=None, body=None, orchestrator=False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if orchestrator:
        headers["X-Hades-Orchestrator"] = os.environ["ORCHESTRATOR_SECRET"]
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def seed_memory_fixture(token, key, value):
    identity = {
        AMBER: ("user-amber", "domain-home-amber"),
        COBALT: ("user-cobalt", "domain-home-cobalt"),
    }[token]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scoped_memory (user_id,domain_id,memory_key,value) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (user_id,domain_id,memory_key) DO UPDATE SET value=EXCLUDED.value, "
            "revision=scoped_memory.revision+1,updated_at=now() RETURNING revision",
            (*identity, key, psycopg.types.json.Jsonb(value)),
        )
        return cur.fetchone()[0]


class GatewayIntegration(unittest.TestCase):
    def test_workspace_gateway_blocks_new_operations_for_waiting_tasks(self):
        status, task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Park workspace execution for operator review",
        })
        self.assertEqual(status, 201, task)
        task_id = task["task_id"]
        first_id = hashlib.sha256(f"{task_id}:confirmed-before-review".encode()).hexdigest()
        status, first = call("POST", "/v1/workspace/exec", AMBER, {
            "task_id": task_id, "command": "pwd", "operation_id": first_id,
        })
        self.assertEqual((status, first["state"]), (200, "CONFIRMED"), first)

        status, parked = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "WAITING",
            "checkpoint": {
                "summary": "Confirmed workspace operation needs review before continuation",
                "completed": ["original workspace operation"],
                "pending": ["operator review"],
                "operator_review_required": True,
            },
            "_orchestrator_finalization": {"reason": "workspace_resume_requires_persisted_identity"},
        }, orchestrator=True)
        self.assertEqual((status, parked["state"]), (200, "WAITING"), parked)

        status, replay = call("POST", "/v1/workspace/exec", AMBER, {
            "task_id": task_id, "command": "pwd", "operation_id": first_id,
        })
        self.assertEqual((status, replay.get("effect_id"), replay.get("already_recorded")),
                         (200, first["effect_id"], True))

        second_id = hashlib.sha256(f"{task_id}:new-after-review-park".encode()).hexdigest()
        status, rejected = call("POST", "/v1/workspace/exec", AMBER, {
            "task_id": task_id,
            "command": "python -c \"from pathlib import Path; Path('.cp90-should-not-run').write_text('x')\"",
            "operation_id": second_id,
        })
        self.assertEqual(status, 409, rejected)
        self.assertIn("running task", rejected["error"])
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT effect_id,state FROM effects WHERE task_id=%s AND effect_kind='WORKSPACE_COMMAND' ORDER BY created_at",
                (task_id,),
            )
            rows = cur.fetchall()
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual((str(rows[0][0]), rows[0][1]), (first["effect_id"], "CONFIRMED"))

        status, approval_task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Do not run workspace operations while approval is pending",
        })
        self.assertEqual(status, 201, approval_task)
        approval_task_id = approval_task["task_id"]
        status, parked = call("POST", f"/v1/tasks/{approval_task_id}/checkpoint", AMBER, {
            "state": "WAITING",
            "checkpoint": {
                "summary": "An approval is pending",
                "completed": [],
                "pending": ["operator approval"],
                "approval_pending": True,
            },
            "_orchestrator_finalization": {"reason": "approval_pending"},
        }, orchestrator=True)
        self.assertEqual((status, parked["state"]), (200, "WAITING"), parked)
        approval_op = hashlib.sha256(f"{approval_task_id}:unapproved".encode()).hexdigest()
        status, rejected = call("POST", "/v1/workspace/exec", AMBER, {
            "task_id": approval_task_id,
            "command": "python -c \"from pathlib import Path; Path('.cp90-approval-bypass').write_text('x')\"",
            "operation_id": approval_op,
        })
        self.assertEqual(status, 409, rejected)
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM effects WHERE task_id=%s AND effect_kind='WORKSPACE_COMMAND'",
                (approval_task_id,),
            )
            self.assertEqual(cur.fetchone()[0], 0)

    def test_workspace_operation_retry_is_bound_to_identity_and_quarantines_unknown(self):
        status, task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Write one synthetic workspace marker exactly once",
        })
        self.assertEqual(status, 201, task)
        task_id = task["task_id"]
        marker = f".cp81-operation-{task_id}.txt"
        command = (
            "python -c \"from pathlib import Path; p=Path('" + marker + "'); "
            "p.write_text((p.read_text() if p.exists() else '') + 'x')\""
        )
        operation_id = hashlib.sha256(f"{task_id}:tool-call-1".encode()).hexdigest()
        body = {"task_id": task_id, "command": command, "operation_id": operation_id}
        status, missing_identity = call("POST", "/v1/workspace/exec", AMBER, {
            "task_id": task_id, "command": command,
        })
        self.assertEqual(status, 400, missing_identity)

        status, first = call("POST", "/v1/workspace/exec", AMBER, body)
        self.assertEqual((status, first["state"]), (200, "CONFIRMED"), first)
        status, replay = call("POST", "/v1/workspace/exec", AMBER, body)
        self.assertEqual((status, replay["effect_id"], replay.get("already_recorded")),
                         (200, first["effect_id"], True))
        status, canonical_task = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(status, 200, canonical_task)
        identity_rows = [effect for effect in canonical_task["effects"] if effect["effect_id"] == first["effect_id"]]
        self.assertEqual(len(identity_rows), 1)
        self.assertEqual(identity_rows[0]["operation_id"], operation_id)
        status, changed = call("POST", "/v1/workspace/exec", AMBER,
                               {**body, "command": command + " "+"# changed"})
        self.assertEqual(status, 409, changed)

        read_id = hashlib.sha256(f"{task_id}:tool-call-read".encode()).hexdigest()
        read_command = f"python -c \"from pathlib import Path; print(Path('{marker}').read_text())\""
        status, observed = call("POST", "/v1/workspace/exec", AMBER, {
            "task_id": task_id, "command": read_command, "operation_id": read_id,
        })
        self.assertEqual(status, 200, observed)
        self.assertEqual(observed["stdout"].strip(), "x")
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT effect_id,state,request FROM effects WHERE task_id=%s "
                "AND effect_kind='WORKSPACE_COMMAND' AND request->>'operation_id'=%s",
                (task_id, operation_id),
            )
            rows = cur.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0][0], rows[0][1]), (uuid.UUID(first["effect_id"]), "CONFIRMED"))
            self.assertEqual(rows[0][2]["request_digest"], hashlib.sha256(
                json.dumps({"command": command}, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
            ).hexdigest())

        cleanup_command = f"python -c \"from pathlib import Path; Path('{marker}').unlink()\""
        cleanup_id = hashlib.sha256(f"{task_id}:cleanup".encode()).hexdigest()
        status, cleanup = call("POST", "/v1/workspace/exec", AMBER, {
            "task_id": task_id, "command": cleanup_command, "operation_id": cleanup_id,
        })
        self.assertEqual(status, 200, cleanup)

        status, unknown_task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Do not repeat an unresolved synthetic workspace operation",
        })
        self.assertEqual(status, 201, unknown_task)
        unknown_task_id = unknown_task["task_id"]
        unknown_operation = hashlib.sha256(f"{unknown_task_id}:interrupted-call".encode()).hexdigest()
        unknown_command = "python -c \"from pathlib import Path; Path('.unknown-marker').write_text('x')\""
        unknown_digest = hashlib.sha256(
            json.dumps({"command": unknown_command}, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO effects (task_id,user_id,domain_id,effect_kind,resource_key,state,request) "
                "VALUES (%s,'user-amber','domain-home-amber','WORKSPACE_COMMAND',%s,'DISPATCHED',%s) "
                "RETURNING effect_id",
                (unknown_task_id, "workspace:user-amber", psycopg.types.json.Jsonb({
                    "command": unknown_command,
                    "operation_id": unknown_operation,
                    "request_digest": unknown_digest,
                })),
            )
            unknown_effect_id = str(cur.fetchone()[0])
        for retry_id in (unknown_operation, hashlib.sha256(b"different-call").hexdigest()):
            status, quarantined = call("POST", "/v1/workspace/exec", AMBER, {
                "task_id": unknown_task_id,
                "command": unknown_command,
                "operation_id": retry_id,
            })
            self.assertEqual((status, quarantined["state"], quarantined["effect_id"]),
                             (202, "QUARANTINED", unknown_effect_id))
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*),MIN(state) FROM effects WHERE task_id=%s AND effect_kind='WORKSPACE_COMMAND'",
                        (unknown_task_id,))
            self.assertEqual(cur.fetchone(), (1, "QUARANTINED"))

    def test_memory_correction_diagnostics_are_structural_and_distinguish_mismatch(self):
        self.assertEqual(json_shape({"private-key-name": ["secret value"]}), "object:1:[array:1:[string]]")
        self.assertEqual(json_shape(True), "boolean")
        self.assertEqual(correction_diagnostic_class(0, 1, 0), "query_no_match")
        self.assertEqual(correction_diagnostic_class(1, 0, 0), "expected_value_no_match")
        self.assertEqual(correction_diagnostic_class(1, 1, 0), "query_and_value_match_different_rows")
        self.assertEqual(correction_diagnostic_class(1, 1, 1), "unique_match")
        self.assertEqual(correction_diagnostic_class(2, 2, 2), "ambiguous_intersection")

    def test_memory_revision_migration_upgrades_existing_and_fresh_schemas(self):
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute("CREATE TEMP TABLE scoped_memory (memory_key text, value jsonb)")
            cur.execute("INSERT INTO scoped_memory VALUES ('legacy-key', '{\"v\":1}')")
            ensure_memory_revision(cur)
            ensure_memory_revision(cur)
            cur.execute("SELECT revision FROM scoped_memory WHERE memory_key='legacy-key'")
            self.assertEqual(cur.fetchone()[0], 1)

    def test_memory_write_requires_task_and_records_atomic_effect(self):
        key = "cp75-write-" + uuid.uuid4().hex[:12]
        task_id = None
        self.addCleanup(self._cleanup_memory_write, key, lambda: task_id)
        body = {"key": key, "value": {"format": "brief"}}
        self.assertEqual(call("POST", "/v1/memory", AMBER, body)[0], 400)
        self.assertEqual(call("GET", f"/v1/memory/{key}", AMBER)[0], 404)

        status, task = call("POST", "/v1/tasks", AMBER, {"goal": "Write a requested synthetic preference"})
        self.assertEqual(status, 201)
        task_id = task["task_id"]
        mutation = {**body, "task_id": task_id}
        status, result = call("POST", "/v1/memory", AMBER, mutation)
        self.assertEqual(status, 200, result)
        self.assertEqual((result["state"], result["revision"]), ("CONFIRMED", 1))
        effect_id = result["effect_id"]
        status, replay = call("POST", "/v1/memory", AMBER, mutation)
        self.assertEqual((status, replay["effect_id"], replay["already_recorded"]),
                         (200, effect_id, True))
        self.assertEqual(call("POST", "/v1/memory", AMBER,
                              {**mutation, "value": {"format": "changed"}})[0], 409)
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM effects WHERE task_id=%s AND effect_id=%s AND state='CONFIRMED'",
                        (task_id, effect_id))
            self.assertEqual(cur.fetchone()[0], 1)

    def _cleanup_memory_write(self, key, task_id_getter):
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            task_id = task_id_getter()
            if task_id:
                cur.execute("DELETE FROM effects WHERE task_id=%s", (task_id,))
                cur.execute("DELETE FROM tasks WHERE task_id=%s", (task_id,))
            cur.execute("DELETE FROM scoped_memory WHERE user_id='user-amber' AND memory_key=%s", (key,))

    def test_keyed_memory_correction_is_atomic_idempotent_scoped_and_recoverable(self):
        key = "cp75-memory-" + uuid.uuid4().hex[:12]
        task_ids = []
        original = {"format": "weekly summary in paragraphs"}
        corrected = {"format": "short weekly summary bullets"}
        other_value = {"format": "cobalt private preference"}

        def cleanup():
            with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
                for task_id in task_ids:
                    cur.execute("DELETE FROM effects WHERE task_id=%s", (task_id,))
                    cur.execute("DELETE FROM tasks WHERE task_id=%s", (task_id,))
                cur.execute("DELETE FROM scoped_memory WHERE memory_key=%s", (key,))

        self.addCleanup(cleanup)
        self.assertEqual(seed_memory_fixture(AMBER, key, original), 1)
        self.assertEqual(seed_memory_fixture(COBALT, key, other_value), 1)

        status, task = call("POST", "/v1/tasks", AMBER, {"goal": "Correct and verify the weekly summary preference"})
        self.assertEqual(status, 201, task)
        task_id = task["task_id"]
        task_ids.append(task_id)
        status, search = call("GET", "/v1/memory/search?q=weekly+summary", AMBER)
        self.assertEqual(status, 200, search)
        match = next(row for row in search["memories"] if row["memory_key"] == key)
        self.assertEqual((match["value"], match["revision"]), (original, 1))
        mutation = {"task_id": task_id, "memory_key": match["memory_key"],
                    "expected_revision": match["revision"], "value": corrected}

        # A missing task cannot create an untracked canonical mutation.
        no_task = {k: v for k, v in mutation.items() if k != "task_id"}
        self.assertEqual(call("POST", "/v1/memory/correct-by-key", AMBER, no_task)[0], 400)

        status, changed = call("POST", "/v1/memory/correct-by-key", AMBER, mutation)
        self.assertEqual(status, 200, changed)
        self.assertEqual(changed["state"], "CONFIRMED")
        self.assertEqual((changed["memory_key"], changed["revision"], changed["task_id"]),
                         (key, 2, task_id))
        effect_id = changed["effect_id"]

        # Canonical row and effect are independently read from PostgreSQL.
        with psycopg.connect(os.environ["DATABASE_URL"], row_factory=psycopg.rows.dict_row) as conn, conn.cursor() as cur:
            cur.execute("SELECT user_id,domain_id,value,revision FROM scoped_memory WHERE memory_key=%s AND user_id='user-amber'", (key,))
            canonical = cur.fetchone()
            cur.execute("SELECT task_id,user_id,domain_id,effect_kind,resource_key,state,request,result FROM effects WHERE effect_id=%s", (effect_id,))
            effect = cur.fetchone()
        self.assertEqual((canonical["value"], canonical["revision"]), (corrected, 2))
        self.assertEqual((effect["task_id"], effect["user_id"], effect["domain_id"]),
                         (uuid.UUID(task_id), "user-amber", "domain-home-amber"))
        self.assertEqual((effect["effect_kind"], effect["resource_key"], effect["state"]),
                         ("MEMORY_MUTATION", f"memory:{key}", "CONFIRMED"))
        self.assertEqual(effect["request"], {"operation": "memory_correct", "memory_key": key,
                                              "expected_revision": 1, "value": corrected})
        self.assertEqual(effect["result"]["revision"], canonical["revision"])

        # Exact retries return the original durable effect; changed retries conflict.
        status, repeated = call("POST", "/v1/memory/correct-by-key", AMBER, mutation)
        self.assertEqual(status, 200, repeated)
        self.assertEqual(repeated["effect_id"], effect_id)
        self.assertTrue(repeated["already_recorded"])
        self.assertEqual(call("POST", "/v1/memory/correct-by-key", AMBER,
                              {**mutation, "value": {"format": "changed retry"}})[0], 409)

        # A stale revision on another task cannot mutate or create an effect.
        status, stale_task = call("POST", "/v1/tasks", AMBER, {"goal": "Retry a stale memory correction"})
        self.assertEqual(status, 201)
        task_ids.append(stale_task["task_id"])
        stale = {**mutation, "task_id": stale_task["task_id"]}
        self.assertEqual(call("POST", "/v1/memory/correct-by-key", AMBER, stale)[0], 409)
        status, stale_row = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual((status, stale_row["value"], stale_row["revision"]), (200, corrected, 2))
        status, stale_task_row = call("GET", f"/v1/tasks/{stale_task['task_id']}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(stale_task_row["effects"], [])

        # A different authenticated user cannot use the amber task or its record.
        self.assertEqual(call("POST", "/v1/memory/correct-by-key", COBALT,
                              {**mutation, "value": {"format": "cross-user attack"}})[0], 404)
        status, cobalt_row = call("GET", f"/v1/memory/{key}", COBALT)
        self.assertEqual((status, cobalt_row["value"], cobalt_row["revision"]), (200, other_value, 1))

        # A task row for the same user but another domain is not valid
        # authorization for a correction through the amber domain token.
        status, foreign_domain_task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Reject a memory correction bound to another domain",
        })
        self.assertEqual(status, 201, foreign_domain_task)
        foreign_domain_task_id = foreign_domain_task["task_id"]
        task_ids.append(foreign_domain_task_id)
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET domain_id='domain-home-cobalt' WHERE task_id=%s AND user_id='user-amber'",
                (foreign_domain_task_id,),
            )
            self.assertEqual(cur.rowcount, 1)
        foreign_domain = {
            **mutation,
            "task_id": foreign_domain_task_id,
            "expected_revision": 2,
            "value": {"format": "cross-domain attack"},
        }
        self.assertEqual(call("POST", "/v1/memory/correct-by-key", AMBER, foreign_domain)[0], 404)
        status, after_domain_rejection = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual((status, after_domain_rejection["value"], after_domain_rejection["revision"]),
                         (200, corrected, 2))
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM effects WHERE task_id=%s", (foreign_domain_task_id,))
            self.assertEqual(cur.fetchone()[0], 0)

        proof = {"task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
                 "tool_evidence": [{"tool": "memory_correct", "status": "ok", "state": "CONFIRMED",
                                    "effect_id": effect_id, "memory_key": key, "memory_revision": 2}]}
        status, complete = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {"summary": "Preference corrected and verified",
                "completed": ["preference corrected"], "pending": []},
            "_orchestrator_finalization": proof,
        }, orchestrator=True)
        self.assertEqual(status, 200, complete)
        self.assertEqual(complete["state"], "COMPLETED")

        # A new task represents a fresh model context after candidate/gateway restart.
        status, fresh_task = call("POST", "/v1/tasks", AMBER, {"goal": "Recall the corrected preference in a fresh context"})
        self.assertEqual(status, 201)
        task_ids.append(fresh_task["task_id"])
        status, recalled = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual((status, recalled["value"], recalled["revision"]), (200, corrected, 2))

    def test_memory_effect_and_value_rollback_together_on_confirmation_failure(self):
        key = "cp75-atomic-" + uuid.uuid4().hex[:12]
        task_id = None
        constraint = "cp75_reject_confirm_" + uuid.uuid4().hex[:10]
        self.addCleanup(self._cleanup_memory_atomic, key, constraint, lambda: task_id)
        self.assertEqual(seed_memory_fixture(AMBER, key, "before"), 1)
        status, task = call("POST", "/v1/tasks", AMBER, {"goal": "Atomic correction fault injection"})
        self.assertEqual(status, 201)
        task_id = task["task_id"]
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(f"ALTER TABLE effects ADD CONSTRAINT {constraint} CHECK (NOT (effect_kind='MEMORY_MUTATION' AND resource_key='memory:{key}' AND state='CONFIRMED'))")
        status, _ = call("POST", "/v1/memory/correct-by-key", AMBER,
                         {"task_id": task_id, "memory_key": key, "expected_revision": 1, "value": "after"})
        self.assertEqual(status, 502)
        status, canonical = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual((status, canonical["value"], canonical["revision"]), (200, "before", 1))
        status, task_row = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(task_row["effects"], [])

    def test_orchestrator_scoped_memory_contract_requires_real_exact_cas_before_completion(self):
        key = "cp81-cas-" + uuid.uuid4().hex[:12]
        task_ids = []
        before, after = {"format": "long paragraphs"}, {"format": "three bullets"}

        def cleanup():
            with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
                for task_id in task_ids:
                    cur.execute("DELETE FROM effects WHERE task_id=%s", (task_id,))
                    cur.execute("DELETE FROM tasks WHERE task_id=%s", (task_id,))
                cur.execute("DELETE FROM scoped_memory WHERE user_id='user-amber' AND memory_key=%s", (key,))

        self.addCleanup(cleanup)
        self.assertEqual(seed_memory_fixture(AMBER, key, before), 1)
        contract = {"version": 1, "kind": "memory_correction", "required": [{
            "effect_kind": "MEMORY_MUTATION", "memory_key": key,
            "expected_revision": 1, "value": after,
        }]}
        status, task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Set the synthetic preference to three bullets", "completion_contract": contract,
        }, orchestrator=True)
        self.assertEqual(status, 201, task)
        task_id = task["task_id"]
        task_ids.append(task_id)
        self.assertEqual(task["checkpoint"]["trusted_completion_contract"]["kind"], "memory_correction")

        checkpoint = {"summary": "The requested memory correction is complete",
                      "completed": ["preference correction"], "pending": []}
        false_claim = {"response": "I updated the preference to three bullets.",
                       "response_nonempty": True, "tool_evidence": [], "reason": "claimed"}
        status, _ = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": checkpoint,
            "_orchestrator_finalization": false_claim,
        }, orchestrator=True)
        self.assertEqual(status, 409, "claim without a mutation must not complete")

        status, changed = call("POST", "/v1/memory/correct-by-key", AMBER, {
            "task_id": task_id, "memory_key": key, "expected_revision": 1,
            "value": after,
        })
        self.assertEqual(status, 200, changed)
        effect_id = changed["effect_id"]
        status, retry = call("POST", "/v1/memory/correct-by-key", AMBER, {
            "task_id": task_id, "memory_key": key, "expected_revision": 1,
            "value": after,
        })
        self.assertEqual((status, retry["effect_id"], retry["already_recorded"]),
                         (200, effect_id, True))
        self.assertEqual(call("POST", "/v1/memory/correct-by-key", AMBER, {
            "task_id": task_id, "memory_key": key, "expected_revision": 1,
            "value": {"format": "changed retry"},
        })[0], 409)
        proof = {**false_claim, "reason": "trusted_success_criteria_satisfied"}
        status, complete = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": checkpoint,
            "_orchestrator_finalization": proof,
        }, orchestrator=True)
        self.assertEqual(status, 200, complete)
        self.assertEqual(complete["state"], "COMPLETED")
        self.assertEqual(complete["checkpoint"]["response_delivery"], "PERSISTED_PENDING_DELIVERY")
        self.assertEqual(complete["checkpoint"]["final_response"], proof["response"])
        status, completed_task = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(status, 200, completed_task)
        self.assertEqual(len(completed_task["effects"]), 1)
        self.assertEqual(completed_task["effects"][0]["effect_id"], effect_id)
        status, canonical = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual((status, canonical["value"], canonical["revision"]), (200, after, 2))

    def _cleanup_memory_atomic(self, key, constraint, task_id_getter):
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(f"ALTER TABLE effects DROP CONSTRAINT IF EXISTS {constraint}")
            task_id = task_id_getter()
            if task_id:
                cur.execute("DELETE FROM effects WHERE task_id=%s", (task_id,))
                cur.execute("DELETE FROM tasks WHERE task_id=%s", (task_id,))
            cur.execute("DELETE FROM scoped_memory WHERE user_id='user-amber' AND memory_key=%s", (key,))

    def test_scoped_reads_memory_tasks_and_verified_compound_edit(self):
        status, _ = call("GET", "/health")
        self.assertEqual(status, 200)
        status, _ = call("GET", "/v1/inventory")
        self.assertEqual(status, 401)

        status, contract = call("GET", "/tools.json")
        self.assertEqual(status, 200)
        self.assertEqual(contract["version"], 1)
        self.assertIn("inventory_read", {tool["name"] for tool in contract["tools"]})

        seed_memory_fixture(AMBER, "fixture-read-only-probe", {"sentinel": "unchanged"})

        status, amber_inventory = call("GET", "/v1/inventory", AMBER)
        self.assertEqual(status, 200)
        amber_stock = {item["name"]: item["amount"] for item in amber_inventory["items"]}
        self.assertEqual(amber_stock["Rice"], 2)
        self.assertEqual(amber_stock["Milk"], 1)

        status, cobalt_inventory = call("GET", "/v1/inventory", COBALT)
        self.assertEqual(status, 200)
        cobalt_stock = {item["name"]: item["amount"] for item in cobalt_inventory["items"]}
        self.assertEqual(set(cobalt_stock.values()), {0})

        status, amber_list = call("GET", "/v1/shopping-list", AMBER)
        self.assertEqual(status, 200)
        if {item["name"] for item in amber_list["items"]} != {"Milk", "Oats"}:
            status, reset = call("POST", "/v1/shopping-list/changes", AMBER, {
                "remove": [item["name"] for item in amber_list["items"]],
                "add": [{"name": "Milk", "amount": 1}, {"name": "Oats", "amount": 1}],
            })
            self.assertEqual(status, 200, reset)
            status, amber_list = call("GET", "/v1/shopping-list", AMBER)
            self.assertEqual(status, 200)
        self.assertEqual({item["name"] for item in amber_list["items"]}, {"Milk", "Oats"})
        status, cobalt_list = call("GET", "/v1/shopping-list", COBALT)
        self.assertEqual(status, 200)
        self.assertEqual(cobalt_list["items"], [])

        status, infrastructure = call("GET", "/v1/infrastructure", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(
            {item["observation_state"] for item in infrastructure["observations"]},
            {"FRESH", "STALE", "UNKNOWN"},
        )

        status, probe = call("GET", "/v1/memory/fixture-read-only-probe", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(probe["value"], {"sentinel": "unchanged"})
        status, matches = call("GET", "/v1/memory/search?q=sentinel+read+only+preference", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual([row["memory_key"] for row in matches["memories"]], ["fixture-read-only-probe"])
        status, matches = call("GET", "/v1/memory/search?q=sentinel+read+only+preference", COBALT)
        self.assertEqual(status, 200)
        self.assertEqual(matches["memories"], [])
        status, _ = call("GET", "/v1/memory/fixture-read-only-probe", COBALT)
        self.assertEqual(status, 404)

        status, correction_task = call("POST", "/v1/tasks", AMBER, {
            "goal": "correct the disposable read-only probe"
        })
        self.assertEqual(status, 201)
        correction_task_id = correction_task["task_id"]
        try:
            status, legacy = call("POST", "/v1/memory/correct", AMBER, {
                "query": "fixture read only probe",
                "expected_value": {"sentinel": "unchanged"},
                "value": {"sentinel": "legacy route must not mutate"},
            })
            self.assertEqual(status, 410)

            status, fresh = call("GET", "/v1/memory/fixture-read-only-probe", AMBER)
            self.assertEqual(status, 200)
            status, corrected = call("POST", "/v1/memory/correct-by-key", AMBER, {
                "task_id": correction_task_id,
                "memory_key": fresh["memory_key"],
                "expected_revision": fresh["revision"],
                "value": {"sentinel": "corrected"},
            })
            self.assertEqual(status, 200, corrected)
            self.assertEqual(corrected["memory_key"], "fixture-read-only-probe")
            self.assertEqual(corrected["value"], {"sentinel": "corrected"})

            status, selected = call("GET", "/v1/memory/fixture-read-only-probe", AMBER)
            status2, other = call("GET", "/v1/memory/answer_style", AMBER)
            self.assertEqual(status, 200)
            self.assertEqual(status2, 200)
            self.assertEqual(selected["value"], {"sentinel": "corrected"})
            self.assertEqual(other["value"], {"scope": "synthetic lab status updates", "style": "brief prose"})

            status, cross_user = call("POST", "/v1/memory/correct-by-key", COBALT, {
                "task_id": correction_task_id,
                "memory_key": "fixture-read-only-probe",
                "expected_revision": selected["revision"],
                "value": {"sentinel": "cross user"},
            })
            self.assertEqual(status, 404)
        finally:
            with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM effects WHERE task_id=%s", (correction_task_id,))
                cur.execute("DELETE FROM tasks WHERE task_id=%s", (correction_task_id,))
            seed_memory_fixture(AMBER, "fixture-read-only-probe", {"sentinel": "unchanged"})
            status, restored = call("GET", "/v1/memory/fixture-read-only-probe", AMBER)
            self.assertEqual(status, 200)
            self.assertEqual(restored["value"], {"sentinel": "unchanged"})

        status, task = call("POST", "/v1/tasks", AMBER, {"goal": "fixture restart task"})
        self.assertEqual(status, 201)
        task_id = task["task_id"]
        status, read_task = call("POST", "/v1/tasks", AMBER, {"goal": "report current infrastructure observations"})
        self.assertEqual(status, 201)
        status, infra = call("GET", "/v1/infrastructure", AMBER)
        self.assertEqual(status, 200)
        status, rejected = call("POST", f"/v1/tasks/{read_task['task_id']}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {
                "summary": "Read complete", "completed": ["read infrastructure"], "pending": []
            }
        })
        self.assertEqual(status, 403)
        proof = {
            "task_type": "READ_ONLY", "response_nonempty": True, "completion_claim": False,
            "tool_evidence": [{"tool": "infrastructure_read", "status": "ok"}],
        }
        status, forged_read = call("POST", f"/v1/tasks/{read_task['task_id']}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {
                "summary": "Read and report completed", "completed": ["read infrastructure"], "pending": []
            }, "_orchestrator_finalization": proof,
        })
        self.assertEqual(status, 403)
        status, completed_read = call("POST", f"/v1/tasks/{read_task['task_id']}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {
                "summary": "Read and report completed", "completed": ["read infrastructure"], "pending": []
            },
            "_orchestrator_finalization": proof,
        }, orchestrator=True)
        self.assertEqual(status, 200, completed_read)
        self.assertEqual(completed_read["state"], "COMPLETED")
        status, empty_proof_task = call("POST", "/v1/tasks", AMBER, {"goal": "reject unsupported completion evidence"})
        self.assertEqual(status, 201)
        status, rejected_empty_proof = call("POST", f"/v1/tasks/{empty_proof_task['task_id']}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {"summary": "Unsupported", "completed": ["answer"], "pending": []},
            "_orchestrator_finalization": {"task_type": "EFFECTFUL", "response_nonempty": True,
                                           "completion_claim": True, "tool_evidence": []},
        }, orchestrator=True)
        self.assertEqual(status, 409)
        self.assertIn("verified read or write evidence", rejected_empty_proof["error"])
        status, rejected = call("POST", f"/v1/tasks/{read_task['task_id']}/checkpoint", AMBER, {
            "state": "FAILED", "checkpoint": {
                "summary": "Should not overwrite terminal", "completed": [], "pending": []
            }
        })
        self.assertEqual(status, 409)
        status, rejected = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "WAITING", "checkpoint": {}
        })
        self.assertEqual(status, 400)
        self.assertIn("completed/pending", rejected["error"])
        status, saved = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "WAITING", "checkpoint": {
                "summary": "Inventory read completed",
                "completed": ["inventory_read"],
                "pending": ["continue task"],
                "step": "after-source-read",
            },
            "_orchestrator_finalization": {"response_nonempty": True, "tool_evidence": []},
        }, orchestrator=True)
        self.assertEqual(status, 200)
        self.assertEqual(saved["revision"], 1)
        status, resumed = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(resumed["checkpoint"]["step"], "after-source-read")
        self.assertEqual(resumed["checkpoint"]["completed"], ["inventory_read"])
        status, still_waiting = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(still_waiting["state"], "WAITING")
        status, denied_resume = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "RUNNING", "checkpoint": {"summary": "Candidate cannot resume", "completed": ["inventory_read"], "pending": ["continue task"]}
        })
        self.assertEqual(status, 409)
        status, resumed = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "RUNNING", "checkpoint": {"summary": "Explicit resume", "completed": ["inventory_read"], "pending": ["continue task"]},
            "_orchestrator_resume": True,
        }, orchestrator=True)
        self.assertEqual(status, 200)
        self.assertEqual(resumed["state"], "RUNNING")
        status, _ = call("GET", f"/v1/tasks/{task_id}", COBALT)
        self.assertEqual(status, 404)

        status, rejected = call("POST", "/v1/shopping-list/changes", AMBER, {
            "task_id": task_id,
            "remove": ["Oats"],
            "add": [{"name": "Egg", "amount": 3}, {"name": "Pasta", "amount": 1}],
        })
        self.assertEqual(status, 404)
        self.assertIn("inventory_read", rejected["error"])
        self.assertIn("No changes applied", rejected["error"])
        self.assertIn("Eggs", rejected["error"])
        self.assertIn("Pasta", rejected["error"])
        status, unchanged = call("GET", "/v1/shopping-list", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual({item["name"] for item in unchanged["items"]}, {"Milk", "Oats"})

        status, _ = call("POST", "/v1/shopping-list/changes", COBALT, {
            "task_id": task_id,
            "remove": ["Milk"],
            "add": [{"name": "Rice", "amount": 1}],
        })
        self.assertEqual(status, 404)
        status, unchanged = call("GET", "/v1/shopping-list", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual({item["name"] for item in unchanged["items"]}, {"Milk", "Oats"})

        status, changed = call("POST", "/v1/shopping-list/changes", AMBER, {
            "task_id": task_id,
            "remove": ["Milk"],
            "add": [{"name": "Rice", "amount": 1}, {"name": "Eggs", "amount": 2}],
        })
        self.assertEqual(status, 200, changed)
        self.assertEqual(changed["state"], "CONFIRMED")
        self.assertEqual(changed["task_id"], task_id)
        expected = {"Oats": 1, "Rice": 1, "Eggs": 2}
        actual = {item["name"]: item["amount"] for item in changed["verified_after"]}
        self.assertEqual(actual, expected)
        status, wrong_effect_proof = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {
                "summary": "Wrong effect proof", "completed": ["list read-back matched"], "pending": []
            },
            "_orchestrator_finalization": {
                "task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
                "tool_evidence": [{
                    "tool": "shopping_list_change", "status": "ok", "state": "CONFIRMED",
                    "effect_id": "00000000-0000-0000-0000-000000000000", "verified_after": changed["verified_after"],
                }],
            },
        }, orchestrator=True)
        self.assertEqual(status, 409)
        self.assertIn("effect ID exactly", wrong_effect_proof["error"])
        status, still_running = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(still_running["state"], "RUNNING")
        status, no_http_shortcut = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {"summary": "Done", "completed": ["change"], "pending": []}
        })
        self.assertEqual(status, 403)
        status, completed_write = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {
                "summary": "Compound list change verified", "completed": ["list read-back matched"], "pending": []
            },
            "_orchestrator_finalization": {
                "task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
                "tool_evidence": [{
                    "tool": "shopping_list_change", "status": "ok", "state": "CONFIRMED",
                    "effect_id": changed["effect_id"], "verified_after": changed["verified_after"],
                }],
            },
        }, orchestrator=True)
        self.assertEqual(status, 200, completed_write)
        self.assertEqual(completed_write["state"], "COMPLETED")

        status, cobalt_after = call("GET", "/v1/shopping-list", COBALT)
        self.assertEqual(status, 200)
        self.assertEqual(cobalt_after["items"], [])


if __name__ == "__main__":
    unittest.main()
