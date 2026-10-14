import json
import unittest
from unittest.mock import patch

from pydantic_ai import Agent
from pydantic_ai.messages import RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness import Shell
import probe
from gateway_workspace import HadesGatewayWorkspace


class QuarantinedResponse:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"state": "QUARANTINED", "inspection_required": True}).encode()


class CountingOpener:
    def __init__(self):
        self.calls = 0

    def open(self, _request, timeout):
        self.calls += 1
        if timeout != 25:
            raise AssertionError("workspace request timeout changed")
        return QuarantinedResponse()


class UncertainShellRecoveryTests(unittest.TestCase):
    def test_shell_only_stops_after_one_quarantined_command(self):
        previous_profile = probe.TOOL_PROFILE
        previous_calls = probe.MODEL_CALLS
        probe.TOOL_PROFILE = "shell_only"
        probe.MODEL_CALLS = 0
        opener = CountingOpener()
        workspace = HadesGatewayWorkspace("http://unused", "fixture-token", "task-id")
        agent = Agent(
            FunctionModel(probe.scripted_model, model_name="strict-hades-a2-peer"),
            capabilities=[Shell(tools=["run_command"], default_timeout=20)],
        )
        try:
            with patch("gateway_workspace.urllib.request.build_opener", return_value=opener):
                result = agent.run_sync(probe.TASK_WORDING, workspace=workspace)
        finally:
            probe.TOOL_PROFILE = previous_profile
            probe.MODEL_CALLS = previous_calls

        self.assertEqual(opener.calls, 1)
        self.assertEqual(probe.MODEL_CALLS, 2)
        self.assertIn("uncertain", result.output.casefold())
        self.assertIn("without retrying", result.output.casefold())
        self.assertEqual(
            sum(isinstance(part, RetryPromptPart) for message in result.all_messages()
                for part in message.parts), 1,
        )
        self.assertEqual(
            sum(isinstance(part, ToolCallPart) for message in result.all_messages()
                for part in message.parts), 1,
        )


if __name__ == "__main__":
    unittest.main()
