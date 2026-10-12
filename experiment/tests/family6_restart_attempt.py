"""Drive one family 6 phase against the disposable candidate API."""

import argparse
import json
import urllib.error
import urllib.request

TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"


def get_task(task_id):
    request = urllib.request.Request(
        f"{GATEWAY}/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("lean", "pydantic"), required=True)
    parser.add_argument("--trial", required=True)
    parser.add_argument("--phase", choices=("prepare", "resume"), required=True)
    parser.add_argument("--task-id")
    args = parser.parse_args()

    goal = (
        f"[FAMILY6 {args.trial}] In the synthetic repository, repair the discount calculation "
        "so it reduces the price by the given percent. Run all tests, review the diff, and "
        "commit the verified fix as `Recover discount calculation`."
    )
    if args.phase == "prepare":
        checkpoint = json.dumps({"summary": "Inspected the source and tests; no files changed.",
                                 "completed": ["read discount.py", "read test_discount.py"],
                                 "pending": ["repair formula", "run tests", "review diff", "commit"],
                                 "family": "family6", "trial": args.trial,
                                 "phase": "source_inspected", "repair_pending": True})
        messages = [{"role": "user", "content":
            f"{goal} For this turn, do only two things: (1) use workspace_exec once to run "
            "`cat discount.py && cat test_discount.py`; (2) call task_checkpoint with state "
            f"RUNNING and checkpoint exactly {checkpoint}. Do not edit files or call any other "
            "tool. Stop after the checkpoint call."}]
        task_id = None
    else:
        if not args.task_id:
            raise SystemExit("--task-id is required for resume")
        task_id = args.task_id
        messages = [
            {"role": "user", "content": goal},
            {"role": "assistant", "content": "I inspected the source and tests before the runtime was interrupted. The durable task checkpoint says the repair is pending."},
            {"role": "user", "content": "The authorized synthetic coding task is active, and no additional approval is needed. Resume this same durable task. First read its checkpoint and inspect the workspace state. Complete the pending repair now, run tests, review the diff, and commit the verified fix if tests pass. Do not pause or ask whether to continue unless a real prerequisite is missing."},
        ]

    body = {"candidate": args.candidate, "user_token": TOKEN, "messages": messages}
    if task_id:
        body["task_id"] = task_id
    request = urllib.request.Request(
        CANDIDATE_API + "/api/turn", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read())
        task_id = result.get("task_id") or task_id
        task = get_task(task_id) if task_id else {}
        record = {"phase": args.phase, "candidate": args.candidate, "trial": args.trial,
                  "task_id": task_id, "http_status": 200, "task_state": task.get("state"),
                  "checkpoint": task.get("checkpoint", {}),
                  "tool_calls": result.get("tool_calls", []),
                  "usage": result.get("usage", {}), "duration_ms": result.get("duration_ms"),
                  "text": result.get("text", "")}
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        if isinstance(error, urllib.error.HTTPError):
            try:
                failure = json.loads(error.read().decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                failure = {"error": "non-json HTTP failure"}
            status = error.code
        else:
            failure = {"error": type(error).__name__}
            status = None
        task_id = failure.get("task_id") or task_id
        try:
            task = get_task(task_id) if task_id else {}
        except Exception as read_error:
            task = {"read_error": type(read_error).__name__}
        record = {"phase": args.phase, "candidate": args.candidate, "trial": args.trial,
                  "task_id": task_id, "http_status": status, "failure": failure,
                  "task_state": task.get("state"), "checkpoint": task.get("checkpoint", {})}
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
