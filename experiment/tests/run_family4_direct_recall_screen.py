"""Run a balanced, isolated direct-recall screen on the disposable fixture."""

import json
import time
import urllib.parse
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
MEMORY_KEY = "meeting_agenda_order"
SEED_VALUE = "updates, blockers, then decisions"
UPDATED_VALUE = "decisions, updates, then blockers"
TURNS = (
    "What order did I choose for the monthly planning meeting agenda?",
    "Change my saved order for the monthly planning meeting agenda from updates, blockers, then decisions to decisions, updates, then blockers.",
    "For the next monthly planning meeting, what comes first in the agenda?",
)
FRESH_RECALL = "What agenda order did I choose for the monthly planning meeting?"
ATTEMPTS = ("pydantic", "lean", "lean", "pydantic", "pydantic", "lean")


def request_json(method, url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read())


def gateway(path):
    return request_json("GET", GATEWAY + path)


def post_turn(candidate, messages, attempt, turn):
    result = request_json("POST", CANDIDATE_API + "/api/turn", {
        "candidate": candidate,
        "user_token": TOKEN,
        "messages": messages,
    })
    task = gateway(f"/v1/tasks/{result['task_id']}")
    record = {
        "candidate": candidate,
        "attempt": attempt,
        "turn": turn,
        "task_id": result["task_id"],
        "task_state": task["state"],
        "tools": task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", []),
        "tool_evidence": result.get("tool_evidence", []),
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms"),
        "text": result.get("text", ""),
    }
    print(json.dumps(record), flush=True)
    if task["state"] != "COMPLETED":
        raise RuntimeError(f"candidate task failed: {result['task_id']}")
    return result.get("text", "")


for index, candidate in enumerate(ATTEMPTS, 1):
    # Reset the unique synthetic fixture row before every independent attempt.
    seeded = request_json("POST", GATEWAY + "/v1/memory", {
        "key": MEMORY_KEY,
        "value": SEED_VALUE,
    })
    assert seeded["value"] == SEED_VALUE, seeded
    history = []
    for turn, prompt in enumerate(TURNS, 1):
        history.append({"role": "user", "content": prompt})
        answer = post_turn(candidate, history, index, turn)
        history.append({"role": "assistant", "content": answer})
    fresh = post_turn(candidate, [{"role": "user", "content": FRESH_RECALL}], index, "fresh")
    stored = gateway(f"/v1/memory/{urllib.parse.quote(MEMORY_KEY, safe='')}")
    search = gateway("/v1/memory/search?q=monthly+planning+meeting+agenda+order")
    record = {
        "candidate": candidate,
        "attempt": index,
        "fresh_context_recall": fresh,
        "stored_memory": stored,
        "search_results": search.get("memories", []),
    }
    print(json.dumps(record), flush=True)
    if stored["value"] != UPDATED_VALUE:
        raise RuntimeError(f"canonical correction failed in attempt {index}: {stored}")
    time.sleep(1)
