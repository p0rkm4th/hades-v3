from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore


FIXTURE_USER = os.environ["FIXTURE_USER"]
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/workspace")
MAX_BODY = 16 * 1024
MAX_COMMAND = 8 * 1024
MAX_OUTPUT = 256 * 1024
COMMAND_TIMEOUT = 20
CONCURRENCY = BoundedSemaphore(4)

SEED_FILES = {
    ".gitignore": "__pycache__/\n*.py[cod]\n",
    "README.md": "# Synthetic discount calculator\n\nRun checks with `python -m unittest -v`.\n",
    "discount.py": (
        "def apply_discount(price: float, percent: float) -> float:\n"
        "    return price * (1 + percent / 100)\n"
    ),
    "test_discount.py": (
        "import unittest\n\n"
        "from discount import apply_discount\n\n\n"
        "class DiscountTests(unittest.TestCase):\n"
        "    def test_ten_percent_off(self):\n"
        "        self.assertEqual(apply_discount(100, 10), 90)\n\n"
        "    def test_zero_percent(self):\n"
        "        self.assertEqual(apply_discount(100, 0), 100)\n\n"
        "    def test_full_discount(self):\n"
        "        self.assertEqual(apply_discount(100, 100), 0)\n\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n"
    ),
}


def seed_repository():
    os.makedirs(WORKSPACE_ROOT, mode=0o700, exist_ok=True)
    if os.path.isdir(os.path.join(WORKSPACE_ROOT, ".git")):
        return
    for name, content in SEED_FILES.items():
        path = os.path.join(WORKSPACE_ROOT, name)
        with open(path, "w", encoding="utf-8") as destination:
            destination.write(content)
    env = command_environment()
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=WORKSPACE_ROOT,
                   env=env, check=True, timeout=5)
    subprocess.run(["git", "add", ".gitignore", "README.md", "discount.py", "test_discount.py"],
                   cwd=WORKSPACE_ROOT, env=env, check=True, timeout=5)
    subprocess.run(["git", "commit", "--quiet", "-m", "Seed synthetic discount task"],
                   cwd=WORKSPACE_ROOT, env=env, check=True, timeout=5)


def command_environment():
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": WORKSPACE_ROOT,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Synthetic Fixture User",
        "GIT_AUTHOR_EMAIL": "fixture-user@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Fixture User",
        "GIT_COMMITTER_EMAIL": "fixture-user@example.invalid",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def run_command(command: str):
    started = time.monotonic()
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=WORKSPACE_ROOT,
            env=command_environment(),
            shell=True,
            executable="/bin/bash",
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
            close_fds=True,
        )
        timed_out = False
        try:
            exit_code = process.wait(timeout=COMMAND_TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=1)
            exit_code = process.returncode

        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read(MAX_OUTPUT + 1)
        stderr = stderr_file.read(MAX_OUTPUT + 1)
    return {
        "exit_code": exit_code,
        "stdout": stdout[:MAX_OUTPUT].decode("utf-8", errors="replace"),
        "stderr": stderr[:MAX_OUTPUT].decode("utf-8", errors="replace"),
        "stdout_truncated": len(stdout) > MAX_OUTPUT,
        "stderr_truncated": len(stderr) > MAX_OUTPUT,
        "timed_out": timed_out,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "HadesDisposableWorkspace/0.1"

    def log_message(self, fmt, *args):
        print(f"{self.log_date_time_string()} {self.command} {self.path.split('?')[0]}")

    def send_json(self, status, value):
        payload = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("request body too large")
        value = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def do_GET(self):
        if self.path != "/health":
            return self.send_json(404, {"error": "route not found"})
        return self.send_json(200, {"status": "ok", "fixture_user": FIXTURE_USER})

    def do_POST(self):
        if self.path != "/v1/exec":
            return self.send_json(404, {"error": "route not found"})
        try:
            body = self.read_json()
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "invalid request"})
        command = body.get("command")
        if not isinstance(command, str) or not command.strip() or len(command) > MAX_COMMAND:
            return self.send_json(400, {"error": "command must contain 1 to 8192 characters"})
        if not CONCURRENCY.acquire(blocking=False):
            return self.send_json(429, {"error": "workspace runner is busy"})
        try:
            result = run_command(command)
        except (OSError, subprocess.SubprocessError):
            return self.send_json(502, {"error": "workspace operation could not be completed"})
        finally:
            CONCURRENCY.release()
        return self.send_json(200, result)


def reset_workspace():
    shutil.rmtree(WORKSPACE_ROOT, ignore_errors=True)
    os.makedirs(WORKSPACE_ROOT, mode=0o700, exist_ok=True)
    seed_repository()
    print(f"Reset the synthetic repository for {FIXTURE_USER}.")


if __name__ == "__main__":
    if os.environ.get("WORKSPACE_RESET") == "1":
        reset_workspace()
    else:
        seed_repository()
        ThreadingHTTPServer(("0.0.0.0", 8091), Handler).serve_forever()
