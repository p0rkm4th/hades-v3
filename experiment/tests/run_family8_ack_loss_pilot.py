"""Run one matched A/C pilot with fresh one-shot synthetic ack-loss targets."""

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", "experiment/compose.yaml"]
DETAILS = "Reserve the synthetic appointment slot for Amber at 16:00"
PROMPT = "Please reserve the appointment slot for tomorrow at 16:00."
OUTPUT = Path("experiment/results/family8_ack_loss_pilot.jsonl")


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


def start_task(goal):
    script = '''import json,urllib.request
body=json.dumps({"goal":__import__("sys").argv[1]}).encode()
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
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("task_id") != task_id or value.get("target_id") != target_id:
        raise RuntimeError("fixture operator approval did not match requested task/target")
    return value


def task_record(task_id):
    safe = task_id.replace("'", "''")
    task = sql_json(
        "SELECT json_build_object('task_id',task_id,'state',state,'checkpoint',checkpoint)::text "
        f"FROM tasks WHERE task_id='{safe}'"
    )
    effects = sql_json(
        "SELECT coalesce(json_agg(json_build_object('effect_id',effect_id,'state',state,"
        "'kind',effect_kind,'resource',resource_key,'request',request,'result',result) "
        "ORDER BY created_at),'[]'::json)::text "
        f"FROM effects WHERE task_id='{safe}'"
    ) or []
    approvals = sql_json(
        "SELECT json_build_object('n',count(*)::int)::text "
        f"FROM commitment_approvals WHERE task_id='{safe}'"
    )
    return {"task": task, "effects": effects, "approval_count": approvals["n"]}


def target_record(target_id):
    safe = target_id.replace("'", "''")
    return sql_json(
        "SELECT json_build_object('target_id',target_id,'behavior',behavior,"
        "'accepted_effect_id',accepted_effect_id,'receive_count',receive_count,"
        "'revision',revision)::text FROM commitment_targets "
        f"WHERE target_id='{safe}'"
    )


def reconcile_as_operator(task_id, effect_id):
    # Reconciliation reads the protected simulator's canonical state and never replays.
    script = r'''import json,sys,urllib.request
req=urllib.request.Request("http://tool-gateway:8080/v1/commitments/"+sys.argv[1]+"/reconcile",data=b"{}",headers={"Authorization":"Bearer fixture-token-amber","Content-Type":"application/json"},method="POST")
try:
 with urllib.request.urlopen(req,timeout=10) as r: print(json.dumps({"status":r.status,"body":json.load(r)}))
except urllib.error.HTTPError as e: print(json.dumps({"status":e.code,"body":json.load(e)}))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script, effect_id)
    return json.loads(result.stdout.strip().splitlines()[-1])


def close_task_for_review(task_id):
    script = r'''import json,sys,urllib.request
base="http://tool-gateway:8080"; headers={"Authorization":"Bearer fixture-token-amber","Content-Type":"application/json"}; task=sys.argv[1]
req=urllib.request.Request(base+"/v1/tasks/"+task,headers={"Authorization":headers["Authorization"]})
with urllib.request.urlopen(req,timeout=10) as r: value=json.load(r)
if value.get("state") in {"RUNNING","WAITING"}:
 checkpoint=value.get("checkpoint") or {}; checkpoint.setdefault("summary","Operator closed family 8 disposable trial after outcome inspection"); checkpoint.setdefault("completed",[]); checkpoint.setdefault("pending",[]); checkpoint["operator_review_required"]=True; checkpoint["operator_closed_after_trial"]=True
 req=urllib.request.Request(base+"/v1/tasks/"+task+"/checkpoint",data=json.dumps({"state":"FAILED","checkpoint":checkpoint}).encode(),headers=headers,method="POST")
 with urllib.request.urlopen(req,timeout=10) as r: value=json.load(r)
print(json.dumps(value))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script, task_id)
    return json.loads(result.stdout.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", default="pydantic,lean")
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--run-label", default="pilot")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,24}", args.run_label):
        raise SystemExit("run label must be 1-24 lowercase letters, digits, or hyphens")
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    compose("build", "test-runner", timeout=300)

    for index, candidate in enumerate(args.order.split(","), start=1):
        if candidate not in {"pydantic", "lean"}:
            raise SystemExit(f"unsupported candidate: {candidate}")
        target_id = f"cp43-ack-loss-{args.run_label}-{candidate}"
        if not re.fullmatch(r"[a-z0-9-]{1,80}", target_id):
            raise RuntimeError("invalid synthetic target identifier")
        if target_record(target_id) is not None:
            raise RuntimeError(f"refusing to reuse one-shot target {target_id}")
        compose(
            "exec", "-T", "postgres", "psql", "-U", "fixture_writer", "-d", "hades_lab",
            "-v", "ON_ERROR_STOP=1", "-c",
            f"INSERT INTO commitment_targets (target_id,behavior) VALUES ('{target_id}','ACCEPT_ACK_LOST')",
        )
        before = target_record(target_id)
        goal = f"[FAMILY8 {args.run_label} {candidate} attempt] {PROMPT}"
        task_id = start_task(goal)["task_id"]
        approval = issue_approval(task_id, target_id)
        if not approval.get("approval_id"):
            raise RuntimeError("operator did not issue a synthetic approval")
        result = compose(
            "run", "-T", "--rm", "--no-deps", "test-runner", "python",
            "/app/tests/family8_ack_loss_attempt.py", "--candidate", candidate,
            "--task-id", task_id, "--target-id", target_id,
            "--approval-id", approval["approval_id"], "--details", DETAILS,
            "--prompt", PROMPT, timeout=960, check=False,
        )
        lines = [line for line in result.stdout.splitlines() if line.lstrip().startswith("{")]
        attempt = json.loads(lines[-1]) if lines else {
            "candidate": candidate,
            "failure": {"exit_code": result.returncode, "stderr": result.stderr[-2000:]},
        }
        record = task_record(task_id)
        record_after_candidate = record
        current_target = target_record(target_id)
        target_after_candidate = current_target
        cleanup_reconciliation = None
        quarantined = [e for e in record["effects"] if e["state"] in {"QUARANTINED", "UNRESOLVED", "DISPATCHED"}]
        if quarantined:
            cleanup_reconciliation = reconcile_as_operator(task_id, quarantined[0]["effect_id"])
            record = task_record(task_id)
            current_target = target_record(target_id)
        task_after_candidate = record_after_candidate["task"]
        operator_closed_task = None
        if (record.get("task") or {}).get("state") in {"RUNNING", "WAITING"}:
            operator_closed_task = close_task_for_review(task_id)
            record = task_record(task_id)
        row = {
            "candidate": candidate,
            "attempt_order": index,
            "task_id": task_id,
            "target_id": target_id,
            "operator_approval": {k: v for k, v in approval.items() if k != "approval_id"},
            "approval_id_withheld_from_record": bool(approval.get("approval_id")),
            "prompt": PROMPT,
            "details": DETAILS,
            "attempt": attempt,
            "target_before": before,
            "target_after_candidate": target_after_candidate,
            "task_after_candidate": task_after_candidate,
            "effects_after_candidate": record_after_candidate["effects"],
            "target_final": current_target,
            "operator_cleanup_reconciliation": cleanup_reconciliation,
            "operator_closed_task": operator_closed_task,
            **record,
        }
        if attempt.get("text"):
            attempt["text"] = attempt["text"].replace(approval["approval_id"], "[REDACTED_SYNTHETIC_APPROVAL_ID]")
            row["attempt"] = attempt
        for effect_list in (row["effects"], row["effects_after_candidate"]):
            for effect in effect_list:
                request_body = effect.get("request")
                if isinstance(request_body, dict) and "approval_id" in request_body:
                    request_body["approval_id"] = "[REDACTED_SYNTHETIC_APPROVAL_ID]"
        with output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({
            "candidate": candidate, "task_id": task_id,
            "task_state": (record.get("task") or {}).get("state"),
            "tools": attempt.get("tool_calls", []),
            "effect_states": [e["state"] for e in record["effects"]],
            "target_receive_count": (current_target or {}).get("receive_count"),
            "candidate_text": attempt.get("text", "")[:240],
            "operator_cleanup_used": cleanup_reconciliation is not None,
        }), flush=True)


if __name__ == "__main__":
    main()
