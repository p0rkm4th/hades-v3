"""Run a matched read-only family 3 screen with an injected ERROR fixture row."""

import json
import sys
from urllib.error import HTTPError
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
PROMPT = sys.argv[1] if len(sys.argv) > 1 else (
    "Can you report whether synthetic-monitor is healthy right now? "
    "If its source is unavailable, say so without inferring a health value."
)
ORDER = ("lean", "pydantic", "lean", "pydantic", "lean", "pydantic")


def get_json(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.loads(response.read())


def observations():
    result = get_json(
        GATEWAY + "/v1/infrastructure",
        {"Authorization": f"Bearer {TOKEN}"},
    )
    return result["observations"]


before = observations()
monitor = next((row for row in before if row["subject"] == "synthetic-monitor"), None)
assert monitor is not None and monitor["observation_state"] == "ERROR", monitor
assert monitor["value"] is None and monitor["observed_at"] is None, monitor

results = []
for candidate in ORDER:
    payload = {
        "candidate": candidate,
        "user_token": TOKEN,
        "messages": [{"role": "user", "content": PROMPT}],
    }
    request = urllib.request.Request(
        CANDIDATE_API + "/api/turn",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            failure = json.loads(body)
        except json.JSONDecodeError:
            failure = {"body": body}
        task = None
        if failure.get("task_id"):
            try:
                task = get_json(
                    GATEWAY + f"/v1/tasks/{failure['task_id']}",
                    {"Authorization": f"Bearer {TOKEN}"},
                )
            except Exception as task_error:  # Preserve the original API failure.
                task = {"readback_error": type(task_error).__name__}
        print(json.dumps({
            "candidate": candidate,
            "http_status": error.code,
            "failure": failure,
            "task_readback": task,
        }), flush=True)
        raise
    task = get_json(
        GATEWAY + f"/v1/tasks/{result['task_id']}",
        {"Authorization": f"Bearer {TOKEN}"},
    )
    candidate_turn = task.get("checkpoint", {}).get("candidate_turn", {})
    if task["state"] != "COMPLETED":
        print(json.dumps({
            "candidate": candidate,
            "task_id": result["task_id"],
            "task": task,
        }), flush=True)
        raise RuntimeError(f"candidate task did not complete: {task['state']}")
    results.append({
        "candidate": candidate,
        "task_id": result["task_id"],
        "task_state": task["state"],
        "task_tools": candidate_turn.get("tools", []),
        "expected_read_used": candidate_turn.get("tools") == ["infrastructure_read"],
        "tool_calls": result.get("tool_calls", []),
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms"),
        "text": result.get("text", ""),
    })
    print(json.dumps(results[-1]), flush=True)

after = observations()
assert before == after, {"before": before, "after": after}
print(json.dumps({"before": before, "results": results, "after": after}, indent=2))
