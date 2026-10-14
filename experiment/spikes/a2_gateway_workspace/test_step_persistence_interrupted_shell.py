"""Verify Harness StepPersistence exposes an interrupted Shell call for review.

The synthetic workspace writes one marker and then terminates the worker. This
checks the upstream journal contract only; it does not resume or replay the
uncertain command and does not prove HADES gateway reconciliation.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.workspaces import (
    CommandResult,
    SupportsCommands,
    WorkspaceBackend,
    WorkspaceCommand,
    WorkspaceRef,
)
from pydantic_ai_harness import Shell
from pydantic_ai_harness.step_persistence import (
    SqliteStepStore,
    StepPersistence,
    continue_run,
)


RUN_ID = "cp81-interrupted-shell-contract"


class _SyntheticWorkspace(WorkspaceBackend, SupportsCommands):
    marker: Path

    def __init__(self, marker: Path, *, crash: bool) -> None:
        self.marker = marker
        self.crash = crash

    @property
    def ref(self) -> WorkspaceRef:
        return WorkspaceRef(provider="synthetic", id="interrupted-shell")

    async def working_dir(self) -> str:
        return "/workspace"

    async def run(
        self,
        command: WorkspaceCommand,
        *,
        shell: bool = False,
        env=None,
        timeout=None,
    ) -> CommandResult:
        await asyncio.to_thread(self._dispatch)
        return CommandResult(exit_code=0, stdout="synthetic result", stderr="")

    def _dispatch(self) -> None:
        self.marker.write_text("one synthetic dispatch\n")
        if self.crash:
            os._exit(79)


def _model(messages, info):
    tool = next(item for item in info.function_tools if item.name == "run_command")
    return ModelResponse(
        parts=[ToolCallPart(tool.name, {"command": "write synthetic marker", "timeout_seconds": 20})]
    )


def _crash_worker(db_path: Path, marker_path: Path) -> None:
    store = SqliteStepStore(database=db_path)
    agent = Agent(
        FunctionModel(_model, model_name="interrupted-shell-peer"),
        capabilities=[
            Shell(tools=["run_command"]),
            StepPersistence(
                store=store,
                agent_name="cp81-shell-probe",
                run_id=RUN_ID,
                capture_frontier=True,
            ),
        ],
    )
    agent.run_sync(
        "Execute one synthetic marker command",
        workspace=_SyntheticWorkspace(marker_path, crash=True),
    )


async def _verify(db_path: Path, marker_path: Path) -> None:
    store = SqliteStepStore(database=db_path)
    run = await store.get_run(run_id=RUN_ID)
    assert run is not None, "StepPersistence did not retain the run record"
    unresolved = await store.list_unresolved_tool_effects(run_id=RUN_ID)
    assert len(unresolved) == 1, unresolved
    effect = unresolved[0]
    assert str(effect.status) == "started", effect
    snapshot = await store.latest_snapshot(run_id=RUN_ID, include_interrupted=True)
    assert snapshot is not None and str(snapshot.state) == "interrupted", snapshot
    history = await continue_run(store, run_id=RUN_ID, include_interrupted=True)
    calls = [part for message in history for part in message.parts if isinstance(part, ToolCallPart)]
    assert len(calls) == 1 and calls[0].tool_call_id == effect.tool_call_id
    assert marker_path.read_text() == "one synthetic dispatch\n"
    default_snapshot = await store.latest_snapshot(run_id=RUN_ID, include_interrupted=False)
    assert default_snapshot is not None and str(default_snapshot.state) == "complete"
    default_history = await continue_run(store, run_id=RUN_ID)
    default_calls = [
        part for message in default_history for part in message.parts if isinstance(part, ToolCallPart)
    ]
    assert not default_calls
    print(
        "PASS StepPersistence retains the same unresolved tool identity; both interrupted and "
        "default continuation can omit the pending call, so caller must inspect unresolved "
        "effects before resume; no replay was attempted"
    )


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "crash":
        _crash_worker(Path(sys.argv[2]), Path(sys.argv[3]))
        raise AssertionError("fault-injected worker unexpectedly returned")

    with tempfile.TemporaryDirectory(prefix="hades-a2-step-persistence-") as directory:
        root = Path(directory)
        db_path = root / "steps.sqlite"
        marker_path = root / "marker.txt"
        result = subprocess.run(
            [sys.executable, __file__, "crash", str(db_path), str(marker_path)],
            check=False,
            timeout=20,
        )
        assert result.returncode == 79, result.returncode
        asyncio.run(_verify(db_path, marker_path))


if __name__ == "__main__":
    main()
