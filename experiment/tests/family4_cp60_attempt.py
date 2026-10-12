"""Run one saved deployment-note preference correction and fresh-recall attempt."""

import json
import sys
import urllib.parse
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
MEMORY_KEY = "deployment_note_heading_order"
SEED_VALUE = "service name, change, rollout status"
UPDATED_VALUE = "change, service name, rollout status"
TURNS = (
    "What order did I choose for the headings in a deployment note?",
    "Update my saved heading order for deployment notes from service name, change, rollout status to change, service name, rollout status.",
    "What heading should appear first in the next deployment note?",
)
FRESH_RECALL = "What heading order did I ask for in deployment notes?"


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
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read())
    task = get_json(f"/v1/tasks/{result['task_id']}")
    item = {
        "candidate": candidate,
        "task_id": result["task_id"],
        "task_state": task["state"],
        "tools": task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", []),
        "tool_evidence": result.get("tool_evidence", []),
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms"),
        "text": result.get("text", ""),
    }
    print(json.dumps(item, ensure_ascii=False), flush=True)
    if task["state"] == "FAILED":
        raise RuntimeError(f"candidate task failed: {result['task_id']}")
    return result.get("text", ""), result["task_id"]


candidate = sys.argv[1]
attempt = int(sys.argv[2])
assert candidate in {"lean", "pydantic"}, candidate
seed = get_json(f"/v1/memory/{urllib.parse.quote(MEMORY_KEY, safe='')}")
assert seed["value"] == SEED_VALUE, seed

history = []
task_ids = []
answers = []
for prompt in TURNS:
    history.append({"role": "user", "content": prompt})
    answer, task_id = post_turn(candidate, history)
    task_ids.append(task_id)
    answers.append(answer)
    history.append({"role": "assistant", "content": answer})

fresh_answer, task_id = post_turn(candidate, [{"role": "user", "content": FRESH_RECALL}])
task_ids.append(task_id)
stored = get_json(f"/v1/memory/{urllib.parse.quote(MEMORY_KEY, safe='')}")
print(json.dumps({
    "attempt": attempt,
    "candidate": candidate,
    "task_ids": task_ids,
    "answers": answers,
    "fresh_context_recall": fresh_answer,
    "stored_memory": stored,
}, ensure_ascii=False), flush=True)
