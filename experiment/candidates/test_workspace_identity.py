"""Verify A/C adapters bind workspace dispatch to persisted tool-call identity."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from unittest.mock import patch

import api
from pydantic_ai import Agent, FunctionToolset, RunContext, Tool
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

TASK_ID = "8c7e3024-d47f-4d9c-85db-96572814da32"
CALL_ID = "call-persisted-workspace-7"
COMMAND = "git status --short"


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"state": "CONFIRMED", "effect_id": "synthetic"}).encode()


def _assert_identity(requests: list[dict], call_id: str) -> None:
    assert len(requests) == 1, requests
    expected = hashlib.sha256(f"{TASK_ID}:{call_id}".encode()).hexdigest()
    assert requests[0]["operation_id"] == expected, requests
    assert requests[0]["task_id"] == TASK_ID
    assert requests[0]["command"] == COMMAND


def main() -> None:
    captured: list[dict] = []

    def fake_urlopen(request, timeout=30):
        assert timeout == 35
        captured.append(json.loads(request.data))
        return _Response()

    with patch.object(urllib.request, "urlopen", fake_urlopen):
        try:
            api.gateway_call("workspace_exec", {"command": COMMAND}, "fixture-token", TASK_ID)
        except ValueError as exc:
            assert "persisted tool-call identity" in str(exc)
        else:
            raise AssertionError("workspace dispatch without persisted identity was accepted")
        assert not captured

        # Lean-loop path: the model protocol's original tool-call ID is available here.
        api.gateway_call(
            "workspace_exec", {"command": COMMAND}, "fixture-token", TASK_ID,
            tool_call_id=CALL_ID,
        )
        _assert_identity(captured, CALL_ID)
        captured.clear()

        def invoke(ctx: RunContext[None], **kwargs):
            return api.gateway_call(
                "workspace_exec", kwargs, "fixture-token", TASK_ID,
                tool_call_id=ctx.tool_call_id,
            )

        toolset = FunctionToolset()
        spec = next(t for t in api.VISIBLE_TOOLS if t["name"] == "workspace_exec")
        toolset.add_tool(Tool.from_schema(
            function=invoke,
            name=spec["name"],
            description=spec["description"],
            json_schema=spec["parameters"],
            takes_ctx=True,
        ))

        def model(messages, _info):
            if any(isinstance(part, ToolReturnPart) for message in messages for part in message.parts):
                return ModelResponse(parts=[TextPart("command observation received")])
            return ModelResponse(parts=[ToolCallPart(
                "workspace_exec", {"command": COMMAND}, tool_call_id=CALL_ID,
            )])

        result = Agent(
            FunctionModel(model, model_name="workspace-identity-peer"),
            toolsets=[toolset],
        ).run_sync("Inspect the synthetic repository")
        assert result.output == "command observation received", result.output
        _assert_identity(captured, CALL_ID)

    print("PASS Pydantic tool context and lean adapter bind workspace effects to the same persisted call ID")


if __name__ == "__main__":
    main()
