"""Check current Pydantic DBOSDurability + Harness Shell recovery on HADES gateway."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from dataclasses import dataclass

from dbos import DBOS, SetWorkflowID
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.durable_exec.dbos import DBOSDurability
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness import Shell
from pydantic_ai.workspaces import WorkspaceBackend, WorkspaceRef, WorkspaceUnavailableError

from gateway_workspace import HadesGatewayWorkspace
from operation_identity import HadesOperationIdentity


BASE = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080").rstrip("/")
TOKEN = os.environ.get("HADES_USER_TOKEN", "fixture-token-amber")
PROMPT = "Write one synthetic marker file in the assigned workspace and report the verified result."


def request(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
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


def _model_for(marker: str, calls_path: Path, run_id: str, *, quarantine_case: bool = False):
    def model(messages, info):
        with calls_path.open("a", encoding="utf-8") as stream:
            stream.write(run_id + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        tool_returns = [
            part for message in messages for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if tool_returns:
            observed = str(tool_returns[-1].content)
            if "marker recorded" in observed:
                return ModelResponse(parts=[TextPart("The synthetic marker was recorded.")])
            return ModelResponse(parts=[TextPart("The marker result was not confirmed.")])
        tool = next(item for item in info.function_tools if item.name == "run_command")
        if quarantine_case:
            command = (
                f"python -c \"from pathlib import Path; import time; p=Path('{marker}'); "
                "p.write_text((p.read_text() if p.exists() else '') + 'x'); "
                "print('marker recorded', flush=True); time.sleep(25)\""
            )
        else:
            command = (
                f"python -c \"from pathlib import Path; p=Path('{marker}'); "
                "p.write_text((p.read_text() if p.exists() else '') + 'x'); "
                "print('marker recorded')\""
            )
        return ModelResponse(parts=[ToolCallPart(tool.name, {
            "command": command,
            "timeout_seconds": 20,
        })])
    return model


class _CrashAfterGatewayResponse(HadesGatewayWorkspace):
    def _execute(self, command: str, operation_id: str):
        super()._execute(command, operation_id)
        os._exit(79)


class _CrashAfterGatewayOutcome(HadesGatewayWorkspace):
    def _execute(self, command: str, operation_id: str):
        try:
            super()._execute(command, operation_id)
        except WorkspaceUnavailableError:
            os._exit(80)
        os._exit(79)


@dataclass
class _HadesGatewayWorkspaceCapability(AbstractCapability[str]):
    """Provide the authenticated HADES workspace through the public workspace hook."""

    backend_class: type[HadesGatewayWorkspace] = HadesGatewayWorkspace
    gateway_url: str = BASE
    token: str = TOKEN
    id: str | None = "cp83_hades_gateway_workspace"

    def get_workspace(
        self, ctx: RunContext[str], *, ref: WorkspaceRef | None,
    ) -> WorkspaceBackend | None:
        task_id = ctx.deps
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("HADES workspace needs the authenticated task ID")
        backend = self.backend_class(self.gateway_url, self.token, task_id)
        if ref is not None and ref != backend.ref:
            return None
        return backend


def _child(mode: str, task_id: str, marker: str, run_id: str, state: Path) -> int:
    db_path = state / "dbos.sqlite"
    calls_path = state / "model-calls.log"
    DBOS(config={
        "name": "hades_cp83_pydantic_dbos_shell",
        "application_version": "1",
        "system_database_url": f"sqlite:///{db_path}",
    })
    agent = Agent(
        FunctionModel(
            _model_for(marker, calls_path, run_id, quarantine_case=mode.endswith("quarantine")),
            model_name="cp83-strict-dbos-peer",
        ),
        name="hades-cp83-shell",
        deps_type=str,
        capabilities=[
            _HadesGatewayWorkspaceCapability(
                backend_class=(
                    _CrashAfterGatewayResponse if mode == "crash"
                    else _CrashAfterGatewayOutcome if mode == "crash_quarantine"
                    else HadesGatewayWorkspace
                ),
            ),
            Shell(tools=["run_command"], default_timeout=20),
            HadesOperationIdentity(),
            DBOSDurability(parallel_execution_mode="sequential"),
        ],
    )

    @DBOS.workflow()
    async def run_marker(workspace_task_id: str) -> str:
        result = await agent.run(
            PROMPT, deps=workspace_task_id,
            model_settings={"temperature": 0},
        )
        return result.output

    DBOS.launch()
    if mode in {"crash", "crash_quarantine"}:
        with SetWorkflowID(run_id):
            asyncio.run(run_marker(task_id))
        raise RuntimeError("fault injection did not terminate the worker")
    result = DBOS.get_result(run_id)
    print("CP83_FINAL:" + str(result), flush=True)
    DBOS.destroy()
    return 0


def _run_child(mode: str, task_id: str, marker: str, run_id: str, state: Path):
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", mode,
         task_id, marker, run_id, str(state)],
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )


def _workspace_request(task_id: str, operation_tag: str, command: str):
    operation_id = hashlib.sha256(f"{task_id}:{operation_tag}".encode()).hexdigest()
    return request("POST", "/v1/workspace/exec", {
        "task_id": task_id,
        "command": command,
        "operation_id": operation_id,
    })


def main() -> None:
    if len(sys.argv) == 7 and sys.argv[1] == "--child":
        raise SystemExit(_child(
            sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], Path(sys.argv[6]),
        ))

    with tempfile.TemporaryDirectory(prefix="hades-cp83-dbos-") as directory:
        state = Path(directory)
        outcomes = []
        for case in range(1, 4):
            status, task = request("POST", "/v1/tasks", {
                "goal": "Write one synthetic marker in the isolated workspace and report the result."
            })
            assert status == 201, task
            task_id = str(task["task_id"])
            marker = f".cp83-marker-{uuid.uuid4().hex}.txt"
            run_id = f"hades-task-{task_id}"

            crashed = _run_child("crash", task_id, marker, run_id, state)
            assert crashed.returncode == 79, (case, crashed.returncode, crashed.stderr[-1000:])
            status, after_dispatch = request("GET", f"/v1/tasks/{task_id}")
            assert status == 200 and len(after_dispatch["effects"]) == 1, after_dispatch
            first = after_dispatch["effects"][0]
            assert first["state"] == "CONFIRMED" and first["operation_id"], first

            resumed = _run_child("resume", task_id, marker, run_id, state)
            assert resumed.returncode == 0, (case, resumed.stderr[-1200:])
            final = next((line[11:] for line in resumed.stdout.splitlines()
                          if line.startswith("CP83_FINAL:")), None)
            assert final == "The synthetic marker was recorded.", (final, resumed.stderr[-800:])

            status, after_resume = request("GET", f"/v1/tasks/{task_id}")
            assert status == 200 and len(after_resume["effects"]) == 1, after_resume
            assert after_resume["effects"][0]["effect_id"] == first["effect_id"], after_resume
            assert after_resume["effects"][0]["operation_id"] == first["operation_id"], after_resume

            status, marker_result = _workspace_request(
                task_id, "oracle-read", f"python -c \"from pathlib import Path; print(Path('{marker}').read_text())\"",
            )
            assert status == 200 and marker_result["stdout"] == "x\n", marker_result
            model_calls = (state / "model-calls.log").read_text().splitlines()
            calls_for_run = [value for value in model_calls if value == run_id]
            assert len(calls_for_run) == 2, calls_for_run

            status, cleanup = _workspace_request(
                task_id, "oracle-cleanup", f"python -c \"from pathlib import Path; Path('{marker}').unlink()\"",
            )
            assert status == 200 and cleanup["exit_code"] == 0, cleanup
            status, after_cleanup = request("GET", f"/v1/tasks/{task_id}")
            assert status == 200 and len(after_cleanup["effects"]) == 3, after_cleanup
            assert all(e["state"] == "CONFIRMED" for e in after_cleanup["effects"])
            assert after_cleanup["effects"][0]["effect_id"] == first["effect_id"]
            outcomes.append({
                "effect_reused": True,
                "marker_count": 1,
                "model_generations": len(calls_for_run),
                "workspace_cleanup": True,
                "task_state": after_cleanup["state"],
            })

        status, task = request("POST", "/v1/tasks", {
            "goal": "Write one synthetic marker, then report only if its command is confirmed."
        })
        assert status == 201, task
        task_id = str(task["task_id"])
        marker = f".cp83-uncertain-marker-{uuid.uuid4().hex}.txt"
        run_id = f"hades-task-{task_id}"
        crashed = _run_child("crash_quarantine", task_id, marker, run_id, state)
        assert crashed.returncode == 80, (crashed.returncode, crashed.stderr[-1200:])
        status, quarantined = request("GET", f"/v1/tasks/{task_id}")
        assert status == 200 and len(quarantined["effects"]) == 1, quarantined
        uncertain = quarantined["effects"][0]
        assert uncertain["state"] == "QUARANTINED", uncertain

        resumed = _run_child("resume_quarantine", task_id, marker, run_id, state)
        assert resumed.returncode == 1, (resumed.returncode, resumed.stdout[-800:])
        assert "WorkspaceUnavailableError: HADES workspace command outcome is not confirmed" in (
            resumed.stderr
        ), resumed.stderr[-1200:]
        assert "CP83_FINAL:" not in resumed.stdout
        status, after_resume = request("GET", f"/v1/tasks/{task_id}")
        assert status == 200 and len(after_resume["effects"]) == 1, after_resume
        assert after_resume["effects"][0]["effect_id"] == uncertain["effect_id"]
        assert after_resume["effects"][0]["state"] == "QUARANTINED"

        status, observer = request("POST", "/v1/tasks", {
            "goal": "Independently inspect one synthetic workspace marker."
        })
        assert status == 201, observer
        observer_id = str(observer["task_id"])
        status, marker_result = _workspace_request(
            observer_id, "uncertainty-oracle-read",
            f"python -c \"from pathlib import Path; print(Path('{marker}').read_text())\"",
        )
        assert status == 200 and marker_result["stdout"] == "x\n", marker_result
        calls_before_repeat = (state / "model-calls.log").read_text().splitlines()
        quarantined_calls = [value for value in calls_before_repeat if value == run_id]
        repeated = _run_child("resume_quarantine", task_id, marker, run_id, state)
        assert repeated.returncode == 1, (repeated.returncode, repeated.stderr[-1200:])
        assert "WorkspaceUnavailableError: HADES workspace command outcome is not confirmed" in (
            repeated.stderr
        ), repeated.stderr[-1200:]
        assert "CP83_FINAL:" not in repeated.stdout
        assert (state / "model-calls.log").read_text().splitlines() == calls_before_repeat
        status, after_repeated_resume = request("GET", f"/v1/tasks/{task_id}")
        assert status == 200 and len(after_repeated_resume["effects"]) == 1
        assert after_repeated_resume["effects"][0]["effect_id"] == uncertain["effect_id"]
        assert after_repeated_resume["effects"][0]["state"] == "QUARANTINED"
        status, cleanup = _workspace_request(
            observer_id, "uncertainty-oracle-cleanup",
            f"python -c \"from pathlib import Path; Path('{marker}').unlink()\"",
        )
        assert status == 200 and cleanup["exit_code"] == 0, cleanup
        outcomes.append({
            "scenario": "quarantined timeout across DBOS worker restart",
            "effect_id_preserved": True,
            "effect_state": "QUARANTINED",
            "independently_observed_marker_count": 1,
            "duplicate_dispatch": False,
            "repeat_resume_model_generations": 0,
            "task_state": after_repeated_resume["state"],
            "final_response": None,
            "resume_result": "fail-closed exception; no false success",
            "cleanup": True,
        })
        print(json.dumps({
            "classification": "CONTRACT_TEST",
            "pydantic_ai_slim": "2.56.0",
            "pydantic_ai_harness": "0.56.0",
            "dbos": "3.2.0",
            "dbos_durability": True,
            "workflow_identity": "deterministically derived from HADES task ID",
            "crash_boundary": "after gateway confirmed before Harness received result",
            "workflow_resume_repetitions": 3,
            "quarantined_restart_case_passed": True,
            "quarantined_task_state": after_repeated_resume["state"],
            "quarantined_tool_calls_after_timeout": len(quarantined_calls),
            "all_repetitions_passed": True,
            "model_generations_per_repetition": 2,
            "effect_reused_per_repetition": True,
            "marker_count_per_repetition": 1,
            "marker_cleanup_per_repetition": True,
            "task_state": "RUNNING",
            "task_finalization_in_scope": False,
            "outcomes": outcomes,
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
