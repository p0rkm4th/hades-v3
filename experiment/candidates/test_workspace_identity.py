"""Verify A/C adapters bind workspace dispatch to persisted tool-call identity."""

from __future__ import annotations

import hashlib
import http.client
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
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


def _test_stateless_resume_route() -> None:
    current = {
        "task_id": TASK_ID,
        "state": "RUNNING",
        "effects": [{"effect_kind": "WORKSPACE_COMMAND", "state": "CONFIRMED"}],
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps({
            "candidate": "lean",
            "user_token": "fixture-token-amber",
            "task_id": TASK_ID,
            "messages": [{"role": "user", "content": "Continue the synthetic task"}],
        })
        with (
            patch.object(api, "gateway_call", return_value=current),
            patch.object(api, "transition_task") as transition,
            patch.object(api, "chat_openai") as model,
        ):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            connection.request("POST", "/api/turn", body=body,
                               headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            result = json.loads(response.read())
            connection.close()
            assert response.status == 409, (response.status, result)
            assert result["task_state"] == "WAITING" and result["operator_review_required"], result
            transition.assert_called_once()
            model.assert_not_called()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def main() -> None:
    provider = api.pydantic_provider()
    assert provider.client.max_retries == 0, provider.client.max_retries

    running_with_confirmed_workspace_effect = {
        "state": "RUNNING",
        "effects": [{"effect_kind": "WORKSPACE_COMMAND", "state": "CONFIRMED"}],
    }
    with patch.object(api, "transition_task") as transition:
        guarded = api.workspace_resume_guard("fixture-token-amber", TASK_ID,
                                             running_with_confirmed_workspace_effect)
        assert guarded is not None and guarded["task_state"] == "WAITING", guarded
        transition.assert_called_once()
        assert transition.call_args.args[:4] == (
            "fixture-token-amber", TASK_ID, "WAITING", [],
        ), transition.call_args
        assert transition.call_args.kwargs["error_type"] == "workspace_resume_requires_persisted_identity"
    with patch.object(api, "transition_task") as transition:
        guarded = api.workspace_resume_guard("fixture-token-amber", TASK_ID, {
            "state": "WAITING",
            "effects": [{"effect_kind": "WORKSPACE_COMMAND", "state": "CONFIRMED"}],
        })
        assert guarded is not None and guarded["operator_review_required"], guarded
        transition.assert_not_called()
    assert api.workspace_resume_guard("fixture-token-amber", TASK_ID, {
        "state": "RUNNING", "effects": [],
    }) is None
    assert api.workspace_resume_guard("fixture-token-amber", TASK_ID, {
        "state": "RUNNING", "effects": [{"effect_kind": "MEMORY_MUTATION", "state": "CONFIRMED"}],
    }) is None
    with patch.object(api, "transition_task") as transition:
        guarded = api.workspace_resume_guard("fixture-token-amber", TASK_ID, {"state": "RUNNING"})
        assert guarded is not None and guarded["task_state"] == "WAITING", guarded
        assert transition.call_args.kwargs["error_type"] == "workspace_effect_snapshot_unavailable"
    _test_stateless_resume_route()

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

    print("PASS provider retry budget, stateless workspace-resume quarantine, and A/C tool-call identity contracts")


if __name__ == "__main__":
    main()
