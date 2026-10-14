"""One bounded CP75 correction or fresh-context recall against a disposable fixture."""

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import psycopg


GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
TOKEN = "fixture-token-amber"
CASES = {
    "tone": {
        "key": "cp75-tone-scalar",
        "before": "concise",
        "after": "warm and professional",
        "correct": "Please update my saved report tone: I prefer concise currently; change it to warm and professional.",
        "correct_terms": ["warm", "professional"],
        "recall": "What tone is saved for my reports?",
        "answer_terms": ["warm", "professional"],
    },
    "weekly": {
        "key": "cp75-weekly-structure",
        "before": {"format": "paragraphs", "length": "detailed"},
        "after": {"format": "3 short bullet points", "length": "brief"},
        "correct": "I changed my mind about the weekly summary. Use 3 short bullet points and keep it brief instead of detailed paragraphs.",
        "correct_terms": ["bullet", "brief"],
        "recall": "How should my weekly summary be formatted?",
        "answer_terms": ["bullet", "brief"],
    },
    "reminders": {
        "key": "cp75-reminder-time",
        "before": ["morning", "weekdays"],
        "after": ["late afternoon", "weekdays"],
        "correct": "Correction to my reminder preference: keep weekdays, but move reminders from morning to late afternoon.",
        "correct_terms": ["late", "afternoon"],
        "recall": "When do I prefer weekday reminders?",
        "answer_terms": ["late", "afternoon"],
    },
}


def request_json(url, token=None, body=None, timeout=600):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
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


def get_task(task_id):
    status, task = request_json(f"{GATEWAY}/v1/tasks/{task_id}", TOKEN)
    if status != 200:
        raise RuntimeError(f"task readback failed with HTTP {status}")
    return task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("pydantic", "lean"), required=True)
    parser.add_argument("--case", choices=tuple(CASES), required=True)
    parser.add_argument("--phase", choices=("correct", "resume", "recall", "cleanup"), required=True)
    parser.add_argument("--task-id")
    args = parser.parse_args()
    case = CASES[args.case]
    memory_path = "/v1/memory/" + urllib.parse.quote(case["key"], safe="")

    if args.phase == "cleanup":
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM scoped_memory WHERE user_id='user-amber' AND memory_key=%s", (case["key"],))
        print(json.dumps({"candidate": args.candidate, "case": args.case, "phase": "cleanup",
                          "canonical_fixture_removed": True}, sort_keys=True))
        return

    if args.phase == "correct":
        status, existing = request_json(GATEWAY + memory_path, TOKEN)
        if status != 404:
            raise RuntimeError("fixture key already exists; refusing to overwrite a trial seed")
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO scoped_memory (user_id,domain_id,memory_key,value) "
                "VALUES ('user-amber','domain-home-amber',%s,%s) "
                "ON CONFLICT (user_id,domain_id,memory_key) DO NOTHING "
                "RETURNING memory_key,value,revision",
                (case["key"], psycopg.types.json.Jsonb(case["before"])),
            )
            seeded = cur.fetchone()
        if seeded is None:
            raise RuntimeError("fixture seed collided; refusing to overwrite a trial record")
        before = {"memory_key": seeded[0], "value": seeded[1], "revision": seeded[2]}
        message = case["correct"]
    elif args.phase == "resume":
        if not args.task_id:
            raise RuntimeError("resume phase requires the original task ID")
        status, before = request_json(GATEWAY + memory_path, TOKEN)
        if status != 200 or before.get("value") != case["after"]:
            raise RuntimeError("resume phase lacks independently verified corrected value")
        message = (
            "Continue the existing task. Read its checkpoint and confirmed effects. "
            "The requested memory correction is already persisted; do not call memory_correct "
            "or memory_write again. If all requested work is verified, persist the task "
            "completion checkpoint before replying."
        )
    else:
        status, before = request_json(GATEWAY + memory_path, TOKEN)
        if status != 200 or before.get("value") != case["after"]:
            raise RuntimeError("fresh recall phase has no independently verified corrected value")
        message = case["recall"]

    request_body = {
        "candidate": args.candidate,
        "user_token": TOKEN,
        "messages": [{"role": "user", "content": message}],
    }
    if args.phase == "resume":
        request_body["task_id"] = args.task_id
    status, result = request_json(CANDIDATE_API + "/api/turn", body=request_body)
    if status != 200:
        raise RuntimeError(f"candidate request failed with HTTP {status}")
    task = get_task(result["task_id"])
    answer = result.get("text", "")
    tools = task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", [])
    output = {
        "candidate": args.candidate,
        "case": args.case,
        "phase": args.phase,
        "task_id": result.get("task_id"),
        "task_state": task.get("state"),
        "tools": tools,
        "effect_count": len(task.get("effects", [])),
        "effects": task.get("effects", []),
        "usage": result.get("usage", {}),
        "model_generations": result.get("model_generations"),
        "duration_ms": result.get("duration_ms"),
        "answer": answer,
    }

    if args.phase == "correct":
        status, canonical = request_json(GATEWAY + memory_path, TOKEN)
        output["seed_revision"] = before.get("revision")
        output["canonical"] = canonical if status == 200 else {"http_status": status}
        effects = task.get("effects", [])
        output["passed"] = (
            task.get("state") == "COMPLETED"
            and tools.count("memory_search") >= 1
            and tools.count("memory_correct") == 1
            and set(tools) <= {"memory_search", "memory_correct"}
            and len(effects) == 1
            and effects[0].get("state") == "CONFIRMED"
            and effects[0].get("effect_kind") == "MEMORY_MUTATION"
            and effects[0].get("request", {}).get("memory_key") == case["key"]
            and effects[0].get("request", {}).get("expected_revision") == before.get("revision")
            and canonical.get("value") == case["after"]
            and canonical.get("revision") == before.get("revision", 0) + 1
            and all(term in answer.casefold() for term in case["correct_terms"])
        )
    elif args.phase == "resume":
        status, canonical = request_json(GATEWAY + memory_path, TOKEN)
        output["canonical"] = canonical if status == 200 else {"http_status": status}
        output["passed"] = (
            task.get("state") == "COMPLETED"
            and canonical.get("value") == case["after"]
            and len(task.get("effects", [])) == 1
            and task["effects"][0].get("state") == "CONFIRMED"
            and all(term in answer.casefold() for term in case["correct_terms"])
        )
    else:
        folded = answer.casefold()
        output["canonical"] = before
        output["passed"] = (
            task.get("state") == "COMPLETED"
            and tools.count("memory_search") >= 1
            and set(tools) == {"memory_search"}
            and not task.get("effects")
            and all(term in folded for term in case["answer_terms"])
        )

    print(json.dumps(output, ensure_ascii=False, sort_keys=True), flush=True)
    if not output["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
