"""Run a matched read-only family 3 screen with an injected ERROR fixture row."""

import json
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
PROMPT = (
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
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read())
    task = get_json(
        GATEWAY + f"/v1/tasks/{result['task_id']}",
        {"Authorization": f"Bearer {TOKEN}"},
    )
    candidate_turn = task.get("checkpoint", {}).get("candidate_turn", {})
    assert task["state"] == "COMPLETED", task
    assert candidate_turn.get("tools") == ["infrastructure_read"], task
    results.append({
        "candidate": candidate,
        "task_id": result["task_id"],
        "task_state": task["state"],
        "tool_calls": result.get("tool_calls", []),
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms"),
        "text": result.get("text", ""),
    })

after = observations()
assert before == after, {"before": before, "after": after}
print(json.dumps({"before": before, "results": results, "after": after}, indent=2))
