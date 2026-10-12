from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, "/app/candidates")
from api import gateway_call
from mcp.server import MCPServer
from pydantic import BaseModel, Field


server = MCPServer("HADES shared fixture tools")
USER_TOKEN = os.environ["HADES_USER_TOKEN"]
TASK_FILE = Path(os.environ["HADES_TASK_FILE"])
TRACE_FILE = Path(os.environ["HADES_TRACE_FILE"])


class ShoppingItem(BaseModel):
    name: str
    amount: float = Field(gt=0)


def invoke(name: str, **arguments):
    task_id = TASK_FILE.read_text().strip()
    TRACE_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with TRACE_FILE.open("a", encoding="utf-8") as stream:
        stream.write(name + "\n")
    return gateway_call(name, arguments, USER_TOKEN, task_id)


@server.tool()
def inventory_read() -> dict:
    """Read current synthetic pantry stock for this user. This never writes memory."""
    return invoke("inventory_read")


@server.tool()
def shopping_list_read() -> dict:
    """Read this user's synthetic shopping list."""
    return invoke("shopping_list_read")


@server.tool()
def shopping_list_change(add: list[ShoppingItem] | None = None, remove: list[str] | None = None) -> dict:
    """Apply compound shopping-list additions/removals and verify the resulting state."""
    return invoke("shopping_list_change", add=[item.model_dump() for item in add or []], remove=remove or [])


@server.tool()
def infrastructure_read() -> dict:
    """Read synthetic infrastructure observations with their freshness and availability."""
    return invoke("infrastructure_read")


@server.tool()
def memory_read(key: str) -> dict:
    """Read one explicitly stored memory for this user."""
    return invoke("memory_read", key=key)


@server.tool()
def memory_write(key: str, value: dict) -> dict:
    """Store a memory only when the user explicitly asked to remember it."""
    return invoke("memory_write", key=key, value=value)


@server.tool()
def task_resume() -> dict:
    """Read the current durable task and its canonical checkpoint."""
    return invoke("task_resume")


@server.tool()
def task_checkpoint(state: Literal["RUNNING", "WAITING", "COMPLETED", "FAILED"], checkpoint: dict) -> dict:
    """Persist progress in the current task's canonical checkpoint."""
    return invoke("task_checkpoint", state=state, checkpoint=checkpoint)


@server.tool()
def commitment_submit(target_id: str, details: str, approval_id: str) -> dict:
    """Submit an exact approved synthetic commitment; an uncertain result must be reconciled, never repeated."""
    return invoke("commitment_submit", target_id=target_id, details=details, approval_id=approval_id)


@server.tool()
def commitment_reconcile(effect_id: str) -> dict:
    """Read back one quarantined commitment's protected fixture state without replaying it."""
    return invoke("commitment_reconcile", effect_id=effect_id)


@server.tool()
def workspace_exec(command: str) -> dict:
    """Run one bounded shell command in this user's isolated synthetic Git workspace."""
    return invoke("workspace_exec", command=command)


if __name__ == "__main__":
    server.run()
