"""Fail-closed gate for resuming interrupted A2 workspace tool calls."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from operation_identity import derive_operation_id

_UNCERTAIN = {"INTENDED", "DISPATCHED", "UNRESOLVED", "QUARANTINED"}


def inspect_resume(task_id: str, pending_calls: Sequence[Any], task_record: dict[str, Any]) -> dict[str, Any]:
    """Check pending Harness calls against the authenticated HADES task/effect read.

    An absent matching effect means the gateway never durably reserved that
    backend dispatch. A confirmed matching effect can be replayed because the
    gateway returns its saved result. Any uncertain effect blocks model resume.
    """

    if task_record.get("task_id") != task_id:
        return {"allow": False, "reason": "task identity mismatch"}
    # WAITING covers approval and other owner-action states; resuming the agent
    # there could bypass the intended pause even if a prior effect is confirmed.
    if task_record.get("state") != "RUNNING":
        return {"allow": False, "reason": "task is not actively resumable"}
    if not pending_calls:
        return {"allow": False, "reason": "no interrupted tool call to resume"}

    effects = task_record.get("effects")
    if not isinstance(effects, list):
        return {"allow": False, "reason": "canonical effect snapshot unavailable"}
    workspace = [effect for effect in effects if effect.get("effect_kind") == "WORKSPACE_COMMAND"]
    if any(effect.get("state") in _UNCERTAIN for effect in effects):
        return {"allow": False, "reason": "task has an unresolved effect"}

    # Each call's ordinal cannot exceed the number of already-recorded workspace
    # effects on this task. This makes lookup bounded and handles prior commands.
    max_ordinal = len(workspace)
    for pending in pending_calls:
        call_id = getattr(pending, "tool_call_id", None)
        if not isinstance(call_id, str) or not call_id:
            return {"allow": False, "reason": "interrupted tool call has no stable identity"}
        matching = {
            derive_operation_id(task_id, call_id, ordinal)
            for ordinal in range(max_ordinal + 1)
        }
        for effect in workspace:
            operation_id = effect.get("operation_id")
            if operation_id in matching and effect.get("state") != "CONFIRMED":
                return {"allow": False, "reason": "matching workspace effect is not confirmed"}

    return {"allow": True, "reason": "canonical effects permit original-call resume"}
