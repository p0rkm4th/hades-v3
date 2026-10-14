"""Verify a confirmed workspace effect is parked before stateless model resume."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request

import psycopg

GATEWAY = os.environ["GATEWAY_URL"]
CANDIDATE_API = os.environ["CANDIDATE_API_URL"]
DATABASE_URL = os.environ["DATABASE_URL"]
SCRIPTED_STATE = "http://cp68-scripted-ollama:11434/__test/state"
TOKEN = "fixture-token-amber"


def request_json(url: str, *, token: str | None = None, body: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers=headers,
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def main() -> None:
    attempts_before = request_json(SCRIPTED_STATE)[1]["attempts"]
    with psycopg.connect(DATABASE_URL) as conn:
        memory_before = conn.execute(
            "SELECT user_id,count(*) FROM scoped_memory GROUP BY user_id ORDER BY user_id"
        ).fetchall()
    status, task = request_json(GATEWAY + "/v1/tasks", token=TOKEN, body={
        "goal": "CP88 synthetic confirmed workspace resume guard",
    })
    assert status == 201, (status, task)
    task_id = task["task_id"]
    operation_id = hashlib.sha256(f"{task_id}:cp88-original-call".encode()).hexdigest()

    status, effect = request_json(GATEWAY + "/v1/workspace/exec", token=TOKEN, body={
        "task_id": task_id,
        "command": "pwd",
        "operation_id": operation_id,
    })
    assert status == 200 and effect["state"] == "CONFIRMED", (status, effect)

    status, blocked = request_json(CANDIDATE_API, body={
        "candidate": "lean",
        "user_token": TOKEN,
        "task_id": task_id,
        "messages": [{"role": "user", "content": "Continue the synthetic task."}],
    })
    assert status == 409, (status, blocked)
    assert blocked.get("task_state") == "WAITING" and blocked.get("operator_review_required"), blocked

    status, durable_task = request_json(GATEWAY + f"/v1/tasks/{task_id}", token=TOKEN)
    assert status == 200 and durable_task["state"] == "WAITING", (status, durable_task)
    checkpoint = durable_task["checkpoint"]
    assert checkpoint.get("workspace_resume_requires_persisted_identity") is True, checkpoint
    assert checkpoint.get("operator_review_required") is True, checkpoint
    assert checkpoint.get("candidate_turn", {}).get("error_type") == \
        "workspace_resume_requires_persisted_identity", checkpoint
    assert checkpoint.get("effect_outcome_uncertain") is False, checkpoint

    effect_id = effect["effect_id"]
    effects = durable_task.get("effects", [])
    assert len(effects) == 1 and effects[0]["effect_id"] == effect_id, effects
    assert effects[0]["effect_kind"] == "WORKSPACE_COMMAND", effects[0]
    assert effects[0]["state"] == "CONFIRMED", effects[0]
    assert effects[0].get("operation_id") == operation_id, effects[0]

    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "SELECT effect_id,state,request->>'operation_id' FROM effects "
            "WHERE task_id=%s AND effect_kind='WORKSPACE_COMMAND'",
            (task_id,),
        ).fetchall()
    assert len(rows) == 1, rows
    assert (str(rows[0][0]), rows[0][1], rows[0][2]) == (
        effect_id, "CONFIRMED", operation_id,
    ), rows
    with psycopg.connect(DATABASE_URL) as conn:
        memory_after = conn.execute(
            "SELECT user_id,count(*) FROM scoped_memory GROUP BY user_id ORDER BY user_id"
        ).fetchall()
    assert memory_after == memory_before, (memory_before, memory_after)
    attempts_after = request_json(SCRIPTED_STATE)[1]["attempts"]
    assert attempts_after == attempts_before, (attempts_before, attempts_after)
    print("PASS CP88: one confirmed synthetic effect; durable task WAITING for review; no model retry")


if __name__ == "__main__":
    main()
