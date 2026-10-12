"""Host orchestrator for one matched family 6 restart-recovery pilot."""

import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", "experiment/compose.yaml"]


def compose(*args, timeout=120, check=True):
    return subprocess.run(COMPOSE + list(args), cwd=ROOT, capture_output=True,
                          text=True, timeout=timeout, check=check)


def sql_json(query):
    result = compose("exec", "-T", "postgres", "psql", "-U", "fixture_writer",
                     "-d", "hades_lab", "-Atc", query)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else None


def checkpoint(trial):
    goal = f"[FAMILY6 {trial}]%"
    safe_goal = goal.replace("'", "''")
    query = (
        "SELECT coalesce(json_agg(json_build_object('task_id',task_id,'state',state,"
        "'checkpoint',checkpoint) ORDER BY updated_at DESC),'[]'::json)::text "
        f"FROM tasks WHERE goal LIKE '{safe_goal}'"
    )
    tasks = sql_json(query) or []
    for task in tasks:
        saved = task.get("checkpoint") or {}
        if saved.get("family") == "family6" and saved.get("phase") == "source_inspected":
            return task
    return None


def trial_task(trial):
    goal = f"[FAMILY6 {trial}]%".replace("'", "''")
    query = (
        "SELECT coalesce(json_agg(json_build_object('task_id',task_id,'state',state,"
        "'checkpoint',checkpoint,'revision',revision) ORDER BY updated_at DESC),'[]'::json)::text "
        f"FROM tasks WHERE goal LIKE '{goal}'"
    )
    tasks = sql_json(query) or []
    return tasks[0] if tasks else None


def wait_terminal(trial, timeout=120):
    deadline = time.monotonic() + timeout
    task = trial_task(trial)
    while task and task["state"] not in {"COMPLETED", "FAILED"} and time.monotonic() < deadline:
        time.sleep(0.5)
        task = trial_task(trial)
    return task


def effects(task_id):
    query = (
        "SELECT coalesce(json_agg(json_build_object('effect_id',effect_id,'state',state,"
        "'kind',effect_kind,'resource',resource_key,'result',result) ORDER BY created_at),'[]'::json)::text "
        f"FROM effects WHERE task_id='{task_id}'"
    )
    return sql_json(query) or []


def close_waiting_task(task_id):
    script = r'''import json,sys,urllib.request
token='fixture-token-amber'; base='http://tool-gateway:8080'; task=sys.argv[1]
headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
req=urllib.request.Request(base+'/v1/tasks/'+task,headers=headers)
with urllib.request.urlopen(req,timeout=10) as r: value=json.loads(r.read())
checkpoint=value.get('checkpoint') or {}; checkpoint['operator_review_required']=True; checkpoint['operator_closed_after_pilot']=True
req=urllib.request.Request(base+'/v1/tasks/'+task+'/checkpoint',data=json.dumps({'state':'FAILED','checkpoint':checkpoint}).encode(),headers=headers,method='POST')
with urllib.request.urlopen(req,timeout=10) as r: print(json.dumps(json.loads(r.read())))'''
    return compose("run", "-T", "--rm", "--no-deps", "test-runner", "python", "-c",
                   script, task_id, timeout=30).stdout.strip().splitlines()[-1]


def snapshot():
    script = r'''import json,subprocess
r=lambda a:subprocess.run(a,cwd='/workspace',capture_output=True,text=True,timeout=30)
status=r(['git','status','--porcelain']);head=r(['git','rev-parse','HEAD']);root=r(['git','rev-list','--max-parents=0','HEAD'])
tests=r(['python','-m','unittest','-q']);source=open('/workspace/discount.py',encoding='utf-8').read()
print(json.dumps({'status':status.stdout,'head':head.stdout.strip(),'root':root.stdout.strip(),'test_exit':tests.returncode,'test_stdout':tests.stdout,'test_stderr':tests.stderr,'source':source}))'''
    result = compose("exec", "-T", "workspace-amber", "python", "-c", script)
    return json.loads(result.stdout.strip().splitlines()[-1])


def run_phase(trial, candidate, phase, task_id=None):
    command = ["run", "-T", "--rm", "--no-deps", "test-runner", "python",
               "/app/tests/family6_restart_attempt.py", "--trial", trial,
               "--candidate", candidate, "--phase", phase]
    if task_id:
        command += ["--task-id", task_id]
    return compose(*command, timeout=660, check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("lean", "pydantic"), required=True)
    parser.add_argument("--trial", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--checkpoint-timeout", type=int, default=240)
    args = parser.parse_args()
    trial = args.trial
    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    compose("exec", "-T", "-e", "WORKSPACE_RESET=1", "workspace-amber",
            "python", "/app/workspace_runner.py")
    before = snapshot()
    if before["root"] != before["head"] or before["status"].strip():
        raise RuntimeError(f"Amber workspace is not at its synthetic seed: {before}")
    if before["test_exit"] == 0 or "1 + percent / 100" not in before["source"]:
        raise RuntimeError("Expected synthetic discount defect is not present")

    initial = subprocess.Popen(
        COMPOSE + ["run", "-T", "--rm", "--no-deps", "test-runner", "python",
                   "/app/tests/family6_restart_attempt.py", "--trial", trial,
                   "--candidate", args.candidate, "--phase", "prepare"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    saved = None
    deadline = time.monotonic() + args.checkpoint_timeout
    while time.monotonic() < deadline and initial.poll() is None:
        saved = checkpoint(trial)
        if saved:
            break
        time.sleep(0.15)

    interrupted = False
    if saved:
        kill = compose("kill", "-s", "SIGKILL", "candidate-api", check=False)
        interrupted = kill.returncode == 0
    if not saved:
        initial.terminate()
    try:
        stdout, stderr = initial.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        initial.kill()
        stdout, stderr = initial.communicate()

    if not saved:
        task = wait_terminal(trial)
        task_effects = effects(task["task_id"]) if task else []
        operator_closed = False
        if task and task["state"] == "WAITING":
            if any(effect["state"] not in {"CONFIRMED", "CANCELLED"} for effect in task_effects):
                raise RuntimeError(f"Unresolved effects on waiting task; inspect before closure: {task_effects}")
            close_waiting_task(task["task_id"])
            operator_closed = True
            task = trial_task(trial)
        after = snapshot()
        record = {"candidate": args.candidate, "trial": trial, "valid": False,
                  "reason": "candidate did not persist the required recovery checkpoint; no interruption performed",
                  "task": task, "effects": task_effects,
                  "operator_closed_waiting_task": operator_closed,
                  "prepare_exit": initial.returncode, "prepare_stdout": stdout[-4000:],
                  "prepare_stderr": stderr[-4000:], "before": before, "after": after}
    else:
        task_id = saved["task_id"]
        state_after_interrupt = sql_json(
            "SELECT json_build_object('task_id',task_id,'state',state,'revision',revision,"
            f"'checkpoint',checkpoint)::text FROM tasks WHERE task_id='{task_id}'"
        )
        compose("up", "-d", "candidate-api", timeout=180)
        # Wait until only the disposable candidate API is serving again.
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            probe = compose("exec", "-T", "test-runner", "python", "-c",
                "import urllib.request; urllib.request.urlopen('http://candidate-api:8080/health',timeout=2)",
                check=False)
            if probe.returncode == 0:
                break
            time.sleep(0.5)
        resume_records = []
        for resume_round in range(1, 4):
            resumed = run_phase(trial, args.candidate, "resume", task_id)
            resume_lines = [line for line in resumed.stdout.splitlines() if line.strip().startswith("{")]
            resume_record = json.loads(resume_lines[-1]) if resume_lines else None
            task_state = sql_json(
                f"SELECT json_build_object('state',state,'revision',revision)::text FROM tasks WHERE task_id='{task_id}'"
            )
            resume_records.append({"round": resume_round, "process_exit": resumed.returncode,
                                   "result": resume_record, "task_state": task_state})
            if task_state and task_state["state"] in {"COMPLETED", "FAILED"}:
                break
        operator_closed = False
        if task_state and task_state["state"] == "WAITING":
            current_effects = effects(task_id)
            if any(effect["state"] not in {"CONFIRMED", "CANCELLED"} for effect in current_effects):
                raise RuntimeError(f"Unresolved effects on waiting task; inspect before closure: {current_effects}")
            close_waiting_task(task_id)
            operator_closed = True
        after = snapshot()
        final_task = sql_json(
            "SELECT json_build_object('task_id',task_id,'state',state,'revision',revision,"
            f"'checkpoint',checkpoint)::text FROM tasks WHERE task_id='{task_id}'"
        )
        task_effects = effects(task_id)
        record = {"candidate": args.candidate, "trial": trial, "valid": bool(interrupted),
                  "task_id": task_id, "checkpoint_observed": saved,
                  "candidate_api_killed": interrupted,
                  "state_after_interruption": state_after_interrupt,
                  "prepare_exit": initial.returncode, "prepare_stdout": stdout[-4000:],
                  "prepare_stderr": stderr[-4000:], "resume_attempts": resume_records,
                  "operator_closed_waiting_task": operator_closed,
                  "final_task": final_task, "effects": task_effects,
                  "before": before, "after": after}

    with output_path.open("a", encoding="utf-8") as destination:
        destination.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"candidate": args.candidate, "trial": trial,
                      "valid": record.get("valid"),
                      "task_id": record.get("task_id") or (record.get("task") or {}).get("task_id"),
                      "state": (record.get("final_task") or record.get("task") or {}).get("state"),
                      "test_exit": (record.get("after") or {}).get("test_exit")}), flush=True)

    if saved:
        if not record["valid"]:
            raise RuntimeError("Candidate API interruption was not confirmed")
        final = record["final_task"]
        if final["state"] not in {"COMPLETED", "FAILED"}:
            raise RuntimeError(f"Task is not terminal; inspect before reset: {record}")
        if any(effect["state"] not in {"CONFIRMED", "CANCELLED"} for effect in record["effects"]):
            raise RuntimeError(f"Unresolved effects; inspect before reset: {record}")
        # Do not reset unless all workspace effects are terminal and inspectable.
        compose("exec", "-T", "-e", "WORKSPACE_RESET=1", "workspace-amber",
                "python", "/app/workspace_runner.py")
        clean = snapshot()
        if clean["root"] != clean["head"] or clean["status"].strip():
            raise RuntimeError(f"Synthetic workspace cleanup failed: {clean}")
    elif record.get("task") and record["task"]["state"] in {"COMPLETED", "FAILED"}:
        if any(effect["state"] not in {"CONFIRMED", "CANCELLED"} for effect in record["effects"]):
            raise RuntimeError(f"Unresolved effects; inspect before reset: {record}")
        if record["after"]["status"].strip():
            raise RuntimeError(f"Workspace changed during checkpoint preparation; inspect before reset: {record}")
        compose("exec", "-T", "-e", "WORKSPACE_RESET=1", "workspace-amber",
                "python", "/app/workspace_runner.py")


if __name__ == "__main__":
    main()
