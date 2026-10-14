"""Check that the pinned Harness can carry a tool-call identity to HADES workspace I/O.

This proves identity forwarding through the real Shell capability, not that an
identity is stable across restart or that a gateway replay is idempotent.
"""

from __future__ import annotations

import asyncio
import contextvars
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.toolsets import WrapperToolset
from pydantic_ai.workspaces import (
    CommandResult,
    SupportsCommands,
    WorkspaceBackend,
    WorkspaceCommand,
    WorkspaceRef,
)
from pydantic_ai_harness import Shell


_current_call: contextvars.ContextVar[tuple[str | None, str | None] | None] = (
    contextvars.ContextVar("hades_operation_identity", default=None)
)
_observed: list[tuple[str, str]] = []


class _IdentityWrapper(WrapperToolset[Any]):
    async def call_tool(self, name, tool_args, ctx, tool):
        token = _current_call.set((ctx.run_id, ctx.tool_call_id))
        try:
            return await super().call_tool(name, tool_args, ctx, tool)
        finally:
            _current_call.reset(token)


class _IdentityCapability(AbstractCapability[Any]):
    def get_wrapper_toolset(self, toolset):
        return _IdentityWrapper(toolset)


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
        identity = _current_call.get()
        assert identity and identity[0] and identity[1]
        _observed.append((identity[0], identity[1]))


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
        capabilities=[Shell(tools=["run_command"]), _IdentityCapability()],
    )
    result = agent.run_sync("Run the synthetic safe command", workspace=_SyntheticWorkspace())
    assert result.output == "identity forwarding verified"
    assert len(_observed) == 1 and all(_observed[0])
    print("PASS pinned Shell forwarded run and tool-call identities through async workspace I/O")


if __name__ == "__main__":
    main()
