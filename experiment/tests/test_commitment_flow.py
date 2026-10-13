import json
import os
import unittest
import urllib.error
import urllib.request


BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
AMBER = "fixture-token-amber"
COBALT = "fixture-token-cobalt"
TASK_ID = os.environ.get("COMMITMENT_TASK_ID")
APPROVAL_ID = os.environ.get("COMMITMENT_APPROVAL_ID")
TARGET = os.environ.get("COMMITMENT_TARGET", "target-ack-loss")
DETAILS = "Reserve the synthetic appointment slot for Amber at 16:00"


def call(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@unittest.skipUnless(TASK_ID and APPROVAL_ID, "requires an operator-issued test grant")
class ProtectedCommitmentFlow(unittest.TestCase):
    def test_ack_loss_is_quarantined_and_reconciled_without_replay(self):
        request = {
            "task_id": TASK_ID,
            "target_id": TARGET,
            "details": DETAILS,
            "approval_id": "00000000-0000-0000-0000-000000000001",
        }
        status, denied = call("POST", "/v1/commitments", AMBER, request)
        self.assertEqual(status, 403, denied)
        status, harmless = call("GET", "/v1/inventory", AMBER)
        self.assertEqual(status, 200, harmless)

        request["approval_id"] = APPROVAL_ID
        request["details"] = "Reserve a different synthetic appointment slot"
        status, mismatched = call("POST", "/v1/commitments", AMBER, request)
        self.assertEqual(status, 403, mismatched)

        request["details"] = DETAILS
        status, pending = call("POST", "/v1/commitments", AMBER, request)
        self.assertEqual(status, 202, pending)
        self.assertEqual(pending["state"], "QUARANTINED")
        effect_id = pending["effect_id"]

        status, hidden = call(
            "POST", f"/v1/commitments/{effect_id}/reconcile", COBALT, {}
        )
        self.assertEqual(status, 404, hidden)

        status, reconciled = call(
            "POST", f"/v1/commitments/{effect_id}/reconcile", AMBER, {}
        )
        self.assertEqual(status, 200, reconciled)
        self.assertEqual(reconciled["state"], "CONFIRMED")
        self.assertEqual(reconciled["reconciled_target_state"]["state"], "ACCEPTED")
        self.assertEqual(reconciled["reconciled_target_state"]["receive_count"], 1)

        status, repeated = call("POST", "/v1/commitments", AMBER, request)
        self.assertEqual(status, 200, repeated)
        self.assertEqual(repeated["state"], "CONFIRMED")
        self.assertEqual(repeated["effect_id"], effect_id)
        self.assertTrue(repeated["already_recorded"])
        self.assertEqual(repeated["target_result"]["reconciled_target_state"]["receive_count"], 1)


if __name__ == "__main__":
    unittest.main()
