import json
import os
import unittest
import urllib.error
import urllib.request


BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
AMBER = "fixture-token-amber"
COBALT = "fixture-token-cobalt"


def call(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


class GatewayIntegration(unittest.TestCase):
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
        status, saved = call("POST", f"/v1/tasks/{task_id}/checkpoint", AMBER, {
            "state": "WAITING", "checkpoint": {"step": "after-source-read", "done": ["inventory"]}
        })
        self.assertEqual(status, 200)
        self.assertEqual(saved["revision"], 1)
        status, resumed = call("GET", f"/v1/tasks/{task_id}", AMBER)
        self.assertEqual(status, 200)
        self.assertEqual(resumed["checkpoint"]["step"], "after-source-read")
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

        status, cobalt_after = call("GET", "/v1/shopping-list", COBALT)
        self.assertEqual(status, 200)
        self.assertEqual(cobalt_after["items"], [])


if __name__ == "__main__":
    unittest.main()
