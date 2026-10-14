"""Minimal DBOS crash-replay probe with an idempotent external-effect stand-in.

This is a contract probe, not a HADES gateway integration or qualification.
Run with DBOS 3.2.0 installed; state is isolated in a temporary directory.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from dbos import DBOS, SetWorkflowID


TASK_ID = "cp77-probe-task"
EFFECT_ID = "cp77-probe-effect"
WORKFLOW_ID = "cp77-probe-workflow"
APP_NAME = "hades_cp77_dbos_probe"
APP_VERSION = "probe-1"


def _connect(path: str) -> sqlite3.Connection:
    return sqlite3.connect(path, timeout=10)


def _child(phase: str, state_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if phase == "crash":
        env["CP77_CRASH_AFTER_EFFECT"] = "1"
    else:
        env.pop("CP77_CRASH_AFTER_EFFECT", None)
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", phase,
         "--state-dir", str(state_dir)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _child_main(phase: str, state_dir: Path) -> int:
    state_dir.mkdir(parents=True, exist_ok=True)
    system_db = state_dir / "dbos.sqlite"
    canonical_db = state_dir / "canonical.sqlite"
    DBOS(config={
        "name": APP_NAME,
        "application_version": APP_VERSION,
        "system_database_url": f"sqlite:///{system_db}",
    })

    @DBOS.step()
    def dispatch(task_id: str, effect_id: str) -> dict[str, str]:
        with _connect(str(canonical_db)) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS attempts "
                "(effect_id TEXT NOT NULL, attempt INTEGER PRIMARY KEY AUTOINCREMENT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS canonical_effects "
                "(effect_id TEXT PRIMARY KEY, task_id TEXT NOT NULL)"
            )
            db.execute("INSERT INTO attempts(effect_id) VALUES (?)", (effect_id,))
            db.execute(
                "INSERT OR IGNORE INTO canonical_effects(effect_id,task_id) VALUES (?,?)",
                (effect_id, task_id),
            )
        if phase == "crash" and os.environ.get("CP77_CRASH_AFTER_EFFECT") == "1":
            # Simulate process death after the target accepted the operation,
            # before DBOS recorded the step result.
            os._exit(73)
        return {"task_id": task_id, "effect_id": effect_id, "state": "accepted"}

    @DBOS.workflow()
    def effect_workflow(task_id: str, effect_id: str) -> dict[str, str]:
        return dispatch(task_id, effect_id)

    DBOS.launch()
    if phase == "crash":
        with SetWorkflowID(WORKFLOW_ID):
            effect_workflow(TASK_ID, EFFECT_ID)
        return 0

    result = DBOS.get_result(WORKFLOW_ID)
    print(json.dumps({"result": result}), flush=True)
    DBOS.destroy()
    return 0


def run_probe() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="hades-cp77-dbos-") as temp:
        state_dir = Path(temp)
        crashed = _child("crash", state_dir)
        if crashed.returncode != 73:
            raise RuntimeError(
                f"expected simulated process exit 73; got {crashed.returncode}; "
                f"{crashed.stderr[-1500:]}"
            )
        resumed = _child("resume", state_dir)
        if resumed.returncode != 0:
            raise RuntimeError(f"resume failed: {resumed.stderr[-2000:]}")
        output = json.loads(resumed.stdout.strip().splitlines()[-1])
        with _connect(str(state_dir / "canonical.sqlite")) as db:
            attempts = db.execute(
                "SELECT count(*) FROM attempts WHERE effect_id=?", (EFFECT_ID,)
            ).fetchone()[0]
            canonical = db.execute(
                "SELECT task_id,effect_id FROM canonical_effects WHERE effect_id=?",
                (EFFECT_ID,),
            ).fetchall()
        passed = (
            output.get("result") == {
                "task_id": TASK_ID, "effect_id": EFFECT_ID, "state": "accepted"
            }
            and attempts == 2
            and canonical == [(TASK_ID, EFFECT_ID)]
        )
        result = {
            "dbos_version": "3.2.0",
            "python_version": sys.version.split()[0],
            "interruption": "after external acceptance, before step checkpoint",
            "workflow_identity_preserved": output.get("result", {}).get("task_id") == TASK_ID,
            "step_attempts": attempts,
            "canonical_effect_rows": len(canonical),
            "canonical_effect_identity_preserved": canonical == [(TASK_ID, EFFECT_ID)],
            "passed": passed,
        }
        if not passed:
            raise AssertionError(json.dumps(result, sort_keys=True))
        return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--child", choices=("crash", "resume"))
    parser.add_argument("--state-dir", type=Path)
    arguments = parser.parse_args()
    if arguments.child:
        if arguments.state_dir is None:
            parser.error("--state-dir is required with --child")
        raise SystemExit(_child_main(arguments.child, arguments.state_dir))
    print(json.dumps(run_probe(), sort_keys=True))
