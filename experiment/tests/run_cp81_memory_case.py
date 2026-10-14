"""One synthetic CP81 memory correction or fresh-context recall trial."""

import argparse
import json
import os
import uuid
import urllib.error
import urllib.parse
import urllib.request

import psycopg
from psycopg.types.json import Jsonb

GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
TOKEN = "fixture-token-amber"
CASES = {
    "coffee_scalar": {
        "key_prefix": "coffee-preference",
        "before": "medium roast", "after": "light roast",
        "correct": "Update my saved coffee preference: switch from medium roast to light roast.",
        "correct_terms": ["light", "roast"],
        "recall": "Which roast do I prefer for coffee?",
        "answer_terms": ["light", "roast"],
    },
    "weekly_structured": {
        "key_prefix": "weekly-planning-note",
        "before": {"layout": "paragraphs", "length": "long"},
        "after": {"layout": "numbered checklist", "length": "concise"},
        "correct": "For my weekly planning note, replace long paragraphs with a concise numbered checklist.",
        "correct_terms": ["numbered", "concise"],
        "recall": "How should my weekly planning note be laid out?",
        "answer_terms": ["numbered", "concise"],
    },
    "reminder_list": {
        "key_prefix": "weekday-reminders",
        "before": ["morning", "weekdays"], "after": ["late afternoon", "weekdays"],
        "correct": "Change my weekday reminder time from morning to late afternoon; keep it on weekdays.",
        "correct_terms": ["late", "afternoon"],
        "recall": "When do I want reminders on weekdays?",
        "answer_terms": ["late", "afternoon"],
    },
}


def request_json(url, token=None, body=None, orchestrator=False, timeout=600):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if orchestrator:
        headers["X-Hades-Orchestrator"] = os.environ["ORCHESTRATOR_SECRET"]
    request = urllib.request.Request(
        url, data=None if body is None else json.dumps(body).encode(),
        headers=headers, method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            value = json.loads(exc.read())
        except json.JSONDecodeError:
            value = {"error": "non-json error response"}
        return exc.code, value


def run_candidate(candidate, case_name, phase, replicate, task_id=None):
    case = CASES[case_name]
    source_task_id = None
    if phase == "correct":
        key = f"cp81-{case['key_prefix']}-r{replicate}-{uuid.uuid4().hex[:8]}"
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO scoped_memory (user_id,domain_id,memory_key,value) "
                "VALUES ('user-amber','domain-home-amber',%s,%s) RETURNING memory_key,value,revision",
                (key, Jsonb(case["before"])),
            )
            seeded = cur.fetchone()
        if seeded is None or seeded[2] != 1:
            raise RuntimeError("fresh synthetic memory seed was not created at revision 1")
        contract = {"version": 1, "kind": "memory_correction", "required": [{
            "effect_kind": "MEMORY_MUTATION", "memory_key": key,
            "expected_revision": seeded[2], "value": case["after"],
        }]}
        status, task = request_json(GATEWAY + "/v1/tasks", TOKEN, {
            "goal": "Complete the requested synthetic memory correction.",
            "completion_contract": contract,
        }, orchestrator=True)
        if status != 201:
            raise RuntimeError(f"trusted task creation failed with HTTP {status}")
        task_id = task["task_id"]
        message = case["correct"]
    else:
        if not task_id:
            raise ValueError("recall phase requires the correction task ID")
        source_task_id = task_id
        status, task = request_json(f"{GATEWAY}/v1/tasks/{source_task_id}", TOKEN)
        if status != 200:
            raise RuntimeError("original correction task is not readable")
        effects = task.get("effects", [])
        if len(effects) != 1 or effects[0].get("state") != "CONFIRMED":
            raise RuntimeError("fresh recall requires one independently confirmed correction effect")
        key = effects[0].get("request", {}).get("memory_key")
        if not isinstance(key, str):
            raise RuntimeError("confirmed effect did not retain the stable memory key")
        status, memory = request_json(
            GATEWAY + "/v1/memory/" + urllib.parse.quote(key, safe=""), TOKEN,
        )
        if status != 200 or memory.get("value") != case["after"]:
            raise RuntimeError("canonical memory does not contain the corrected value")
        status, recall_task = request_json(GATEWAY + "/v1/tasks", TOKEN, {
            "goal": "Recall the saved synthetic preference in a new context.",
        })
        if status != 201:
            raise RuntimeError(f"fresh recall task creation failed with HTTP {status}")
        task_id = recall_task["task_id"]
        message = case["recall"]

    status, result = request_json(CANDIDATE_API + "/api/turn", body={
        "candidate": candidate, "user_token": TOKEN,
        "messages": [{"role": "user", "content": message}],
        "task_id": task_id,
    })
    if status != 200:
        raise RuntimeError(f"candidate turn failed with HTTP {status}")
    status, final_task = request_json(f"{GATEWAY}/v1/tasks/{task_id}", TOKEN)
    if status != 200:
        raise RuntimeError("durable task readback failed")
    tools = (final_task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", []))
    effects = final_task.get("effects", [])
    output = {
        "candidate": candidate, "case": case_name, "phase": phase,
        "replicate": replicate, "task_id": task_id, "task_state": final_task.get("state"),
        "source_task_id": source_task_id,
        "tools": tools, "effect_count": len(effects),
        "effect_ids": [effect.get("effect_id") for effect in effects],
        "canonical_value": None, "canonical_revision": None,
        "model_generations": result.get("model_generations"),
        "duration_ms": result.get("duration_ms"), "answer": result.get("text", ""),
    }
    if phase == "correct":
        status, canonical = request_json(
            GATEWAY + "/v1/memory/" + urllib.parse.quote(key, safe=""), TOKEN,
        )
        output.update({"memory_key": key,
                       "canonical_value": canonical.get("value") if status == 200 else None,
                       "canonical_revision": canonical.get("revision") if status == 200 else None})
        output["passed"] = (
            final_task.get("state") == "COMPLETED"
            and tools.count("memory_search") >= 1 and tools.count("memory_correct") == 1
            and set(tools) <= {"memory_search", "memory_read", "memory_correct"}
            and len(effects) == 1 and effects[0].get("state") == "CONFIRMED"
            and effects[0].get("task_id") == task_id
            and effects[0].get("request", {}).get("memory_key") == key
            and effects[0].get("request", {}).get("expected_revision") == 1
            and canonical.get("value") == case["after"]
            and canonical.get("revision") == 2
            and all(term in output["answer"].casefold() for term in case["correct_terms"])
        )
    else:
        output["memory_key"] = key
        output["canonical_value"] = memory["value"]
        output["canonical_revision"] = memory["revision"]
        output["passed"] = (
            final_task.get("state") == "COMPLETED"
            and tools.count("memory_search") >= 1 and set(tools) == {"memory_search"}
            and not effects
            and all(term in output["answer"].casefold() for term in case["answer_terms"])
        )
    print(json.dumps(output, ensure_ascii=False, sort_keys=True), flush=True)
    if not output["passed"]:
        raise SystemExit(1)
    return task_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("pydantic", "lean"), required=True)
    parser.add_argument("--case", choices=tuple(CASES), required=True)
    parser.add_argument("--phase", choices=("correct", "recall"), required=True)
    parser.add_argument("--replicate", type=int, choices=range(1, 10), required=True)
    parser.add_argument("--task-id")
    args = parser.parse_args()
    if args.phase == "recall" and not args.task_id:
        parser.error("--task-id is required for recall")
    run_candidate(args.candidate, args.case, args.phase, args.replicate, args.task_id)
