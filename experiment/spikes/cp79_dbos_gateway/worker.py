"""Replay DBOS steps through the authenticated HADES commitment API."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dbos import DBOS, SetWorkflowID


STATE = Path(os.environ.get("CP79_STATE_DIR", "/state"))
BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080").rstrip("/")
TOKEN = os.environ.get("HADES_USER_TOKEN", "fixture-token-amber")
APP_NAME = "hades_cp79_durable_gateway_probe"
APP_VERSION = "1"


def request(method: str, path: str, body: dict):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=20) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read())
        except json.JSONDecodeError:
            return error.code, {}


def _record_attempt(workflow_id: str) -> int:
    directory = STATE / "attempts"
    directory.mkdir(exist_ok=True)
    path = directory / f"{workflow_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        value = {"attempts": 0}
    value["attempts"] += 1
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value), encoding="utf-8")
    temp.replace(path)
    return value["attempts"]


def _child(mode: str, scenario: dict) -> int:
    system_db = STATE / "dbos.sqlite"
    DBOS(config={
        "name": APP_NAME,
        "application_version": APP_VERSION,
        "system_database_url": f"sqlite:///{system_db}",
    })

    @DBOS.step()
    def submit(task_id: str, target_id: str, details: str, approval_id: str,
               workflow_id: str, case: int) -> dict:
        attempt = _record_attempt(workflow_id)
        status, body = request("POST", "/v1/commitments", {
            "task_id": task_id, "target_id": target_id,
            "details": details, "approval_id": approval_id,
        })
        if status not in (200, 202):
            raise RuntimeError(f"HADES rejected approved trial request (HTTP {status})")
        result = {
            "task_id": str(body.get("task_id", "")),
            "effect_id": str(body.get("effect_id", "")),
            "state": str(body.get("state", "")),
            "attempt": attempt,
        }
        if mode == "crash" and os.environ.get("CP79_CRASH_AFTER_RESPONSE") == workflow_id:
            crash_record = STATE / f"crash-{case}.json"
            crash_record.write_text(json.dumps({
                "task_id": result["task_id"], "effect_id": result["effect_id"],
                "state": result["state"],
            }), encoding="utf-8")
            os._exit(73)  # Target and gateway have responded; DBOS step has not returned.
        if result["task_id"] != task_id or not result["effect_id"]:
            raise RuntimeError("HADES response lost its task/effect identity")
        return result

    @DBOS.step()
    def reconcile(task_id: str, effect_id: str, state: str) -> dict:
        if state == "CONFIRMED":
            return {"task_id": task_id, "effect_id": effect_id, "state": state}
        status, body = request("POST", f"/v1/commitments/{effect_id}/reconcile", {})
        if status != 200 or body.get("state") != "CONFIRMED":
            raise RuntimeError(f"HADES reconciliation not confirmed (HTTP {status})")
        return {"task_id": task_id, "effect_id": effect_id, "state": body["state"]}

    @DBOS.workflow()
    def commitment_workflow(task_id: str, target_id: str, details: str,
                            approval_id: str, workflow_id: str, case: int) -> dict:
        submitted = submit(task_id, target_id, details, approval_id, workflow_id, case)
        final = reconcile(submitted["task_id"], submitted["effect_id"], submitted["state"])
        return {"task_id": task_id, "effect_id": final["effect_id"], "state": final["state"]}

    DBOS.launch()
    workflow_id = scenario["workflow_id"]
    if mode == "crash":
        with SetWorkflowID(workflow_id):
            commitment_workflow(
                scenario["task_id"], scenario["target_id"], scenario["details"],
                scenario["approval_id"], workflow_id, scenario["case"],
            )
        raise RuntimeError("fault injection failed to stop the first DBOS step")
    result = DBOS.get_result(workflow_id)
    print("CP79_RESULT:" + json.dumps(result, sort_keys=True), flush=True)
    DBOS.destroy()
    return 0


def _run_child(mode: str, scenario: dict) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if mode == "crash":
        env["CP79_CRASH_AFTER_RESPONSE"] = scenario["workflow_id"]
    else:
        env.pop("CP79_CRASH_AFTER_RESPONSE", None)
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", mode,
         "--scenario", json.dumps(scenario, sort_keys=True)],
        env=env, capture_output=True, text=True, timeout=90, check=False,
    )


def run_probe() -> dict:
    scenarios = json.loads((STATE / "fixtures.json").read_text(encoding="utf-8"))
    outcomes = []
    for scenario in scenarios:
        crashed = _run_child("crash", scenario)
        if crashed.returncode != 73:
            diagnostic = crashed.stderr[-1400:].replace(TOKEN, "[redacted]")
            raise RuntimeError(
                f"case {scenario['case']} missed crash boundary "
                f"(exit {crashed.returncode}): {diagnostic}"
            )
        resumed = _run_child("resume", scenario)
        if resumed.returncode != 0:
            raise RuntimeError(f"case {scenario['case']} DBOS resume failed: {resumed.stderr[-1000:]}")
        marker = next((line[len("CP79_RESULT:"):] for line in resumed.stdout.splitlines()
                       if line.startswith("CP79_RESULT:")), None)
        if marker is None:
            raise RuntimeError(f"case {scenario['case']} produced no workflow result")
        result = json.loads(marker)
        crash_record = json.loads((STATE / f"crash-{scenario['case']}.json").read_text())
        attempts = json.loads((STATE / "attempts" / f"{scenario['workflow_id']}.json").read_text())
        if (result["task_id"] != scenario["task_id"]
                or result["effect_id"] != crash_record["effect_id"]
                or result["task_id"] != crash_record["task_id"]
                or result["state"] != "CONFIRMED"
                or attempts["attempts"] != 2):
            raise AssertionError(f"case {scenario['case']} failed identity/replay checks")
        outcomes.append({
            "case": scenario["case"], "behavior": scenario["behavior"],
            "task_id": result["task_id"], "effect_id": result["effect_id"],
            "state": result["state"], "step_attempts": attempts["attempts"],
            "same_effect_after_restart": True,
        })
    path = STATE / "dbos-results.json"
    path.write_text(json.dumps(outcomes, sort_keys=True), encoding="utf-8")
    print(json.dumps({"evidence": "CONTRACT_TEST", "dbos_version": "3.2.0",
                      "interrupted_cases": len(outcomes), "all_recovered": True,
                      "outcomes": outcomes}, sort_keys=True), flush=True)
    return {"passed": True, "cases": len(outcomes)}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--child", choices=("crash", "resume"))
    parser.add_argument("--scenario")
    args = parser.parse_args()
    if args.child:
        if not args.scenario:
            parser.error("--scenario required in child mode")
        raise SystemExit(_child(args.child, json.loads(args.scenario)))
    run_probe()


if __name__ == "__main__":
    main()
