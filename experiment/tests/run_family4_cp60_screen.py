"""Run a balanced family 4 screen on the disposable Amber memory fixture."""

import fcntl
import json
import subprocess
import time
import uuid
from pathlib import Path


from compose_scope import compose_command


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = compose_command("experiment/compose.yaml")
KEY = "deployment_note_heading_order"
SEED = "service name, change, rollout status"
UPDATED = "change, service name, rollout status"
ORDER = ("pydantic", "lean", "lean", "pydantic", "pydantic", "lean")


def compose(*args, timeout=120, check=True):
    return subprocess.run(
        COMPOSE + list(args), cwd=ROOT, capture_output=True, text=True,
        timeout=timeout, check=check,
    )


def db(sql):
    return compose("exec", "-T", "postgres", "psql", "-U", "fixture_writer",
                   "-d", "hades_lab", "-v", "ON_ERROR_STOP=1", "-Atc", sql).stdout.strip()


def memory_value():
    raw = db("SELECT value::text FROM scoped_memory WHERE user_id='user-amber' "
             f"AND domain_id='domain-home-amber' AND memory_key='{KEY}';")
    return json.loads(raw) if raw else None


def seed_memory(value):
    db("INSERT INTO scoped_memory (user_id,domain_id,memory_key,value) "
       f"VALUES ('user-amber','domain-home-amber','{KEY}',to_jsonb('{value}'::text)) "
       "ON CONFLICT (user_id,domain_id,memory_key) DO UPDATE "
       "SET value=EXCLUDED.value,updated_at=now();")
    assert memory_value() == value


def durable_tasks(task_ids):
    ids = ",".join("'" + str(uuid.UUID(item)) + "'::uuid" for item in task_ids)
    raw = db("SELECT coalesce(json_agg(json_build_object('task_id',x.task_id,'state',x.state,"
             "'effect_count',x.effect_count,'effect_states',x.effect_states) ORDER BY x.updated_at), "
             "'[]'::json)::text FROM (SELECT t.task_id,t.state,max(t.updated_at) updated_at,"
             "count(e.effect_id) effect_count,coalesce(array_agg(e.state) FILTER "
             "(WHERE e.effect_id IS NOT NULL),'{}') effect_states FROM tasks t "
             f"LEFT JOIN effects e USING(task_id) WHERE t.task_id IN ({ids}) "
             "GROUP BY t.task_id,t.state) x;")
    return json.loads(raw)


def close_task_for_review(task_id):
    script = r'''import json,sys,urllib.request
base="http://tool-gateway:8080"; token="fixture-token-amber"; task_id=sys.argv[1]
headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"}
request=urllib.request.Request(base+"/v1/tasks/"+task_id,headers={"Authorization":headers["Authorization"]})
with urllib.request.urlopen(request,timeout=10) as response: task=json.load(response)
if task["state"] in {"RUNNING","WAITING"}:
 checkpoint=task.get("checkpoint") or {}; checkpoint.setdefault("summary","Operator closed disposable family 4 trial after outcome inspection"); checkpoint.setdefault("completed",[]); checkpoint.setdefault("pending",[]); checkpoint["operator_review_required"]=True; checkpoint["operator_closed_after_trial"]=True
 body=json.dumps({"state":"FAILED","checkpoint":checkpoint}).encode()
 request=urllib.request.Request(base+"/v1/tasks/"+task_id+"/checkpoint",data=body,headers=headers,method="POST")
 with urllib.request.urlopen(request,timeout=10) as response: task=json.load(response)
print(json.dumps(task))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script, task_id)
    return json.loads(result.stdout.strip().splitlines()[-1])


def normalize(text):
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in text).split())


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="experiment/results/family4_deployment_note_cp60_8b.jsonl")
    args = parser.parse_args()
    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = Path("/tmp/hades-v3-cp60-family4.lock")
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        existing_memory = memory_value()
        if existing_memory not in {None, SEED}:
            raise RuntimeError(f"synthetic memory key {KEY} has an unexpected value; refusing to overwrite")
        records = []
        completed_ids = []
        clean_to_remove = False
        try:
            with output_path.open("w", encoding="utf-8") as out:
                for attempt, candidate in enumerate(ORDER, 1):
                    seed_memory(SEED)
                    run = compose(
                        "run", "-T", "--rm", "--no-deps", "test-runner",
                        "python", "/app/tests/family4_cp60_attempt.py", candidate,
                        str(attempt), timeout=2700, check=False,
                    )
                    lines = [line for line in run.stdout.splitlines() if line.strip()]
                    if run.returncode != 0 or not lines:
                        diagnostic = {
                            "attempt": attempt, "candidate": candidate,
                            "runner_exit": run.returncode, "stdout": run.stdout,
                            "stderr": run.stderr, "memory_after": memory_value(),
                        }
                        out.write(json.dumps(diagnostic, ensure_ascii=False) + "\n")
                        out.flush()
                        raise RuntimeError(f"candidate attempt {attempt} failed; fixture preserved for inspection")
                    summary = json.loads(lines[-1])
                    task_rows = durable_tasks(summary["task_ids"])
                    operator_closed = []
                    for row in task_rows:
                        if row["state"] in {"RUNNING", "WAITING"}:
                            if row["effect_count"] != 0:
                                raise RuntimeError(f"nonterminal task has effects; inspect before cleanup: {row}")
                            operator_closed.append(close_task_for_review(row["task_id"]))
                    task_rows = durable_tasks(summary["task_ids"])
                    completed_ids.extend(summary["task_ids"])
                    actual = memory_value()
                    record = {
                        "profile": "Qwen3-8B-Q4_K_M-cpu-n_ctx40960",
                        "attempt": attempt, "candidate": candidate,
                        "task_summaries": [json.loads(line) for line in lines[:-1]],
                        "result": summary, "durable_tasks": task_rows,
                        "operator_closed_tasks": operator_closed,
                        "canonical_memory_after": actual,
                        "exact_postcondition": actual == UPDATED,
                        "fresh_recall_contains_updated_value": normalize(UPDATED) in normalize(summary["fresh_context_recall"]),
                    }
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out.flush()
                    records.append(record)
                    print(json.dumps({"attempt": attempt, "candidate": candidate,
                                      "memory": actual, "fresh_recall": summary["fresh_context_recall"],
                                      "tasks": task_rows}), flush=True)
                    if (len(task_rows) != 4 or
                            any(row["state"] not in {"COMPLETED", "FAILED"} or row["effect_count"] != 0 for row in task_rows)):
                        raise RuntimeError(f"trial {attempt} has a nonterminal task or effect; inspect before cleanup")
                    time.sleep(1)
                clean_to_remove = len(records) == len(ORDER)
        finally:
            if clean_to_remove:
                # Every run is terminal and the only key is this unique disposable fixture key.
                db(f"DELETE FROM scoped_memory WHERE user_id='user-amber' AND domain_id='domain-home-amber' AND memory_key='{KEY}';")
                if memory_value() is not None:
                    raise RuntimeError("synthetic memory cleanup did not verify")
                print(json.dumps({"final_memory_cleanup": "verified_absent",
                                  "attempts": len(records), "task_ids": completed_ids}), flush=True)


if __name__ == "__main__":
    main()
