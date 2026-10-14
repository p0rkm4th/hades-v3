"""Independently verify DBOS recovery in HADES task, grant, ledger, and target state."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


STATE = Path(os.environ.get("CP79_STATE_DIR", "/state"))
BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080").rstrip("/")
TOKEN = os.environ.get("HADES_USER_TOKEN", "fixture-token-amber")
RESPONSE = "The approved synthetic appointment is confirmed."


def request(method: str, path: str, body: dict | None = None, *, orchestrator: bool = False):
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    if orchestrator:
        headers["X-Hades-Orchestrator"] = os.environ["ORCHESTRATOR_SECRET"]
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read())
        except json.JSONDecodeError:
            return error.code, {}


def verify_fixture(scenario: dict, workflow_result: dict, db_url: str) -> dict:
    expected_digest = hashlib.sha256(json.dumps(
        {"target_id": scenario["target_id"], "details": scenario["details"]},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    with psycopg.connect(db_url, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT task_id,user_id,domain_id,state,checkpoint FROM tasks WHERE task_id=%s",
            (scenario["task_id"],),
        )
        task = cur.fetchone()
        cur.execute(
            "SELECT effect_id,task_id,user_id,domain_id,effect_kind,resource_key,state,request "
            "FROM effects WHERE task_id=%s ORDER BY created_at",
            (scenario["task_id"],),
        )
        effects = cur.fetchall()
        cur.execute(
            "SELECT approval_id,task_id,user_id,domain_id,target_id,effect_digest,consumed_at,expires_at "
            "FROM commitment_approvals WHERE approval_id=%s",
            (scenario["approval_id"],),
        )
        approval = cur.fetchone()
        cur.execute(
            "SELECT target_id,behavior,accepted_effect_id,receive_count "
            "FROM commitment_targets WHERE target_id=%s",
            (scenario["target_id"],),
        )
        target = cur.fetchone()
    if task is None or approval is None or target is None or len(effects) != 1:
        raise AssertionError("independent task/effect/approval/target cardinality check failed")
    effect = effects[0]
    identity = (str(task["task_id"]) == scenario["task_id"]
                and task["user_id"] == "user-amber"
                and task["domain_id"] == approval["domain_id"])
    linked = (str(effect["effect_id"]) == workflow_result["effect_id"]
              and str(effect["task_id"]) == scenario["task_id"]
              and effect["user_id"] == task["user_id"]
              and effect["domain_id"] == task["domain_id"]
              and effect["effect_kind"] == "EXTERNAL_COMMITMENT"
              and effect["resource_key"] == f"commitment:{scenario['target_id']}"
              and effect["request"].get("details") == scenario["details"]
              and effect["request"].get("approval_id") == scenario["approval_id"]
              and effect["request"].get("effect_digest") == expected_digest
              and effect["state"] == "CONFIRMED")
    grant = (str(approval["task_id"]) == scenario["task_id"]
             and approval["user_id"] == task["user_id"]
             and approval["domain_id"] == task["domain_id"]
             and approval["target_id"] == scenario["target_id"]
             and approval["effect_digest"] == expected_digest
             and approval["consumed_at"] is not None
             and approval["consumed_at"] <= approval["expires_at"])
    canonical = (target["behavior"] == scenario["behavior"]
                 and str(target["accepted_effect_id"]) == workflow_result["effect_id"]
                 and target["receive_count"] == 1)
    if not (identity and linked and grant and canonical
            and workflow_result["task_id"] == scenario["task_id"]
            and workflow_result["state"] == "CONFIRMED"):
        raise AssertionError("independent pre-finalization evidence check failed")

    proof = {
        "task_type": "EFFECTFUL", "response_nonempty": True,
        "completion_claim": False, "tool_evidence": [], "response": RESPONSE,
        "provider_error": None,
    }
    status, completed = request("POST", f"/v1/tasks/{scenario['task_id']}/checkpoint", {
        "state": "COMPLETED",
        "checkpoint": {
            "summary": "The approved commitment was independently verified.",
            "completed": ["the bounded approved appointment operation"],
            "pending": [],
        },
        "_orchestrator_finalization": proof,
    }, orchestrator=True)
    if status != 200 or completed.get("state") != "COMPLETED":
        raise AssertionError("trusted gateway finalization rejected verified completion")
    status, persisted = request("GET", f"/v1/tasks/{scenario['task_id']}")
    if (status != 200 or persisted.get("state") != "COMPLETED"
            or persisted.get("checkpoint", {}).get("final_response") != RESPONSE
            or persisted.get("checkpoint", {}).get("response_delivery") != "PERSISTED_PENDING_DELIVERY"):
        raise AssertionError("durable task or response finalization did not persist")
    return {
        "case": scenario["case"], "task_id": scenario["task_id"],
        "effect_id": workflow_result["effect_id"], "task_state": persisted["state"],
        "effect_state": effect["state"], "approval_identity": "verified",
        "canonical_receive_count": target["receive_count"],
        "trusted_response_persisted": True,
    }


def main() -> None:
    scenarios = json.loads((STATE / "fixtures.json").read_text(encoding="utf-8"))
    outcomes = json.loads((STATE / "dbos-results.json").read_text(encoding="utf-8"))
    by_case = {item["case"]: item for item in outcomes}
    if len(by_case) != len(scenarios):
        raise AssertionError("DBOS output does not cover every setup case")
    verified = [verify_fixture(item, by_case[item["case"]], os.environ["DATABASE_URL"])
                for item in scenarios]
    print(json.dumps({
        "evidence": "CONTRACT_TEST", "cases": len(verified),
        "all_tasks_completed_by_trusted_gateway": True,
        "canonical_receives_per_task": [item["canonical_receive_count"] for item in verified],
        "all_original_task_and_effect_ids_preserved": True,
        "no_duplicate_dispatch_or_unrelated_effects": True,
        "results": verified,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
