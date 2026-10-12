"""Run one candidate's bounded multi-turn memory correction and recall attempt."""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
MEMORY_KEY = "weekly_report_format"
SEED_VALUE = "brief prose"
TURNS = (
    "What format is saved for my weekly readiness reports?",
    "Correction: change the saved weekly report format from brief prose to numbered bullet points. Update that preference.",
    "For the next weekly readiness report, what format should I use?",
)
FRESH_RECALL = "What format is currently saved for my weekly readiness reports?"


def get_json(path):
    request = urllib.request.Request(
        GATEWAY + path,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
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
                task = get_json(f"/v1/tasks/{failure['task_id']}")
            except Exception as task_error:
                task = {"readback_error": type(task_error).__name__}
        print(json.dumps({
            "http_status": error.code,
            "failure": failure,
            "task_readback": task,
        }), flush=True)
        raise

    task = get_json(f"/v1/tasks/{result['task_id']}")
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
seed = get_json(f"/v1/memory/{urllib.parse.quote(MEMORY_KEY, safe='')}")
assert seed["value"] == SEED_VALUE, seed

history = []
for prompt in TURNS:
    history.append({"role": "user", "content": prompt})
    answer = post_turn(candidate, history)
    history.append({"role": "assistant", "content": answer})

# A fresh conversation verifies that the correction is independently retrievable.
fresh_answer = post_turn(candidate, [{"role": "user", "content": FRESH_RECALL}])
stored = get_json(f"/v1/memory/{urllib.parse.quote(MEMORY_KEY, safe='')}")
related = get_json("/v1/memory/search?q=weekly+report+format")
print(json.dumps({
    "candidate": candidate,
    "fresh_context_recall": fresh_answer,
    "stored_memory": stored,
    "related_memories": related.get("memories", []),
}), flush=True)
