"""Exercise DBOS recovery through the candidate API's trusted finalizer.

All model behavior is a deterministic Pydantic FunctionModel. The gateway,
task/effect ledger, workspace runner, A tool adapter, and finalizer are real.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from dbos import DBOS, SetWorkflowID
from pydantic_ai import Agent, FunctionToolset, RunContext, Tool, UsageLimits
from pydantic_ai.durable_exec.dbos import DBOSDurability
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

import api


TOKEN = os.environ.get("HADES_USER_TOKEN", "fixture-token-amber")
STATE = Path(os.environ.get("CP84_STATE_DIR", "/tmp/cp84"))
STATE.mkdir(parents=True, exist_ok=True)
PROMPT = "Create one synthetic marker in the assigned workspace and report its verified result."


@dataclass
class TurnDeps:
    task_id: str
    evidence: list[dict] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


def _write_generation(run_id: str) -> None:
    with (STATE / "model-calls.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(run_id + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _make_toolset():
    toolset = FunctionToolset(id="cp84-hades-gateway-tools")
    for spec in api.VISIBLE_TOOLS:
        name = spec["name"]

        def invoke(ctx: RunContext[TurnDeps], _name=name, **kwargs):
            ctx.deps.tools.append(_name)
            return api.gateway_call(
                _name, kwargs, TOKEN, ctx.deps.task_id, ctx.deps.evidence,
                tool_call_id=ctx.tool_call_id,
            )

        toolset.add_tool(Tool.from_schema(
            function=invoke,
            name=name,
            description=spec["description"],
            json_schema=spec["parameters"],
            takes_ctx=True,
        ))
    return toolset


def _build_agent(run_id: str) -> Agent[TurnDeps, str]:
    def model(messages, info):
        _write_generation(run_id)
        returns = [
            part for message in messages for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            tool = next(item for item in info.function_tools if item.name == "workspace_exec")
            marker = f".cp84-marker-{run_id}.txt"
            command = (
                "python -c \"from pathlib import Path; p=Path('" + marker + "'); "
                "p.write_text((p.read_text() if p.exists() else '') + 'x'); "
                "print('marker recorded')\""
            )
            return ModelResponse(parts=[ToolCallPart(tool.name, {
                "command": command,
            }, tool_call_id="cp84-workspace-call")])

        if not any(isinstance(part, ToolReturnPart) and part.tool_name == "task_checkpoint"
                   for message in messages for part in message.parts):
            tool = next(item for item in info.function_tools if item.name == "task_checkpoint")
            return ModelResponse(parts=[ToolCallPart(tool.name, {
                "state": "COMPLETED",
                "checkpoint": {
                    "summary": "Verified the requested synthetic marker operation.",
                    "completed": ["Create and verify one marker"],
                    "pending": [],
                },
            }, tool_call_id="cp84-completion-call")])

        observed = str(returns[0].content)
        if "marker recorded" not in observed:
            return ModelResponse(parts=[TextPart("The marker was not confirmed.")])
        return ModelResponse(parts=[TextPart("The synthetic marker was recorded successfully.")])

    return Agent(
        FunctionModel(model, model_name="cp84-strict-peer"),
        name="cp84-hades-candidate-a",
        deps_type=TurnDeps,
        system_prompt=api.SYSTEM_PROMPT,
        toolsets=[_make_toolset()],
        capabilities=[DBOSDurability(parallel_execution_mode="sequential")],
        retries=0,
    )


def _child(mode: str, task_id: str, run_id: str) -> int:
    db_path = STATE / "dbos.sqlite"
    DBOS(config={
        "name": "hades_cp84_candidate_finalization",
        "application_version": "1",
        "system_database_url": f"sqlite:///{db_path}",
    })
    agent = _build_agent(run_id)

    @DBOS.workflow()
    async def candidate_turn(workspace_task_id: str) -> dict:
        deps = TurnDeps(task_id=workspace_task_id)
        result = await agent.run(
            PROMPT,
            deps=deps,
            model_settings={"temperature": 0, "max_tokens": 256},
            usage_limits=UsageLimits(request_limit=3, tool_calls_limit=2),
        )
        usage = result.usage
        return {
            "text": str(result.output),
            "tool_calls": deps.tools,
            "tool_evidence": deps.evidence,
            "usage": {
                "prompt_tokens": usage.input_tokens,
                "completion_tokens": usage.output_tokens,
            },
            "model_generations": usage.requests,
        }

    DBOS.launch()
    if mode in {"crash_after_tool", "crash_before_finalize"}:
        if mode == "crash_after_tool":
            original = api.gateway_call

            def crashing(*args, **kwargs):
                observation = original(*args, **kwargs)
                if (args and args[0] == "workspace_exec"
                        and observation.get("state") == "CONFIRMED"):
                    os._exit(78)
                return observation

            api.gateway_call = crashing
        with SetWorkflowID(run_id):
            result = asyncio.run(candidate_turn(task_id))
        if mode == "crash_before_finalize":
            assert result.get("text"), result
            os._exit(79)
        raise RuntimeError("fault injection did not terminate the worker")

    result = DBOS.get_result(run_id)
    finalized = api.finalize_turn(TOKEN, task_id, result)
    print("CP84_RESULT:" + json.dumps({
        "result": result,
        "task_state": finalized.get("state"),
        "checkpoint": finalized.get("checkpoint"),
    }, sort_keys=True), flush=True)
    DBOS.destroy()
    return 0


def _run_child(mode: str, task_id: str, run_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", mode, task_id, run_id],
        env=os.environ.copy(), capture_output=True, text=True, timeout=90, check=False,
    )


def _gateway_call(name: str, args: dict, task_id: str, call_id: str):
    return api.gateway_call(name, args, TOKEN, task_id, tool_call_id=call_id)


def main() -> None:
    if len(sys.argv) == 5 and sys.argv[1] == "--child":
        raise SystemExit(_child(sys.argv[2], sys.argv[3], sys.argv[4]))

    api.ORCHESTRATOR_SECRET = os.environ["ORCHESTRATOR_SECRET"]
    if len(sys.argv) == 4 and sys.argv[1] == "--inspect-cleanup":
        task_id, run_id = sys.argv[2], sys.argv[3]
        task = api.gateway_call("task_resume", {}, TOKEN, task_id)
        assert task.get("state") in {"RUNNING", "COMPLETED"} and len(task.get("effects", [])) == 1, task
        effect = task["effects"][0]
        assert effect["state"] == "CONFIRMED", effect
        marker = f".cp84-marker-{run_id}.txt"
        observer = api.start_task(TOKEN, "Independently inspect the interrupted synthetic marker.")
        observed = _gateway_call(
            "workspace_exec",
            {"command": f"python -c \"from pathlib import Path; print(Path('{marker}').read_text())\""},
            observer["task_id"], "cp84-failed-trial-oracle-read",
        )
        assert observed["state"] == "CONFIRMED" and observed["stdout"] == "x\n", observed
        cleaner = api.start_task(TOKEN, "Remove the marker from the failed disposable trial.")
        cleanup = _gateway_call(
            "workspace_exec",
            {"command": f"python -c \"from pathlib import Path; Path('{marker}').unlink()\""},
            cleaner["task_id"], "cp84-failed-trial-cleanup",
        )
        assert cleanup["state"] == "CONFIRMED" and cleanup["exit_code"] == 0, cleanup
        print("CP84_INITIAL_FAILURE:" + json.dumps({
            "candidate_task_state": task["state"],
            "candidate_effect_state": effect["state"],
            "candidate_effect_id": effect["effect_id"],
            "independent_marker": observed["stdout"].strip(),
            "cleanup_exit_code": cleanup["exit_code"],
        }, sort_keys=True), flush=True)
        return

    # The runner has only the internal operator network: gateway DNS must work,
    # while backend/database aliases must remain unreachable from the candidate.
    assert api.GATEWAY == "http://tool-gateway:8080", api.GATEWAY
    for blocked_host in ("postgres", "workspace-amber", "workspace-cobalt", "grocy"):
        try:
            socket.getaddrinfo(blocked_host, None)
        except socket.gaierror:
            pass
        else:
            raise AssertionError(f"candidate can resolve backend-only host {blocked_host}")

    successes = []
    for _ in range(3):
        task = api.start_task(TOKEN, "Create one synthetic marker and report the verified result.")
        task_id = task["task_id"]
        run_id = f"cp84-task-{task_id}"
        marker = f".cp84-marker-{run_id}.txt"

        crash = _run_child("crash_after_tool", task_id, run_id)
        assert crash.returncode == 78, (crash.returncode, crash.stderr[-1200:])
        before = api.gateway_call("task_resume", {}, TOKEN, task_id)
        assert len(before["effects"]) == 1, before
        first_effect = before["effects"][0]
        assert first_effect["state"] == "CONFIRMED" and first_effect["operation_id"], before

        lost_delivery = _run_child("crash_before_finalize", task_id, run_id)
        assert lost_delivery.returncode == 79, (lost_delivery.returncode, lost_delivery.stderr[-1200:])
        still_running = api.gateway_call("task_resume", {}, TOKEN, task_id)
        assert still_running["state"] == "RUNNING", still_running
        assert still_running["effects"][0]["effect_id"] == first_effect["effect_id"]

        recovered = _run_child("resume", task_id, run_id)
        assert recovered.returncode == 0, recovered.stderr[-1600:]
        line = next((item for item in recovered.stdout.splitlines()
                     if item.startswith("CP84_RESULT:")), None)
        assert line, recovered.stdout[-1600:]
        result = json.loads(line[len("CP84_RESULT:"):])
        assert result["task_state"] == "COMPLETED", result
        assert result["result"]["text"] == "The synthetic marker was recorded successfully.", result
        assert result["result"]["model_generations"] == 3, result
        assert result["result"]["tool_calls"] == ["workspace_exec", "task_checkpoint"], result
        task_after = api.gateway_call("task_resume", {}, TOKEN, task_id)
        assert task_after["state"] == "COMPLETED", task_after
        assert task_after["effects"][0]["effect_id"] == first_effect["effect_id"]

        # An independent task performs the oracle read through the same gateway.
        observer = api.start_task(TOKEN, "Independently inspect the synthetic marker.")
        observed = _gateway_call(
            "workspace_exec",
            {"command": f"python -c \"from pathlib import Path; print(Path('{marker}').read_text())\""},
            observer["task_id"], "cp84-independent-read",
        )
        assert observed["state"] == "CONFIRMED" and observed["stdout"] == "x\n", observed

        repeated = _run_child("resume", task_id, run_id)
        assert repeated.returncode == 0, repeated.stderr[-1200:]
        repeat_line = next((item for item in repeated.stdout.splitlines()
                            if item.startswith("CP84_RESULT:")), None)
        assert repeat_line and json.loads(repeat_line[len("CP84_RESULT:"):])["result"] == result["result"]
        assert (STATE / "model-calls.jsonl").read_text().splitlines().count(run_id) == 3
        repeated_task = api.gateway_call("task_resume", {}, TOKEN, task_id)
        assert repeated_task["state"] == "COMPLETED"
        assert [e["effect_id"] for e in repeated_task["effects"]] == [first_effect["effect_id"]]
        successes.append({"task_id": task_id, "effect_id": first_effect["effect_id"],
                          "generations": 3, "task_state": "COMPLETED",
                          "marker_observation": observed["stdout"].strip()})

        cleanup_task = api.start_task(TOKEN, "Remove the synthetic marker after verification.")
        cleanup = _gateway_call(
            "workspace_exec",
            {"command": f"python -c \"from pathlib import Path; Path('{marker}').unlink()\""},
            cleanup_task["task_id"], "cp84-independent-cleanup",
        )
        assert cleanup["state"] == "CONFIRMED" and cleanup["exit_code"] == 0, cleanup

    print("PASS CP84 " + json.dumps(successes, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
