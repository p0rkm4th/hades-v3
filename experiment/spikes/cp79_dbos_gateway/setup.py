"""Create disposable tasks, exact grants, and targets for the DBOS integration."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import psycopg


STATE = Path(os.environ.get("CP79_STATE_DIR", "/state"))
BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080").rstrip("/")
TOKEN = os.environ.get("HADES_USER_TOKEN", "fixture-token-amber")
DETAILS = "Reserve the synthetic appointment slot for Amber at 16:00"
CASES = ["ACCEPT_ACK_LOST"] * 3


def request(method: str, path: str, body: dict, *, orchestrator: bool = False):
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    if orchestrator:
        headers["X-Hades-Orchestrator"] = os.environ["ORCHESTRATOR_SECRET"]
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), headers=headers, method=method
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read())
        except json.JSONDecodeError:
            return error.code, {}


def main() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    digest_for = lambda target: hashlib.sha256(json.dumps(
        {"target_id": target, "details": DETAILS}, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    fixtures = []
    db_url = os.environ["DATABASE_URL"]
    for index, behavior in enumerate(CASES, start=1):
        target = f"cp79-{uuid.uuid4().hex[:20]}"
        contract = {"version": 1, "kind": "external_commitment_set", "required": [{
            "effect_kind": "EXTERNAL_COMMITMENT", "target_id": target, "details": DETAILS,
        }]}
        status, task = request("POST", "/v1/tasks", {
            "goal": "Complete the approved synthetic appointment operation and report its verified state.",
            "completion_contract": contract,
        }, orchestrator=True)
        if status != 201:
            raise RuntimeError(f"trusted task setup rejected (HTTP {status})")
        task_id = str(task["task_id"])
        digest = digest_for(target)
        with psycopg.connect(db_url) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO commitment_targets (target_id,behavior) VALUES (%s,%s)",
                (target, behavior),
            )
            cur.execute(
                "INSERT INTO commitment_approvals "
                "(user_id,domain_id,task_id,target_id,effect_digest,approved_by,expires_at) "
                "VALUES ('user-amber',%s,%s,%s,%s,'cp79-fixture',now()+interval '10 minutes') "
                "RETURNING approval_id",
                (task["domain_id"], task_id, target, digest),
            )
            approval_id = str(cur.fetchone()[0])
        fixtures.append({
            "case": index, "behavior": behavior, "task_id": task_id,
            "target_id": target, "details": DETAILS, "approval_id": approval_id,
            "workflow_id": f"cp79-{uuid.uuid4()}",
        })
    destination = STATE / "fixtures.json"
    temp = destination.with_suffix(".tmp")
    temp.write_text(json.dumps(fixtures, sort_keys=True), encoding="utf-8")
    temp.replace(destination)
    print(json.dumps({
        "evidence": "CONTRACT_TEST_SETUP", "cases": len(fixtures),
        "all_tasks_have_trusted_completion_criteria": True,
        "all_effects_have_exact_fixture_approvals": True,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
