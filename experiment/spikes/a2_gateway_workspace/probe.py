"""Strict synthetic Harness-to-HADES workspace integration probe."""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness import FileSystem, Shell

from gateway_workspace import HadesGatewayWorkspace


GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://tool-gateway:8080")
TOKEN = os.environ.get("HADES_USER_TOKEN", "fixture-token-amber")
MODEL_CALLS = 0


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{GATEWAY_URL}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=25) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"gateway request failed with HTTP {error.code}") from None


def scripted_model(messages, _agent_info):
    global MODEL_CALLS
    MODEL_CALLS += 1
    retries = [
        part for message in messages if isinstance(message, ModelRequest)
        for part in message.parts if isinstance(part, RetryPromptPart)
    ]
    if retries:
        detail = str(retries[-1].content)
        print(json.dumps({"harness_tool_retry": detail[:300]}, sort_keys=True), flush=True)
        return ModelResponse(parts=[TextPart("The file tool requested a retry; no edit was made.")])
    tool_returns = [
        part for message in messages if isinstance(message, ModelRequest)
        for part in message.parts if isinstance(part, ToolReturnPart)
    ]
    returned_names = {part.tool_name for part in tool_returns}
    if "read_file" not in returned_names:
        return ModelResponse(parts=[ToolCallPart("read_file", {"path": "discount.py"})])
    if "write_file" not in returned_names:
        prior_read = next(part for part in tool_returns if part.tool_name == "read_file")
        read_result = str(prior_read.content)
        match = re.search(r"\| hash:([0-9a-f]{12})\]", read_result)
        valid_read = bool(match and "1 + percent / 100" in read_result)
        print(json.dumps({
            "read_file_observation": {
                "has_content_hash": bool(match),
                "contains_expected_fixture_source": "1 + percent / 100" in read_result,
                "not_found": read_result.startswith("Path not found:"),
            }
        }, sort_keys=True), flush=True)
        if not valid_read:
            return ModelResponse(parts=[TextPart("The current source could not be verified; no edit was made.")])
        content = (
            "def apply_discount(price: float, percent: float) -> float:\n"
            "    return price * (1 - percent / 100)\n"
        )
        return ModelResponse(parts=[ToolCallPart("write_file", {
            "path": "discount.py", "content": content, "expected_hash": match.group(1),
        })])
    if "run_command" not in returned_names:
        command = (
            "python -m unittest -q"
        )
        return ModelResponse(
            parts=[ToolCallPart("run_command", {"command": command, "timeout_seconds": 20})]
        )
    if "OK" in str(tool_returns[-1].content):
        return ModelResponse(parts=[TextPart("The discount calculation is fixed and its tests pass.")])
    return ModelResponse(parts=[TextPart("The command did not report passing tests.")])


def main() -> None:
    # The runner is attached only to the isolated operator network. Workspace and
    # database names must not resolve from this candidate-facing network.
    for forbidden in ("workspace-amber", "workspace-cobalt", "postgres"):
        try:
            socket.getaddrinfo(forbidden, None)
        except socket.gaierror:
            continue
        raise AssertionError(f"candidate network unexpectedly resolves {forbidden}")

    task = call("POST", "/v1/tasks", {"goal": "Fix the synthetic discount calculator and run its tests."})
    task_id = task["task_id"]
    workspace = HadesGatewayWorkspace(GATEWAY_URL, TOKEN, task_id)
    agent = Agent(
        FunctionModel(scripted_model, model_name="strict-hades-a2-peer"),
        capabilities=[
            Shell(tools=["run_command"], default_timeout=20),
            FileSystem(root_dir="/workspace", tools=["read_file", "write_file"]),
        ],
    )
    run = agent.run_sync(
        "Make the requested correction in the existing synthetic repository and report the test result.",
        workspace=workspace,
    )
    assert "tests pass" in run.output
    assert MODEL_CALLS == 4, MODEL_CALLS

    before_oracle = call("GET", f"/v1/tasks/{task_id}")
    candidate_effects = before_oracle.get("effects", [])
    assert before_oracle["state"] == "RUNNING"
    assert len(candidate_effects) >= 2
    assert all(
        e["effect_kind"] == "WORKSPACE_COMMAND" and e["state"] == "CONFIRMED"
        for e in candidate_effects
    ), candidate_effects

    # Independent oracle: use a separate gateway call and inspect durable task/effect state.
    oracle = HadesGatewayWorkspace(GATEWAY_URL, TOKEN, task_id)
    verification = call("POST", "/v1/workspace/exec", {
        "task_id": task_id,
        "command": (
            "python -m unittest -q && git status --short --branch "
            "&& python -c \"from pathlib import Path; s=Path('discount.py').read_text(); "
            "assert '1 - percent / 100' in s and '1 + percent / 100' not in s; print('source_verified')\""
        ),
    })
    assert verification["state"] == "CONFIRMED", verification
    assert verification["exit_code"] == 0, verification
    assert "OK" in verification["stderr"]
    assert "source_verified" in verification["stdout"]
    state = call("GET", f"/v1/tasks/{task_id}")
    effects = state.get("effects", [])
    assert state["task_id"] == task_id
    assert state["state"] == "RUNNING"  # The probe did not assert task completion.
    assert len(effects) == len(candidate_effects) + 1, effects
    assert len({e["effect_id"] for e in effects}) == len(effects), effects
    assert all(e["effect_kind"] == "WORKSPACE_COMMAND" and e["state"] == "CONFIRMED" for e in effects), effects
    print(json.dumps({
        "evidence": "CONTRACT_TEST",
        "task_state": state["state"],
        "candidate_model_calls": MODEL_CALLS,
        "candidate_gateway_effects": len(candidate_effects),
        "hades_workspace_effects": len(effects),
        "all_effects_confirmed": True,
        "independent_test_and_source_check": "passed",
        "answer_correct": "tests pass" in run.output,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
