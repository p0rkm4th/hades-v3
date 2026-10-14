import hashlib
import json
import unittest
import urllib.error
import urllib.request


BASE = "http://tool-gateway:8080"
AMBER = "fixture-token-amber"
COBALT = "fixture-token-cobalt"


def call(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


class WorkspaceFlow(unittest.TestCase):
    def setUp(self):
        self.call_index = 0

    def exec_command(self, token, task_id, command):
        self.call_index += 1
        operation_id = hashlib.sha256(
            f"{task_id}:workspace-flow:{self.call_index}".encode()
        ).hexdigest()
        status, result = call("POST", "/v1/workspace/exec", token, {
            "task_id": task_id, "command": command, "operation_id": operation_id,
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["state"], "CONFIRMED")
        self.assertFalse(result["timed_out"])
        return result

    def test_real_shell_git_test_and_per_user_workspace_isolation(self):
        status, task = call("POST", "/v1/tasks", AMBER, {
            "goal": "fix the synthetic discount calculation and verify it",
        })
        self.assertEqual(status, 201, task)
        amber_task = task["task_id"]

        initial = self.exec_command(AMBER, amber_task, "git status --short --branch")
        self.assertEqual(initial["exit_code"], 0)
        self.assertIn("## main", initial["stdout"])

        failing = self.exec_command(AMBER, amber_task, "python -m unittest -v")
        self.assertNotEqual(failing["exit_code"], 0)
        self.assertIn("FAILED", failing["stderr"])

        repair = (
            "python -c \"from pathlib import Path; p=Path('discount.py'); "
            "s=p.read_text(); old='1 + percent / 100'; assert old in s; "
            "p.write_text(s.replace(old, '1 - percent / 100'))\""
        )
        fixed = self.exec_command(AMBER, amber_task, repair)
        self.assertEqual(fixed["exit_code"], 0, fixed)

        passing = self.exec_command(AMBER, amber_task, "python -m unittest -v")
        self.assertEqual(passing["exit_code"], 0, passing)
        self.assertIn("Ran 3 tests", passing["stderr"])
        self.assertIn("OK", passing["stderr"])

        committed = self.exec_command(
            AMBER, amber_task,
            "git add discount.py && git commit -m 'Fix discount calculation'",
        )
        self.assertEqual(committed["exit_code"], 0, committed)
        git_state = self.exec_command(AMBER, amber_task, "git status --short --branch")
        self.assertEqual(git_state["stdout"].strip(), "## main")
        latest = self.exec_command(AMBER, amber_task, "git log -1 --format=%s")
        self.assertEqual(latest["stdout"].strip(), "Fix discount calculation")
        isolation = self.exec_command(
            AMBER, amber_task,
            "python - <<'PY'\n"
            "import socket\n"
            "try:\n"
            "    socket.getaddrinfo('workspace-cobalt', 8091)\n"
            "except socket.gaierror:\n"
            "    print('isolated')\n"
            "else:\n"
            "    raise SystemExit(1)\n"
            "PY",
        )
        self.assertEqual(isolation["stdout"].strip(), "isolated")

        status, cobalt = call("POST", "/v1/tasks", COBALT, {
            "goal": "verify an isolated synthetic workspace",
        })
        self.assertEqual(status, 201, cobalt)
        cobalt_status = self.exec_command(COBALT, cobalt["task_id"], "git status --short --branch")
        self.assertEqual(cobalt_status["exit_code"], 0)
        self.assertEqual(cobalt_status["stdout"].strip(), "## main")
        cobalt_test = self.exec_command(COBALT, cobalt["task_id"], "python -m unittest -q")
        self.assertNotEqual(cobalt_test["exit_code"], 0)
        self.assertIn("FAILED", cobalt_test["stderr"])
        reverse_isolation = self.exec_command(
            COBALT, cobalt["task_id"],
            "python - <<'PY'\n"
            "import socket\n"
            "try:\n"
            "    socket.getaddrinfo('workspace-amber', 8091)\n"
            "except socket.gaierror:\n"
            "    print('isolated')\n"
            "else:\n"
            "    raise SystemExit(1)\n"
            "PY",
        )
        self.assertEqual(reverse_isolation["stdout"].strip(), "isolated")


if __name__ == "__main__":
    unittest.main()
