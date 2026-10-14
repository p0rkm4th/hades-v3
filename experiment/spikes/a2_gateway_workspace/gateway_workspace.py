"""Pydantic workspace adapter that routes shell commands through HADES."""

from __future__ import annotations

import asyncio
import json
import shlex
import urllib.error
import urllib.request
from collections.abc import Mapping

from pydantic_ai.workspaces import (
    CommandResult,
    SupportsCommands,
    WorkspaceBackend,
    WorkspaceCommand,
    WorkspaceRef,
    WorkspaceUnavailableError,
)


class HadesGatewayWorkspace(WorkspaceBackend, SupportsCommands):
    """Expose only the gateway's bounded workspace command to Harness tools."""

    def __init__(self, gateway_url: str, token: str, task_id: str) -> None:
        self._gateway_url = gateway_url.rstrip("/")
        self._token = token
        self._task_id = task_id
        self._ref = WorkspaceRef(provider="hades-gateway", id=task_id)

    @property
    def ref(self) -> WorkspaceRef:
        return self._ref

    async def working_dir(self) -> str:
        return "/workspace"

    async def run(
        self,
        command: WorkspaceCommand,
        *,
        shell: bool = False,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        if env:
            raise ValueError("HADES workspace commands use the runner's fixed environment")
        if timeout not in (None, 20, 20.0):
            raise ValueError("HADES workspace commands have a fixed 20 second limit")
        if isinstance(command, str):
            if not shell:
                raise TypeError("string commands require shell=True")
            command_text = command
        else:
            if shell:
                raise TypeError("argv commands require shell=False")
            command_text = shlex.join(command)
        return await asyncio.to_thread(self._execute, command_text)

    def _execute(self, command: str) -> CommandResult:
        body = json.dumps({"task_id": self._task_id, "command": command}).encode()
        request = urllib.request.Request(
            f"{self._gateway_url}/v1/workspace/exec",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=25) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise WorkspaceUnavailableError(
                f"HADES workspace rejected the command (HTTP {error.code})"
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            raise WorkspaceUnavailableError("HADES workspace result is unavailable") from None
        if result.get("state") != "CONFIRMED" or result.get("timed_out"):
            # The gateway retains any uncertain effect; this adapter never retries it.
            raise WorkspaceUnavailableError("HADES workspace command outcome is not confirmed")
        return CommandResult(
            exit_code=int(result["exit_code"]),
            stdout=str(result.get("stdout", "")),
            stderr=str(result.get("stderr", "")),
        )
