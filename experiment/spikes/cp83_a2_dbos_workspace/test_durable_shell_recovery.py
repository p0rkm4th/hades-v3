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
from pydantic_ai.workspaces import WorkspaceBackend, WorkspaceRef

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


def _model_for(marker: str, calls_path: Path, run_id: str):
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
        FunctionModel(_model_for(marker, calls_path, run_id), model_name="cp83-strict-dbos-peer"),
        name="hades-cp83-shell",
        deps_type=str,
        capabilities=[
            _HadesGatewayWorkspaceCapability(
                backend_class=(_CrashAfterGatewayResponse if mode == "crash" else HadesGatewayWorkspace),
            ),
            Shell(tools=["run_command"], default_timeout=20),
            HadesOperationIdentity(),
            DBOSDurability(parallel_execution_mode="sequential"),
        ],
    )

    @DBOS.workflow()
    async def run_marker(workspace_task_id: str) -> str:
        result = await agent.run(PROMPT, deps=workspace_task_id)
        return result.output

    DBOS.launch()
    if mode == "crash":
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
        print(json.dumps({
            "classification": "CONTRACT_TEST",
            "pydantic_ai_slim": "2.56.0",
            "pydantic_ai_harness": "0.56.0",
            "dbos": "3.2.0",
            "dbos_durability": True,
            "workflow_identity": "deterministically derived from HADES task ID",
            "crash_boundary": "after gateway confirmed before Harness received result",
            "workflow_resume_repetitions": len(outcomes),
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
