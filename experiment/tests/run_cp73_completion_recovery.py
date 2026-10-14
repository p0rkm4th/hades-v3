"""Matched A/C recovery trial with a trusted bounded task contract."""

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
    rows = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(rows[-1]) if rows else None


def create_task(target_id):
    script = '''import json,os,sys,urllib.request
target=sys.argv[1]; details=sys.argv[2]
body={"goal":"Reserve exactly the approved synthetic appointment slot.","completion_contract":{"version":1,"kind":"external_commitment_set","required":[{"effect_kind":"EXTERNAL_COMMITMENT","target_id":target,"details":details}]}}
req=urllib.request.Request("http://tool-gateway:8080/v1/tasks",data=json.dumps(body).encode(),headers={"Authorization":"Bearer fixture-token-amber","X-Hades-Orchestrator":os.environ["ORCHESTRATOR_SECRET"],"Content-Type":"application/json"},method="POST")
with urllib.request.urlopen(req,timeout=10) as r: print(json.dumps(json.load(r)))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script,
                     target_id, DETAILS)
    return json.loads(result.stdout.strip().splitlines()[-1])


def issue_approval(task_id, target_id):
    result = compose("--profile", "fixture-admin", "run", "-T", "--rm", "fixture-admin",
                     "approve", "--user", "user-amber", "--task", task_id,
                     "--target", target_id, "--details", DETAILS, "--ttl-seconds", "600")
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("task_id") != task_id or value.get("target_id") != target_id:
        raise RuntimeError("synthetic approval identity mismatch")
    return value


def candidate_attempt(candidate, task_id, target_id, approval_id, timeout=900):
    return compose("--profile", "harness", "run", "-T", "--rm", "--no-deps", "test-runner",
                   "python", "/app/tests/family8_ack_loss_attempt.py",
                   "--candidate", candidate, "--task-id", task_id,
                   "--target-id", target_id, "--approval-id", approval_id,
                   "--details", DETAILS, "--prompt", PROMPT,
                   timeout=timeout, check=False)


def parse_attempt(result):
    lines = [line for line in result.stdout.splitlines() if line.lstrip().startswith("{")]
    if not lines:
        return {"exit_code": result.returncode, "failure_class": "candidate_request_interrupted_or_failed"}
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"exit_code": result.returncode, "failure_class": "invalid_candidate_result"}
    return value


def target_record(target_id):
    safe = target_id.replace("'", "''")
    return sql_json(
        "SELECT json_build_object('target_id',target_id,'accepted_effect_id',accepted_effect_id,"
        f"'receive_count',receive_count,'revision',revision)::text FROM commitment_targets WHERE target_id='{safe}'"
    )


def task_and_effect_records(task_id):
    safe = task_id.replace("'", "''")
    task = sql_json(
        "SELECT json_build_object('task_id',task_id,'user_id',user_id,'domain_id',domain_id,"
        "'state',state,'checkpoint',checkpoint)::text FROM tasks "
        f"WHERE task_id='{safe}'"
    )
    effects = sql_json(
        "SELECT coalesce(json_agg(json_build_object('effect_id',effect_id,'task_id',task_id,"
        "'user_id',user_id,'domain_id',domain_id,'effect_kind',effect_kind,'resource_key',resource_key,"
        f"'state',state,'request',request,'result',result) ORDER BY created_at),'[]'::json)::text FROM effects WHERE task_id='{safe}'"
    ) or []
    return task, effects


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
    parser.add_argument("--repetition", type=int, choices=range(1, 4), required=True)
    parser.add_argument("--output", default="experiment/results/cp73_completion_recovery.jsonl")
    args = parser.parse_args()
    label = f"cp73-{args.candidate}-{args.repetition}"
    target_id = f"{label}-target"
    if target_record(target_id) is not None:
        raise SystemExit("refusing to reuse a one-shot target")
    compose("exec", "-T", "postgres", "psql", "-U", "fixture_writer", "-d", "hades_lab",
            "-v", "ON_ERROR_STOP=1", "-c",
            f"INSERT INTO commitment_targets (target_id,behavior) VALUES ('{target_id}','ACCEPT_ACK_LOST_DELAYED')")
    task = create_task(target_id)
    task_id = task["task_id"]
    approval = issue_approval(task_id, target_id)

    initial_process = subprocess.Popen(
        COMPOSE + ["--profile", "harness", "run", "-T", "--rm", "--no-deps", "test-runner",
                   "python", "/app/tests/family8_ack_loss_attempt.py", "--candidate", args.candidate,
                   "--task-id", task_id, "--target-id", target_id,
                   "--approval-id", approval["approval_id"], "--details", DETAILS,
                   "--prompt", PROMPT], cwd=ROOT, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    deadline = time.monotonic() + 600
    dispatch_seen = False
    while time.monotonic() < deadline and initial_process.poll() is None:
        current_target = target_record(target_id)
        if current_target and current_target["receive_count"] == 1:
            dispatch_seen = True
            compose("kill", "-s", "SIGKILL", "candidate-api", "tool-gateway")
            break
        time.sleep(0.1)
    try:
        initial_stdout, initial_stderr = initial_process.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        initial_process.kill()
        initial_stdout, initial_stderr = initial_process.communicate()
    initial = parse_attempt(subprocess.CompletedProcess([], initial_process.returncode,
                                                         initial_stdout, initial_stderr))
    if dispatch_seen:
        compose("up", "-d", "tool-gateway", "candidate-api", timeout=180)
    effect_rows = task_and_effect_records(task_id)[1]
    effect_ids = [row["effect_id"] for row in effect_rows]
    reconciliation = reconcile(effect_ids[0]) if dispatch_seen and effect_ids else None
    if reconciliation and reconciliation["status"] != 200:
        raise RuntimeError("canonical acceptance reconciliation did not succeed")

    # CP73's second restart boundary: reconciliation is durable, but the API
    # dies before producing/persisting a final user response.
    if dispatch_seen:
        compose("kill", "-s", "SIGKILL", "candidate-api")
        compose("up", "-d", "candidate-api", timeout=120)
    resumed = candidate_attempt(args.candidate, task_id, target_id, approval["approval_id"])
    resumed_result = parse_attempt(resumed)
    final_task, final_effects = task_and_effect_records(task_id)
    for effect in final_effects:
        request = effect.get("request") or {}
        if "approval_id" in request:
            request["approval_id"] = "[REDACTED_SYNTHETIC_APPROVAL_ID]"
    final_target = target_record(target_id)
    row = {
        "candidate": args.candidate, "repetition": args.repetition,
        "source_parent": "39309dca28aca89ba08ab0184aab111865361dcd",
        "task_id": task_id, "target_id": target_id,
        "interruption_points": ["dispatch_before_ack", "after_reconciliation_before_final_response"],
        "dispatch_seen": dispatch_seen, "initial_turn": initial,
        "operator_reconciliation": reconciliation,
        "resumed_turn": resumed_result, "final_task": final_task,
        "final_effects": final_effects, "final_target": final_target,
        "expected_details": DETAILS, "approval_id_withheld": True,
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    passed = (
        dispatch_seen and final_task and final_task["state"] == "COMPLETED"
        and len(final_effects) == 1 and final_effects[0]["state"] == "CONFIRMED"
        and final_target and final_target["receive_count"] == 1
        and final_task["checkpoint"].get("response_delivery") == "PERSISTED_PENDING_DELIVERY"
        and bool(final_task["checkpoint"].get("final_response"))
    )
    print(json.dumps({"candidate": args.candidate, "repetition": args.repetition,
                      "task_id": task_id, "task_state": final_task.get("state") if final_task else None,
                      "effect_count": len(final_effects),
                      "receive_count": final_target.get("receive_count") if final_target else None,
                      "final_response_persisted": bool(final_task and final_task["checkpoint"].get("final_response")),
                      "passed": passed}), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
