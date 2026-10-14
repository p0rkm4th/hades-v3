"""Exercise A2 Shell recovery when the gateway confirms before the worker dies.

The worker is killed after the authenticated gateway response arrives but
before Harness records the tool return. Recovery must replay the original
tool-call identity and receive the saved result rather than redispatching.
"""

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
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness import Shell
from pydantic_ai_harness.step_persistence import SqliteStepStore, StepPersistence, continue_run

from gateway_workspace import HadesGatewayWorkspace
from operation_identity import HadesOperationIdentity
from recovery_gate import inspect_resume


_RUN_ID = "cp82-confirmed-command-recovery"


def _call(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        os.environ["GATEWAY_URL"].rstrip("/") + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {os.environ['HADES_USER_TOKEN']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def _command(marker: str) -> str:
    return (
        f"python -c \"from pathlib import Path; p=Path('{marker}'); "
        "p.write_text((p.read_text() if p.exists() else '') + 'x'); "
        "print('marker recorded')\""
    )


class _CrashAfterGatewayResponse(HadesGatewayWorkspace):
    def _execute(self, command: str, operation_id: str):
        super()._execute(command, operation_id)
        os._exit(79)


def _model_for(marker: str):
    def model(messages, info):
        if any(isinstance(part, ToolReturnPart) for message in messages for part in message.parts):
            return ModelResponse(parts=[TextPart("The synthetic marker command completed.")])
        tool = next(item for item in info.function_tools if item.name == "run_command")
        return ModelResponse(parts=[ToolCallPart(tool.name, {
            "command": _command(marker),
            "timeout_seconds": 20,
        })])
    return model


def _worker(mode: str, task_id: str, store_path: Path) -> None:
    store = SqliteStepStore(database=store_path)
    workspace_type = _CrashAfterGatewayResponse if mode == "crash" else HadesGatewayWorkspace
    workspace = workspace_type(
        os.environ["GATEWAY_URL"], os.environ["HADES_USER_TOKEN"], task_id,
    )
    agent = Agent(
        FunctionModel(_model_for(f".cp82-marker-{task_id}.txt"), model_name="cp82-strict-recovery-peer"),
        capabilities=[
            Shell(tools=["run_command"], default_timeout=20),
            HadesOperationIdentity(),
            StepPersistence(
                store=store,
                agent_name="cp82-shell-recovery",
                run_id=_RUN_ID if mode == "crash" else None,
                capture_frontier=True,
            ),
        ],
    )
    if mode == "crash":
        agent.run_sync("Write exactly one synthetic marker", workspace=workspace)
        raise AssertionError("fault-injected worker unexpectedly returned")
    status, task_state = _call("GET", f"/v1/tasks/{task_id}")
    if status != 200:
        raise RuntimeError("recovery coordinator could not read canonical HADES task state")
    pending = asyncio.run(store.list_unresolved_tool_effects(run_id=_RUN_ID))
    decision = inspect_resume(task_id, pending, task_state)
    if not decision["allow"]:
        raise RuntimeError(f"recovery coordinator refused continuation: {decision['reason']}")
    history = asyncio.run(continue_run(store, run_id=_RUN_ID, include_interrupted=True))
    result = agent.run_sync(None, message_history=history, workspace=workspace)
    if "marker command completed" not in result.output:
        raise AssertionError("recovered run did not produce the expected final response")
    print(result.output)


async def _effect_record(store_path: Path):
    store = SqliteStepStore(database=store_path)
    unresolved = await store.list_unresolved_tool_effects(run_id=_RUN_ID)
    assert len(unresolved) == 1, unresolved
    return unresolved[0]


def main() -> None:
    if len(sys.argv) == 5 and sys.argv[1] == "worker":
        _worker(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
        return
    status, task = _call("POST", "/v1/tasks", {"goal": "Write exactly one synthetic marker"})
    assert status == 201, task
    task_id = task["task_id"]
    with tempfile.TemporaryDirectory(prefix="hades-cp82-step-persistence-") as directory:
        store_path = Path(directory) / "steps.sqlite"
        crash = subprocess.run(
            [sys.executable, __file__, "worker", "crash", task_id, str(store_path)],
            check=False,
            timeout=25,
        )
        assert crash.returncode == 79, crash.returncode
        unresolved = asyncio.run(_effect_record(store_path))
        assert str(unresolved.status) == "started", unresolved
        history = asyncio.run(continue_run(
            SqliteStepStore(database=store_path),
            run_id=_RUN_ID,
            include_interrupted=True,
        ))
        calls = [part for message in history for part in message.parts if isinstance(part, ToolCallPart)]
        assert len(calls) == 1 and calls[0].tool_call_id == unresolved.tool_call_id
        status, task_state = _call("GET", f"/v1/tasks/{task_id}")
        assert status == 200 and len(task_state["effects"]) == 1, task_state
        assert task_state["effects"][0]["state"] == "CONFIRMED", task_state
        decision = inspect_resume(task_id, [unresolved], task_state)
        assert decision["allow"], decision
        original_effect_id = task_state["effects"][0]["effect_id"]

        resumed = subprocess.run(
            [sys.executable, __file__, "worker", "resume", task_id, str(store_path)],
            check=False,
            timeout=25,
            capture_output=True,
            text=True,
        )
        assert resumed.returncode == 0, resumed.stderr[-1000:]
        assert "marker command completed" in resumed.stdout
        status, after = _call("GET", f"/v1/tasks/{task_id}")
        assert status == 200 and len(after["effects"]) == 1, after
        assert (after["effects"][0]["state"], after["effects"][0]["effect_id"]) == (
            "CONFIRMED", original_effect_id,
        ), after
        assert inspect_resume(task_id, [unresolved], after)["allow"]
        # Duplicate resume repeats only the original tool call; HADES returns the
        # persisted result, so task/effect identity and target state remain stable.
        repeated = subprocess.run(
            [sys.executable, __file__, "worker", "resume", task_id, str(store_path)],
            check=False,
            timeout=25,
            capture_output=True,
            text=True,
        )
        assert repeated.returncode == 0, repeated.stderr[-1000:]
        status, after_repeat = _call("GET", f"/v1/tasks/{task_id}")
        assert status == 200 and len(after_repeat["effects"]) == 1, after_repeat
        assert after_repeat["effects"][0]["effect_id"] == original_effect_id, after_repeat
        original_journal_effect = asyncio.run(_effect_record(store_path))
        assert str(original_journal_effect.status) == "started", original_journal_effect

        marker_path = f".cp82-marker-{task_id}.txt"
        read_command = f"python -c \"from pathlib import Path; print(Path('{marker_path}').read_text())\""
        read_id = hashlib.sha256(f"{task_id}:independent-marker-read".encode()).hexdigest()
        status, marker = _call("POST", "/v1/workspace/exec", {
            "task_id": task_id,
            "command": read_command,
            "operation_id": read_id,
        })
        assert status == 200 and marker["stdout"] == "x\n", (status, marker)
        status, after_read = _call("GET", f"/v1/tasks/{task_id}")
        assert status == 200 and len(after_read["effects"]) == 2, after_read
        assert after_read["effects"][0]["effect_id"] == original_effect_id, after_read
        cleanup_command = f"python -c \"from pathlib import Path; Path('{marker_path}').unlink()\""
        cleanup_id = hashlib.sha256(f"{task_id}:marker-cleanup".encode()).hexdigest()
        status, cleaned = _call("POST", "/v1/workspace/exec", {
            "task_id": task_id,
            "command": cleanup_command,
            "operation_id": cleanup_id,
        })
        assert status == 200 and cleaned["exit_code"] == 0, (status, cleaned)
        print(
            "PASS the HADES-aware resume gate matched the original call to its confirmed effect; "
            "repeated resumes returned the same result, independent read found one marker, and cleanup passed. "
            "LIMITATION: StepPersistence keeps its original run entry marked started; the gate rechecks "
            "canonical HADES effects before each continuation."
        )


if __name__ == "__main__":
    main()
