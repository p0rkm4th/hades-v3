"""Run one candidate's multi-turn scoped-memory correction and recall attempt."""

import json
import sys
import urllib.error
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
TURNS = (
    "How do I prefer you to format synthetic lab status updates? Please check my saved preference.",
    "Correction: change my saved answer style for synthetic lab status updates to short bullet lists instead of brief prose. Please update what you remember.",
    "Okay, what should the next synthetic lab status update look like?",
)
FRESH_RECALL = "What is currently saved as my answer style for synthetic lab status updates? Please retrieve the stored preference."


def get_json(url):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.loads(response.read())


def post_turn(candidate, messages):
    request = urllib.request.Request(
        CANDIDATE_API + "/api/turn",
        data=json.dumps({
            "candidate": candidate,
            "user_token": TOKEN,
            "messages": messages,
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            failure = json.loads(body)
        except json.JSONDecodeError:
            failure = {"body": body}
        task = None
        if failure.get("task_id"):
            try:
                task = get_json(GATEWAY + f"/v1/tasks/{failure['task_id']}")
            except Exception as task_error:
                task = {"readback_error": type(task_error).__name__}
        print(json.dumps({
            "http_status": error.code,
            "failure": failure,
            "task_readback": task,
        }), flush=True)
        raise

    task = get_json(GATEWAY + f"/v1/tasks/{result['task_id']}")
    trace = task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", [])
    item = {
        "candidate": candidate,
        "task_id": result["task_id"],
        "task_state": task["state"],
        "tools": trace,
        "reported_tools": result.get("tool_calls", []),
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms"),
        "text": result.get("text", ""),
    }
    print(json.dumps(item), flush=True)
    if task["state"] != "COMPLETED":
        raise RuntimeError(f"candidate task failed: {result['task_id']}")
    return result.get("text", "")


candidate = sys.argv[1]
assert candidate in {"lean", "pydantic"}, candidate
seed = get_json(GATEWAY + "/v1/memory/answer_style")
assert seed["value"] == {"style": "brief prose", "scope": "synthetic lab status updates"}, seed

history = []
for prompt in TURNS:
    history.append({"role": "user", "content": prompt})
    answer = post_turn(candidate, history)
    history.append({"role": "assistant", "content": answer})

# Start a fresh conversational context. The saved memory must survive independently.
fresh_answer = post_turn(candidate, [{"role": "user", "content": FRESH_RECALL}])
try:
    stored = get_json(GATEWAY + "/v1/memory/answer_style")
except urllib.error.HTTPError as error:
    stored = {"http_status": error.code}

print(json.dumps({
    "candidate": candidate,
    "fresh_context_recall": fresh_answer,
    "stored_answer_style": stored,
}), flush=True)
