import json
import os
import unittest
import urllib.error
import urllib.request
import uuid
import psycopg


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


class GatewayIntegration(unittest.TestCase):
    def test_task_linked_memory_correction_is_atomic_idempotent_and_recoverable(self):
        key = "cp74-memory-" + uuid.uuid4().hex[:12]
        task_ids = []

        def cleanup():
            with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
                for task_id in task_ids:
                    cur.execute("DELETE FROM effects WHERE task_id=%s", (task_id,))
                    cur.execute("DELETE FROM tasks WHERE task_id=%s", (task_id,))
                cur.execute(
                    "DELETE FROM scoped_memory WHERE user_id='user-amber' AND memory_key=%s",
                    (key,),
                )

        self.addCleanup(cleanup)
        original = {"format": "weekly summary in paragraphs"}
        corrected = {"format": "short weekly summary bullets"}
        status, seeded = call("POST", "/v1/memory", AMBER, {"key": key, "value": original})
        self.assertEqual(status, 200, seeded)

        status, task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Correct the stored weekly summary preference and verify it in a fresh context"
        })
        self.assertEqual(status, 201, task)
        task_id = task["task_id"]
        task_ids.append(task_id)
        mutation = {
            "task_id": task_id, "query": key.replace("-", " ") + " weekly summary",
            "expected_value": original, "value": corrected,
        }
        status, changed = call("POST", "/v1/memory/correct", AMBER, mutation)
        self.assertEqual(status, 200, changed)
        self.assertEqual(changed["state"], "CONFIRMED")
        self.assertEqual(changed["task_id"], task_id)
        self.assertTrue(changed.get("effect_id"))

        status, repeated = call("POST", "/v1/memory/correct", AMBER, mutation)
        self.assertEqual(status, 200, repeated)
        self.assertEqual(repeated["effect_id"], changed["effect_id"])
        self.assertTrue(repeated["already_recorded"])
        status, task_row = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(len(task_row["effects"]), 1)

        status, mismatch = call("POST", "/v1/memory/correct", AMBER, {
            **mutation, "value": {"format": "changed retry must not apply"},
        })
        self.assertEqual(status, 409)
        status, saved = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(saved["value"], corrected)

        proof = {
            "task_type": "EFFECTFUL", "response_nonempty": True, "completion_claim": True,
            "tool_evidence": [{
                "tool": "memory_correct", "status": "ok", "state": "CONFIRMED",
                "effect_id": changed["effect_id"], "memory_key": key,
            }],
        }
        status, complete = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "COMPLETED", "checkpoint": {
                "summary": "The memory correction was verified", "completed": ["preference corrected"],
                "pending": [],
            }, "_orchestrator_finalization": proof,
        }, orchestrator=True)
        self.assertEqual(status, 200, complete)
        self.assertEqual(complete["state"], "COMPLETED")

        # A separate task simulates a fresh conversational context after restart.
        status, fresh_task = call("POST", "/v1/tasks", AMBER, {
            "goal": "Recall the corrected weekly summary preference"
        })
        self.assertEqual(status, 201)
        task_ids.append(fresh_task["task_id"])
        status, recalled = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(recalled["value"], corrected)
        status, invalid_owner = call("POST", "/v1/memory", COBALT, {
            "task_id": fresh_task["task_id"], "key": key, "value": {"format": "cross-domain"},
        })
        self.assertEqual(status, 404)
        status, still_correct = call("GET", f"/v1/memory/{key}", AMBER)
        self.assertEqual(still_correct["value"], corrected)

    def test_scoped_reads_memory_tasks_and_verified_compound_edit(self):
        status, _ = call("GET", "/health")
        self.assertEqual(status, 200)
        status, _ = call("GET", "/v1/inventory")
        self.assertEqual(status, 401)

        status, contract = call("GET", "/tools.json")
        self.assertEqual(status, 200)
        self.assertEqual(contract["version"], 1)
        self.assertIn("inventory_read", {tool["name"] for tool in contract["tools"]})

        status, _ = call("POST", "/v1/memory", AMBER, {
            "key": "fixture-read-only-probe", "value": {"sentinel": "unchanged"}
        })
        self.assertEqual(status, 200)

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

        try:
            status, corrected = call("POST", "/v1/memory/correct", AMBER, {
                "query": "fixture read only probe",
                "expected_value": {"sentinel": "unchanged"},
                "value": {"sentinel": "corrected"},
            })
            self.assertEqual(status, 200)
            self.assertEqual(corrected["memory_key"], "fixture-read-only-probe")
            self.assertEqual(corrected["value"], {"sentinel": "corrected"})
            status, saved = call("GET", "/v1/memory/fixture-read-only-probe", AMBER)
            self.assertEqual(status, 200)
            self.assertEqual(saved["value"], {"sentinel": "corrected"})

            status, missing = call("POST", "/v1/memory/correct", AMBER, {
                "query": "missing disposable preference",
                "expected_value": {"format": "brief prose"},
                "value": {"format": "short bullets"},
            })
            self.assertEqual(status, 404)
            self.assertIn("no existing memory", missing["error"])

            status, canonical = call("GET", "/v1/memory/answer_style", AMBER)
            self.assertEqual(status, 200)
            shared_value = canonical["value"]
            status, _ = call("POST", "/v1/memory", AMBER, {
                "key": "fixture-read-only-probe", "value": shared_value
            })
            self.assertEqual(status, 200)
            status, ambiguous = call("POST", "/v1/memory/correct", AMBER, {
                "query": "synthetic lab status updates answer style",
                "expected_value": shared_value,
                "value": {"scope": "synthetic lab status updates", "style": "short bullets"},
            })
            self.assertEqual(status, 409)
            self.assertIn("ambiguous", ambiguous["error"])
            status, unchanged = call("GET", "/v1/memory/answer_style", AMBER)
            self.assertEqual(status, 200)
            self.assertEqual(unchanged["value"], shared_value)

            status, cross_user = call("POST", "/v1/memory/correct", COBALT, {
                "query": "fixture read only probe",
                "expected_value": {"sentinel": "corrected"},
                "value": {"sentinel": "cross user"},
            })
            self.assertEqual(status, 404)
        finally:
            status, restored = call("POST", "/v1/memory", AMBER, {
                "key": "fixture-read-only-probe", "value": {"sentinel": "unchanged"}
            })
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
