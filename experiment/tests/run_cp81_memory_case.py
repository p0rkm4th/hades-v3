"""One synthetic CP81 memory correction or fresh-context recall trial."""

import argparse
import json
import os
import re
import uuid
import urllib.error
import urllib.request

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
TOKEN = "fixture-token-amber"
CASES = {
    "coffee_scalar": {
        "key_prefix": "coffee-preference",
        "before": "medium roast", "after": "light roast",
        "correct": "Update my saved coffee preference: switch from medium roast to light roast.",
        "answer_phrases": ["light roast"],
        "answer_negations": [
            r"\b(?:not|isn't|is not|never)\s+(?:a\s+)?light roast\b",
            r"\b(?:do not|don't|does not|doesn't)\s+(?:use|choose|prefer|want|keep)\s+(?:a\s+)?light roast\b",
        ],
        "recall": "Which roast do I prefer for coffee?",
    },
    "weekly_structured": {
        "key_prefix": "weekly-planning-note",
        "before": {"layout": "paragraphs", "length": "long"},
        "after": {"layout": "numbered checklist", "length": "concise"},
        "correct": "For my weekly planning note, replace long paragraphs with a concise numbered checklist.",
        "answer_phrases": ["concise", "numbered checklist"],
        "answer_negations": [
            r"\bnot\s+(?:a\s+)?concise\b", r"\bnot\s+(?:a\s+)?numbered checklist\b",
            r"\b(?:do not|don't|does not|doesn't)\s+(?:use|choose|prefer|want|keep)\s+(?:a\s+)?(?:concise|numbered checklist)\b",
        ],
        "recall": "How should my weekly planning note be laid out?",
    },
    "reminder_list": {
        "key_prefix": "weekday-reminders",
        "before": ["morning", "weekdays"], "after": ["late afternoon", "weekdays"],
        "correct": "Change my weekday reminder time from morning to late afternoon; keep it on weekdays.",
        "answer_phrases": ["late afternoon", "weekdays"],
        "answer_negations": [
            r"\b(?:not|isn't|is not|never)\s+late afternoon\b",
            r"\b(?:do not|don't|does not|doesn't)\s+(?:use|choose|prefer|want|keep|set)\s+late afternoon\b",
            r"\bnot\s+weekdays\b",
        ],
        "recall": "When do I want reminders on weekdays?",
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
            try:
                return response.status, json.loads(response.read())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return response.status, {"invalid_json_response": True}
    except urllib.error.HTTPError as exc:
        try:
            value = json.loads(exc.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            value = {"error": "non-json error response"}
        return exc.code, value
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, {"transport_error_type": type(exc).__name__}


def canonical_row(memory_key):
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT memory_key,value,revision FROM scoped_memory "
            "WHERE user_id='user-amber' AND domain_id='domain-home-amber' AND memory_key=%s",
            (memory_key,),
        )
        return cur.fetchone()


def durable_task_and_effects(task_id):
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT task_id,user_id,domain_id,state,checkpoint FROM tasks "
            "WHERE task_id=%s AND user_id='user-amber' AND domain_id='domain-home-amber'",
            (task_id,),
        )
        task = cur.fetchone()
        cur.execute("SELECT effect_id,task_id,user_id,domain_id,effect_kind,resource_key,state,request,result "
                    "FROM effects WHERE task_id=%s ORDER BY created_at", (task_id,))
        return task, cur.fetchall()


def answer_matches(answer, case):
    normalized = answer.casefold()
    return (all(phrase in normalized for phrase in case["answer_phrases"])
            and not any(re.search(pattern, normalized) for pattern in case["answer_negations"]))


def candidate_error_category(status, payload):
    if status == 0:
        return "transport_error"
    if payload.get("invalid_json_response"):
        return "invalid_json_response"
    if status >= 400:
        return f"http_{status}"
    if payload.get("error"):
        return "candidate_reported_error"
    return None


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
        source_row, effects = durable_task_and_effects(source_task_id)
        if source_row is None or source_row["state"] != "COMPLETED":
            raise RuntimeError("original correction task is not durably completed")
        if len(effects) != 1 or effects[0].get("state") != "CONFIRMED":
            raise RuntimeError("fresh recall requires one independently confirmed correction effect")
        key = effects[0].get("request", {}).get("memory_key")
        if not isinstance(key, str):
            raise RuntimeError("confirmed effect did not retain the stable memory key")
        memory = canonical_row(key)
        if memory is None or memory.get("value") != case["after"]:
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
    durable_task, effects = durable_task_and_effects(task_id)
    if durable_task is None:
        raise RuntimeError("independent durable task read failed")
    checkpoint = durable_task.get("checkpoint") or {}
    candidate_turn = checkpoint.get("candidate_turn") or {}
    tools = candidate_turn.get("tools", [])
    output = {
        "candidate": candidate, "case": case_name, "phase": phase,
        "replicate": replicate, "task_id": task_id, "task_state": durable_task.get("state"),
        "source_task_id": source_task_id,
        "candidate_http_status": status,
        "candidate_error_category": candidate_error_category(status, result),
        "task_error_type": candidate_turn.get("error_type"),
        "task_finalization_reason": (checkpoint.get("task_finalization") or {}).get("reason"),
        "tools": tools, "effect_count": len(effects),
        "effect_ids": [str(effect.get("effect_id")) for effect in effects],
        "canonical_value": None, "canonical_revision": None,
        "model_generations": result.get("model_generations"),
        "duration_ms": result.get("duration_ms"),
        "answer": result.get("text", "") if status == 200 else "",
        "retry_behavior": "gateway exact/changed retry covered separately by database integration test",
    }
    if phase == "correct":
        canonical = canonical_row(key)
        output.update({"memory_key": key,
                       "canonical_value": canonical.get("value") if canonical else None,
                       "canonical_revision": canonical.get("revision") if canonical else None})
        output["durable_task_correct"] = durable_task.get("state") == "COMPLETED"
        output["tool_selection_correct"] = (
            tools.count("memory_search") >= 1 and tools.count("memory_correct") == 1
            and set(tools) <= {"memory_search", "memory_read", "memory_correct"})
        output["mutation_correct"] = (
            len(effects) == 1 and effects[0].get("state") == "CONFIRMED"
            and str(effects[0].get("task_id")) == task_id
            and effects[0].get("user_id") == "user-amber"
            and effects[0].get("domain_id") == "domain-home-amber"
            and effects[0].get("effect_kind") == "MEMORY_MUTATION"
            and effects[0].get("resource_key") == f"memory:{key}"
            and effects[0].get("request", {}).get("memory_key") == key
            and effects[0].get("request", {}).get("expected_revision") == 1
            and effects[0].get("request", {}).get("value") == case["after"]
            and effects[0].get("result", {}).get("value") == case["after"]
            and effects[0].get("result", {}).get("revision") == 2
            and canonical is not None
            and canonical.get("value") == case["after"]
            and canonical.get("revision") == 2)
        output["answer_correct"] = answer_matches(output["answer"], case)
        output["passed"] = all(output[key] for key in (
            "durable_task_correct", "tool_selection_correct", "mutation_correct", "answer_correct"))
    else:
        memory_after = canonical_row(key)
        output["memory_key"] = key
        output["canonical_value"] = memory_after.get("value") if memory_after else None
        output["canonical_revision"] = memory_after.get("revision") if memory_after else None
        output["durable_task_correct"] = durable_task.get("state") == "COMPLETED"
        output["tool_selection_correct"] = tools.count("memory_search") >= 1 and set(tools) == {"memory_search"}
        output["mutation_correct"] = (
            not effects and memory_after is not None
            and memory_after.get("value") == case["after"]
            and memory_after.get("revision") == memory.get("revision"))
        output["answer_correct"] = answer_matches(output["answer"], case)
        output["passed"] = all(output[key] for key in (
            "durable_task_correct", "tool_selection_correct", "mutation_correct", "answer_correct"))
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
