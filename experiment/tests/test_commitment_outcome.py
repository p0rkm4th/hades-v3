import json
import os
import unittest
import urllib.error
import urllib.request


BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
AMBER = "fixture-token-amber"
TASK_ID = os.environ.get("COMMITMENT_TASK_ID")
APPROVAL_ID = os.environ.get("COMMITMENT_APPROVAL_ID")
TARGET = os.environ.get("COMMITMENT_TARGET")
DETAILS = os.environ.get("COMMITMENT_DETAILS")
EXPECTED_STATE = os.environ.get("COMMITMENT_EXPECTED_STATE")


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


@unittest.skipUnless(
    TASK_ID and APPROVAL_ID and TARGET and DETAILS and EXPECTED_STATE,
    "requires an operator-issued test grant and expected fixture outcome",
)
class ApprovedCommitmentOutcome(unittest.TestCase):
    def test_accepted_or_rejected_target_outcome_is_recorded(self):
        status, result = call("POST", "/v1/commitments", AMBER, {
            "task_id": TASK_ID,
            "target_id": TARGET,
            "details": DETAILS,
            "approval_id": APPROVAL_ID,
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["state"], EXPECTED_STATE)
        self.assertEqual(result["task_id"], TASK_ID)
        self.assertTrue(result.get("effect_id"))


if __name__ == "__main__":
    unittest.main()
