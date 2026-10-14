"""Bind each Harness workspace dispatch to its persisted model tool call."""

from __future__ import annotations

import hashlib
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool, WrapperToolset


@dataclass
class _ToolCallIdentity:
    tool_call_id: str
    next_dispatch: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def operation_id(self, task_id: str) -> str:
        # One Harness tool may perform several backend calls. Keep them distinct,
        # but make replay of the same ordered tool call deterministic.
        with self.lock:
            ordinal = self.next_dispatch
            self.next_dispatch += 1
        return derive_operation_id(task_id, self.tool_call_id, ordinal)


_tool_call: ContextVar[_ToolCallIdentity | None] = ContextVar("hades_tool_call", default=None)


def derive_operation_id(task_id: str, tool_call_id: str, ordinal: int) -> str:
    if not task_id or not tool_call_id or ordinal < 0:
        raise ValueError("task, persisted tool-call identity, and nonnegative ordinal are required")
    raw = f"{task_id}:{tool_call_id}:{ordinal}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def next_operation_id(task_id: str) -> str:
    identity = _tool_call.get()
    if identity is None or not identity.tool_call_id:
        raise RuntimeError("HADES workspace call has no persisted tool identity")
    return identity.operation_id(task_id)


class _IdentityToolset(WrapperToolset[Any]):
    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[Any],
        tool: ToolsetTool[Any],
    ) -> Any:
        token = _tool_call.set(_ToolCallIdentity(ctx.tool_call_id))
        try:
            return await super().call_tool(name, tool_args, ctx, tool)
        finally:
            _tool_call.reset(token)


class HadesOperationIdentity(AbstractCapability[Any]):
    """Wrap Harness tool dispatch so adapters can bind calls to persisted IDs."""

    def get_wrapper_toolset(
        self, toolset: AbstractToolset[Any]
    ) -> AbstractToolset[Any] | None:
        return _IdentityToolset(toolset)
