"""Forward Pydantic tool-call identity to the HADES workspace adapter."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool, WrapperToolset
from pydantic_ai import RunContext


_tool_call_id: ContextVar[str | None] = ContextVar("hades_tool_call_id", default=None)


def current_tool_call_id() -> str | None:
    """Return the active Harness tool-call ID for this workspace invocation."""

    return _tool_call_id.get()


class _IdentityToolset(WrapperToolset[Any]):
    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[Any],
        tool: ToolsetTool[Any],
    ) -> Any:
        token = _tool_call_id.set(ctx.tool_call_id)
        try:
            return await super().call_tool(name, tool_args, ctx, tool)
        finally:
            _tool_call_id.reset(token)


class HadesOperationIdentity(AbstractCapability[Any]):
    """Wrap Harness tool dispatch so adapters can bind calls to persisted IDs."""

    def get_wrapper_toolset(
        self, toolset: AbstractToolset[Any]
    ) -> AbstractToolset[Any] | None:
        return _IdentityToolset(toolset)
