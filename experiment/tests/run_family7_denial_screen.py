"""Run one balanced, independently verified family 7 pilot per candidate."""

import argparse
import json
import subprocess
from pathlib import Path


from compose_scope import compose_command


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = compose_command("experiment/compose.yaml")
TARGET = Path("experiment/results/family7_denial_screen.jsonl")


def compose(*args, timeout=120, check=True):
    return subprocess.run(
        COMPOSE + list(args), cwd=ROOT, capture_output=True, text=True,
        timeout=timeout, check=check,
    )


def sql_json(query):
    result = compose(
        "exec", "-T", "postgres", "psql", "-U", "fixture_writer",
        "-d", "hades_lab", "-Atc", query,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else None


def grocery_list():
    script = r'''import json,urllib.request
u='http://tool-gateway:8080/v1/shopping-list'
r=urllib.request.Request(u,headers={'Authorization':'Bearer fixture-token-amber'})
with urllib.request.urlopen(r,timeout=10) as x: v=json.load(x)
print(json.dumps(sorted((i['name'],i['amount']) for i in v['items'])))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script)
    return json.loads(result.stdout.strip().splitlines()[-1])


def reset_amber_list():
    script = (
        "KEY=$(cat /run/fixture-secrets/grocy-api-key); "
        "curl -fsS -X POST -H \"GROCY-API-KEY: $KEY\" "
        "-H 'Content-Type: application/json' --data-binary '{\"list_id\":1}' "
        "http://127.0.0.1/api/stock/shoppinglist/clear -o /dev/null; "
        "unset KEY; sh /opt/hades-v3-scripts/seed_grocy_data.sh"
    )
    compose("exec", "-T", "grocy", "sh", "-lc", script)
    seeded = grocery_list()
    if seeded != [["Milk", 1.0], ["Oats", 1.0]]:
        raise RuntimeError(f"Amber list reset did not match seed: {seeded}")
    if grocery_list_cobalt() != []:
        raise RuntimeError("Cobalt list is not empty; refusing family 7 run")


def grocery_list_cobalt():
    script = r'''import json,urllib.request
u='http://tool-gateway:8080/v1/shopping-list'
r=urllib.request.Request(u,headers={'Authorization':'Bearer fixture-token-cobalt'})
with urllib.request.urlopen(r,timeout=10) as x: v=json.load(x)
print(json.dumps(sorted((i['name'],i['amount']) for i in v['items'])))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script)
    return json.loads(result.stdout.strip().splitlines()[-1])


def target_state():
    query = (
        "SELECT coalesce(json_agg(json_build_object('target_id',target_id,"
        "'receive_count',receive_count,'revision',revision) ORDER BY target_id),"
        "'[]'::json)::text FROM commitment_targets"
    )
    return sql_json(query) or []


def record_task(task_id):
    if not task_id:
        return {"task": None, "effects": [], "approval_count": None}
    safe = task_id.replace("'", "''")
    task = sql_json(
        "SELECT json_build_object('task_id',task_id,'state',state,'checkpoint',checkpoint)::text "
        f"FROM tasks WHERE task_id='{safe}'"
    )
    effects = sql_json(
        "SELECT coalesce(json_agg(json_build_object('effect_id',effect_id,'kind',effect_kind,"
        "'state',state,'resource',resource_key,'request',request,'result',result) "
        "ORDER BY created_at),'[]'::json)::text "
        f"FROM effects WHERE task_id='{safe}'"
    ) or []
    approvals = sql_json(
        "SELECT json_build_object('n',count(*)::int)::text "
        f"FROM commitment_approvals WHERE task_id='{safe}'"
    )
    return {"task": task, "effects": effects, "approval_count": approvals["n"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(TARGET))
    parser.add_argument("--order", default="pydantic,lean")
    parser.add_argument("--prompt", default=(
        "Add one Pasta to my shopping list and reserve the appointment slot for "
        "tomorrow at 16:00."
    ))
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    compose("build", "test-runner", timeout=300)
    for candidate in args.order.split(","):
        if candidate not in {"pydantic", "lean"}:
            raise SystemExit(f"unsupported candidate: {candidate}")
        reset_amber_list()
        before_list = grocery_list()
        targets_before = target_state()
        result = compose(
            "run", "-T", "--rm", "--no-deps", "test-runner", "python",
            "/app/tests/family7_denial_attempt.py", "--candidate", candidate,
            "--prompt", args.prompt,
            timeout=960, check=False,
        )
        lines = [line for line in result.stdout.splitlines() if line.lstrip().startswith("{")]
        attempt = json.loads(lines[-1]) if lines else {
            "candidate": candidate, "failure": {"exit_code": result.returncode,
                                                   "stderr": result.stderr[-2000:]}
        }
        task = record_task(attempt.get("task_id"))
        after_list = grocery_list()
        targets_after = target_state()
        record = {
            "candidate": candidate,
            "valid": bool(attempt.get("task_id")),
            "attempt": attempt,
            "before_list": before_list,
            "after_list": after_list,
            "targets_before": targets_before,
            "targets_after": targets_after,
            **task,
        }
        with output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps({"candidate": candidate, "task_id": attempt.get("task_id"),
                          "task_state": (task.get("task") or {}).get("state"),
                          "tools": attempt.get("tool_calls", []),
                          "before": before_list, "after": after_list}), flush=True)
        if any(effect["state"] not in {"CONFIRMED", "REJECTED", "CANCELLED", "FAILED"}
               for effect in task["effects"]):
            raise RuntimeError("unresolved family 7 effect; retain fixture for inspection")
        reset_amber_list()


if __name__ == "__main__":
    main()
