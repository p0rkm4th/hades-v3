"""Interrupt one protected commitment after simulator acceptance and resume safely."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

from compose_scope import compose_command

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = compose_command("experiment/compose.yaml")
DETAILS = "Reserve the synthetic appointment slot for Amber at 16:00"
PROMPT = "Please reserve the appointment slot for tomorrow at 16:00."


def compose(*args, timeout=120, check=True):
    return subprocess.run(COMPOSE + list(args), cwd=ROOT, capture_output=True,
                          text=True, timeout=timeout, check=check)


def sql_json(query):
    result = compose("exec", "-T", "postgres", "psql", "-U", "fixture_writer",
                     "-d", "hades_lab", "-Atc", query)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else None


def task_record(task_id):
    safe = task_id.replace("'", "''")
    task = sql_json(
        "SELECT json_build_object('task_id',task_id,'state',state,'checkpoint',checkpoint,'revision',revision)::text "
        f"FROM tasks WHERE task_id='{safe}'"
    )
    effects = sql_json(
        "SELECT coalesce(json_agg(json_build_object('effect_id',effect_id,'state',state,'kind',effect_kind) "
        "ORDER BY created_at),'[]'::json)::text "
        f"FROM effects WHERE task_id='{safe}'"
    ) or []
    return {"task": task, "effects": effects}


def target_record(target_id):
    safe = target_id.replace("'", "''")
    return sql_json(
        "SELECT json_build_object('target_id',target_id,'accepted_effect_id',accepted_effect_id,"
        f"'receive_count',receive_count,'revision',revision)::text FROM commitment_targets WHERE target_id='{safe}'"
    )


def start_task(goal):
    script = '''import json,sys,urllib.request
body=json.dumps({"goal":sys.argv[1]}).encode()
req=urllib.request.Request("http://tool-gateway:8080/v1/tasks",data=body,headers={"Authorization":"Bearer fixture-token-amber","Content-Type":"application/json"},method="POST")
with urllib.request.urlopen(req,timeout=10) as r: print(json.dumps(json.load(r)))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script, goal)
    return json.loads(result.stdout.strip().splitlines()[-1])


def issue_approval(task_id, target_id):
    result = compose(
        "--profile", "fixture-admin", "run", "-T", "--rm", "fixture-admin",
        "approve", "--user", "user-amber", "--task", task_id, "--target", target_id,
        "--details", DETAILS, "--ttl-seconds", "600", timeout=60,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def run_attempt(candidate, task_id, target_id, approval_id, phase, timeout=960):
    return compose(
        "run", "-T", "--rm", "--no-deps", "test-runner", "python",
        "/app/tests/family8_ack_loss_attempt.py", "--candidate", candidate,
        "--task-id", task_id, "--target-id", target_id,
        "--approval-id", approval_id, "--details", DETAILS,
        "--prompt", PROMPT, timeout=timeout, check=False,
    )


def parse_attempt(result):
    lines = [line for line in result.stdout.splitlines() if line.lstrip().startswith("{")]
    if not lines:
        return {"exit_code": result.returncode, "failure": result.stderr[-1000:]}
    value = json.loads(lines[-1])
    if value.get("text"):
        value["text"] = value["text"].replace("[REDACTED]", "")
    return value


def reconcile(effect_id):
    script = r'''import json,sys,urllib.request,urllib.error
req=urllib.request.Request("http://tool-gateway:8080/v1/commitments/"+sys.argv[1]+"/reconcile",data=b"{}",headers={"Authorization":"Bearer fixture-token-amber","Content-Type":"application/json"},method="POST")
try:
 with urllib.request.urlopen(req,timeout=10) as r: print(json.dumps({"status":r.status,"body":json.load(r)}))
except urllib.error.HTTPError as e: print(json.dumps({"status":e.code,"body":json.load(e)}))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script, effect_id)
    return json.loads(result.stdout.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("pydantic", "lean"), required=True)
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--output", default="experiment/results/cp72_restart_recovery.jsonl")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,24}", args.run_label):
        parser.error("run label must be 1-24 lowercase letters, digits, or hyphens")

    target_id = f"cp72-crash-{args.run_label}-{args.candidate}"
    if target_record(target_id) is not None:
        raise SystemExit("refusing to reuse a one-shot target")
    compose("exec", "-T", "postgres", "psql", "-U", "fixture_writer", "-d", "hades_lab",
            "-v", "ON_ERROR_STOP=1", "-c",
            f"INSERT INTO commitment_targets (target_id,behavior) VALUES ('{target_id}','ACCEPT_ACK_LOST_DELAYED')")
    task_id = start_task(f"[CP72 restart {args.run_label} {args.candidate}] {PROMPT}")["task_id"]
    approval = issue_approval(task_id, target_id)

    command = COMPOSE + [
        "run", "-T", "--rm", "--no-deps", "test-runner", "python",
        "/app/tests/family8_ack_loss_attempt.py", "--candidate", args.candidate,
        "--task-id", task_id, "--target-id", target_id,
        "--approval-id", approval["approval_id"], "--details", DETAILS,
        "--prompt", PROMPT,
    ]
    initial = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 600
    dispatch_observed = False
    while time.monotonic() < deadline and initial.poll() is None:
        current = target_record(target_id)
        if current and current["receive_count"] == 1:
            dispatch_observed = True
            # Interrupt both caller and gateway while the simulator has committed
            # but is withholding its acknowledgement. Both services are scoped to
            # this unique CP72 project.
            compose("kill", "-s", "SIGKILL", "candidate-api", "tool-gateway")
            break
        time.sleep(0.1)

    try:
        stdout, stderr = initial.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        initial.kill()
        stdout, stderr = initial.communicate()
    initial_result = parse_attempt(subprocess.CompletedProcess(command, initial.returncode,
                                                                 stdout, stderr))

    if dispatch_observed:
        compose("up", "-d", "tool-gateway", "candidate-api", timeout=180)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            probe = compose("exec", "-T", "candidate-api", "python", "-c",
                            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2)",
                            check=False)
            if probe.returncode == 0:
                break
            time.sleep(0.5)

    after_restart = task_record(task_id)
    effect_ids = [effect["effect_id"] for effect in after_restart["effects"]]
    reconciliation = reconcile(effect_ids[0]) if dispatch_observed and effect_ids else None
    after_reconcile = task_record(task_id)
    target_after_reconcile = target_record(target_id)

    resume_results = []
    # Retry the same canonical task at most twice after recovery. The original
    # consumed approval remains fixed, so a candidate cannot dispatch a second
    # accepted operation by replaying the same request.
    for resume_no in range(1, 3):
        task = after_reconcile["task"] or {}
        if task.get("state") in {"COMPLETED", "FAILED"}:
            break
        result = run_attempt(args.candidate, task_id, target_id, approval["approval_id"],
                             f"resume-{resume_no}")
        response = parse_attempt(result)
        resume_results.append(response)
        after_reconcile = task_record(task_id)

    final = task_record(task_id)
    final_target = target_record(target_id)
    row = {
        "candidate": args.candidate, "run_label": args.run_label,
        "task_id": task_id, "target_id": target_id,
        "prompt": PROMPT, "details": DETAILS,
        "interruption": "candidate-api-and-gateway-killed-after-canonical-accept-before-ack",
        "dispatch_observed": dispatch_observed,
        "initial_response": initial_result,
        "task_after_restart": after_restart["task"],
        "effects_after_restart": after_restart["effects"],
        "operator_reconciliation": reconciliation,
        "task_after_reconciliation": after_reconcile["task"],
        "target_after_reconciliation": target_after_reconcile,
        "resume_results": resume_results,
        "final_task": final["task"], "final_effects": final["effects"],
        "final_target": final_target,
        "approval_id_withheld": bool(approval.get("approval_id")),
    }
    for response in [row["initial_response"], *resume_results]:
        if isinstance(response, dict) and response.get("text"):
            response["text"] = response["text"].replace(approval["approval_id"], "[REDACTED_SYNTHETIC_APPROVAL_ID]")
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({
        "candidate": args.candidate, "task_id": task_id,
        "dispatch_observed": dispatch_observed,
        "task_state": (final["task"] or {}).get("state"),
        "effect_count": len(final["effects"]),
        "effect_states": [effect["state"] for effect in final["effects"]],
        "target_receive_count": (final_target or {}).get("receive_count"),
        "resume_attempts": len(resume_results),
    }), flush=True)
    if not dispatch_observed:
        raise SystemExit("candidate did not reach the bounded dispatch interruption point")
    if len(final["effects"]) != 1 or (final_target or {}).get("receive_count") != 1:
        raise SystemExit("independent no-duplicate invariant failed")


if __name__ == "__main__":
    main()
