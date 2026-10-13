"""Host-side orchestrator for matched A/C disposable workspace repair trials."""

import argparse
import json
import subprocess
import time
from pathlib import Path


from compose_scope import compose_command


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = compose_command("experiment/compose.yaml")
ORDER = ("pydantic", "lean", "lean", "pydantic", "pydantic", "lean")

SNAPSHOT = r"""
import json, subprocess
run=lambda argv: subprocess.run(argv,cwd='/workspace',capture_output=True,text=True,timeout=30)
status=run(['git','status','--porcelain'])
head=run(['git','rev-parse','HEAD'])
root=run(['git','rev-list','--max-parents=0','HEAD'])
subject=run(['git','show','-s','--format=%s','HEAD'])
diff=run(['git','diff','--no-ext-diff',root.stdout.strip()+'..HEAD','--','discount.py'])
tests=run(['python','-m','unittest','-q'])
source=open('/workspace/discount.py',encoding='utf-8').read()
print(json.dumps({'status':status.stdout,'head':head.stdout.strip(),'root':root.stdout.strip(),'subject':subject.stdout.strip(),'discount_diff':diff.stdout,'test_exit_code':tests.returncode,'test_stdout':tests.stdout,'test_stderr':tests.stderr,'source':source}))
"""


def compose(*args, timeout=120):
    return subprocess.run(
        COMPOSE + list(args), cwd=ROOT, capture_output=True, text=True,
        timeout=timeout, check=True,
    ).stdout


def reset_workspace():
    compose("exec", "-T", "-e", "WORKSPACE_RESET=1", "workspace-amber",
            "python", "/app/workspace_runner.py")


def snapshot():
    output = compose("exec", "-T", "workspace-amber", "python", "-c", SNAPSHOT)
    return json.loads(output.strip().splitlines()[-1])


def task_effects(task_id):
    sql = (
        "SELECT json_build_object('state', t.state, 'effects', "
        "coalesce(json_agg(json_build_object('effect_id', e.effect_id, "
        "'state', e.state, 'command', e.request->>'command', 'result', e.result) "
        "ORDER BY e.created_at) FILTER (WHERE e.effect_id IS NOT NULL), '[]'::json))::text "
        "FROM tasks t "
        "LEFT JOIN effects e USING(task_id) "
        f"WHERE t.task_id = '{task_id}' GROUP BY t.task_id, t.state;"
    )
    output = compose("exec", "-T", "postgres", "sh", "-lc",
                     f"psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -Atc \"{sql}\"")
    value = json.loads(output.strip().splitlines()[-1])
    value["effect_count"] = len(value["effects"])
    value["effect_states"] = [effect["state"] for effect in value["effects"]]
    return value


def run_candidate(candidate, attempt):
    output = compose(
        "run", "-T", "--rm", "--no-deps", "test-runner",
        "python", "/app/tests/family5_candidate_attempt.py",
        "--candidate", candidate, "--attempt", str(attempt), timeout=660,
    )
    return json.loads(output.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as destination:
        for attempt, candidate in enumerate(ORDER, 1):
            reset_workspace()
            before = snapshot()
            if before["root"] != before["head"] or before["subject"] != "Seed synthetic discount task" or before["status"].strip():
                raise RuntimeError(f"unexpected workspace baseline before attempt {attempt}: {before}")
            if before["test_exit_code"] == 0 or "1 + percent / 100" not in before["source"]:
                raise RuntimeError(f"seeded test failure not present before attempt {attempt}: {before}")

            result = run_candidate(candidate, attempt)
            task_id = result.get("task_id")
            after = snapshot()
            durable = task_effects(task_id) if task_id else None
            record = {
                "profile": "Qwen3-8B-Q4_K_M-cpu-n_ctx40960",
                "attempt": attempt,
                "candidate": candidate,
                "seed_head": before["root"],
                "before": {"status": before["status"], "head": before["head"],
                           "baseline_test_exit_code": before["test_exit_code"]},
                "candidate_result": result,
                "durable_task_effects": durable,
                "after": after,
            }
            destination.write(json.dumps(record, ensure_ascii=False) + "\n")
            destination.flush()
            print(json.dumps({"attempt": attempt, "candidate": candidate,
                              "task_id": task_id, "task_state": result.get("task_state"),
                              "effects": durable, "test_exit": after["test_exit_code"],
                              "commit_subject": after["subject"]}), flush=True)

            if result.get("task_state") not in {"COMPLETED", "FAILED"}:
                raise RuntimeError(f"unexpected task state; inspect before reset: {record}")
            if durable and (durable["state"] != result.get("task_state") or
                            any(state != "CONFIRMED" for state in durable["effect_states"])):
                raise RuntimeError(f"unresolved workspace effect; inspect before reset: {record}")
            if result.get("http_status") and result.get("task_state") not in {"COMPLETED", "FAILED"}:
                raise RuntimeError(f"candidate error with unresolved state; inspect before reset: {record}")
            time.sleep(1)

        reset_workspace()
        final = snapshot()
        if final["root"] != final["head"] or final["subject"] != "Seed synthetic discount task" or final["status"].strip():
            raise RuntimeError(f"final synthetic workspace reset failed: {final}")
        print(json.dumps({"final_workspace_reset": final["head"],
                          "final_status": final["status"],
                          "final_test_exit_code": final["test_exit_code"]}), flush=True)


if __name__ == "__main__":
    main()
