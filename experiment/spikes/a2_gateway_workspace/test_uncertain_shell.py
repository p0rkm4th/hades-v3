import json
import unittest
from unittest.mock import patch

from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness import Shell
from pydantic_ai.workspaces import WorkspaceUnavailableError
import probe
from gateway_workspace import HadesGatewayWorkspace
from operation_identity import HadesOperationIdentity


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
    def test_shell_only_aborts_after_one_quarantined_command_without_retry(self):
        previous_profile = probe.TOOL_PROFILE
        previous_calls = probe.MODEL_CALLS
        probe.TOOL_PROFILE = "shell_only"
        probe.MODEL_CALLS = 0
        opener = CountingOpener()
        workspace = HadesGatewayWorkspace("http://unused", "fixture-token", "task-id")
        agent = Agent(
            FunctionModel(probe.scripted_model, model_name="strict-hades-a2-peer"),
            capabilities=[
                Shell(tools=["run_command"], default_timeout=20),
                HadesOperationIdentity(),
            ],
        )
        model_calls = None
        try:
            with patch("gateway_workspace.urllib.request.build_opener", return_value=opener):
                with self.assertRaises(WorkspaceUnavailableError):
                    agent.run_sync(probe.TASK_WORDING, workspace=workspace)
            model_calls = probe.MODEL_CALLS
        finally:
            probe.TOOL_PROFILE = previous_profile
            probe.MODEL_CALLS = previous_calls

        self.assertEqual(opener.calls, 1)
        self.assertEqual(model_calls, 1)


if __name__ == "__main__":
    unittest.main()
