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
        status, _ = call("GET", "/v1/memory/fixture-read-only-probe", COBALT)
        self.assertEqual(status, 404)

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
