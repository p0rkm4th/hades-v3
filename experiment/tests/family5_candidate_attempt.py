"""Execute one model-driven coding attempt against the shared disposable fixture."""

import argparse
import json
import urllib.error
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
PROMPT = (
    "Please fix the discount calculation in the synthetic repository. It currently adds the "
    "percent; a discount should reduce the price. Inspect the repository and its tests, make "
    "the smallest correct change, run all tests, inspect your final diff, and commit the fix "
    "as `Fix discount calculation` if the tests pass. Then report the test result and commit."
)


def get_json(path):
    request = urllib.request.Request(
        GATEWAY + path,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("lean", "pydantic"), required=True)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    request = urllib.request.Request(
        CANDIDATE_API + "/api/turn",
        data=json.dumps({
            "candidate": args.candidate,
            "user_token": TOKEN,
            "messages": [{"role": "user", "content": PROMPT}],
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read())
        task_id = result.get("task_id")
        task = get_json(f"/v1/tasks/{task_id}") if task_id else {}
        record = {
            "candidate": args.candidate,
            "attempt": args.attempt,
            "prompt": PROMPT,
            "task_id": task_id,
            "task_state": task.get("state"),
            "checkpoint": task.get("checkpoint", {}),
            "tool_calls": result.get("tool_calls", []),
            "tool_evidence": result.get("tool_evidence", []),
            "usage": result.get("usage", {}),
            "duration_ms": result.get("duration_ms"),
            "text": result.get("text", ""),
        }
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        try:
            failure = json.loads(body)
        except json.JSONDecodeError:
            failure = {"response": body}
        task_id = failure.get("task_id")
        task = get_json(f"/v1/tasks/{task_id}") if task_id else {}
        record = {
            "candidate": args.candidate,
            "attempt": args.attempt,
            "prompt": PROMPT,
            "http_status": error.code,
            "error": failure,
            "task_id": task_id,
            "task_state": task.get("state"),
            "checkpoint": task.get("checkpoint", {}),
            "tool_calls": task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", []),
        }
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
