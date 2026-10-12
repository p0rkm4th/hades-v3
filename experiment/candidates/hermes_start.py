from pathlib import Path
import base64
import hashlib
import os
import secrets


def dashboard_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$%s$%s" % (
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


home = Path(os.environ.get("HERMES_HOME", str(Path(os.environ.get("HOME", "/home/hermes")) / ".hermes")))
home.mkdir(mode=0o700, parents=True, exist_ok=True)
template = (Path(__file__).parent / "hermes_config.yaml.in").read_text()
values = {
    "__MODEL_NAME__": os.environ.get("MODEL_NAME", "Qwen3-8B"),
    "__MODEL_URL__": os.environ.get("MODEL_URL", "http://model-server-8b:8080/v1"),
    "__MODEL_CONTEXT_LENGTH__": os.environ.get("MODEL_CONTEXT_LENGTH", "40960"),
    "__USER_TOKEN__": os.environ["HADES_USER_TOKEN"],
    "__TASK_FILE__": os.environ["HADES_TASK_FILE"],
    "__TRACE_FILE__": os.environ["HADES_TRACE_FILE"],
    "__DASHBOARD_PASSWORD_HASH__": dashboard_hash(os.environ["DASHBOARD_PASSWORD"]),
}
for key, value in values.items():
    template = template.replace(key, value)
(home / "config.yaml").write_text(template)
python = "/opt/hermes/.venv/bin/python"
os.execv(python, [
    python, "/opt/hermes/hermes", "gateway", "run", "--no-supervise",
])
