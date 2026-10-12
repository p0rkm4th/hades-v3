"""Operator-run probe for candidate timeout closure; requires a forced short model timeout."""

import argparse
import json
import urllib.error
import urllib.request


parser = argparse.ArgumentParser()
parser.add_argument("--candidate", choices=("lean", "pydantic"), required=True)
args = parser.parse_args()

token = "fixture-token-amber"
base = "http://candidate-api:8080"
gateway = "http://tool-gateway:8080"
prompt = (
    "Check the current synthetic infrastructure observations and distinguish "
    "fresh, stale, and unknown data."
)
payload = {
    "candidate": args.candidate,
    "user_token": token,
    "messages": [{"role": "user", "content": prompt}],
}
request = urllib.request.Request(
    base + "/api/turn",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        raise AssertionError(f"expected bounded model failure, received HTTP {response.status}")
except urllib.error.HTTPError as error:
    if error.code != 502:
        raise AssertionError(f"expected HTTP 502, received HTTP {error.code}") from error
    failure = json.loads(error.read())

task_id = failure.get("task_id")
if not task_id:
    raise AssertionError("failed response omitted the durable task ID")

task_request = urllib.request.Request(
    f"{gateway}/v1/tasks/{task_id}",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(task_request, timeout=10) as response:
    task = json.loads(response.read())

candidate_turn = task.get("checkpoint", {}).get("candidate_turn", {})
assert task.get("state") == "FAILED", task
assert candidate_turn.get("state") == "FAILED", task
assert candidate_turn.get("operator_review_required") is True, task
assert candidate_turn.get("effect_outcome_uncertain") is True, task
assert candidate_turn.get("error_type"), task
assert candidate_turn.get("tools") == [], task
print(json.dumps({
    "candidate": args.candidate,
    "http_status": 502,
    "task_id": task_id,
    "task_state": task["state"],
    "error_type": candidate_turn["error_type"],
    "operator_review_required": candidate_turn["operator_review_required"],
    "effect_outcome_uncertain": candidate_turn["effect_outcome_uncertain"],
    "tools": candidate_turn["tools"],
}, indent=2))
