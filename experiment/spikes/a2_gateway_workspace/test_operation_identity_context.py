"""Check that the pinned Harness can carry a tool-call identity to HADES workspace I/O.

This proves identity forwarding through the real Shell capability, not that an
identity is stable across restart or that a gateway replay is idempotent.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.workspaces import (
    CommandResult,
    SupportsCommands,
    WorkspaceBackend,
    WorkspaceCommand,
    WorkspaceRef,
)
from pydantic_ai_harness import Shell
from operation_identity import HadesOperationIdentity, current_tool_call_id


_observed: list[str] = []


class _SyntheticWorkspace(WorkspaceBackend, SupportsCommands):
    @property
    def ref(self) -> WorkspaceRef:
        return WorkspaceRef(provider="synthetic", id="identity-probe")

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
        await asyncio.to_thread(self._dispatch, command)
        return CommandResult(exit_code=0, stdout="synthetic success", stderr="")

    @staticmethod
    def _dispatch(command: WorkspaceCommand) -> None:
        identity = current_tool_call_id()
        assert identity
        _observed.append(identity)


def _model(messages, info):
    if any(isinstance(part, ToolReturnPart) for message in messages for part in message.parts):
        return ModelResponse(parts=[TextPart("identity forwarding verified")])
    tool = next(item for item in info.function_tools if item.name == "run_command")
    return ModelResponse(
        parts=[ToolCallPart(tool.name, {"command": "printf safe", "timeout_seconds": 20})]
    )


def main() -> None:
    _observed.clear()
    agent = Agent(
        FunctionModel(_model, model_name="strict-identity-peer"),
        capabilities=[Shell(tools=["run_command"]), HadesOperationIdentity()],
    )
    result = agent.run_sync("Run the synthetic safe command", workspace=_SyntheticWorkspace())
    assert result.output == "identity forwarding verified"
    assert len(_observed) == 1 and _observed[0]
    print("PASS pinned Shell forwarded its tool-call identity through async workspace I/O")


if __name__ == "__main__":
    main()
