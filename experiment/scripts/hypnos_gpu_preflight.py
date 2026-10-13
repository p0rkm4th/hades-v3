#!/usr/bin/env python3
"""Read-only Hypnos Ollama preflight using the documented user service.

The SSH target and key are supplied locally. The Hypnos serving address is
discovered from the effective environment of ollama-hades.service and is
never printed by this tool.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit

SERVICE = "ollama-hades.service"
MODEL = "gemma4:12b"
EXPECTED_DIGEST = "4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c"
EXPECTED_API_VERSION = "0.31.1"
TIMEOUT = 4


def parse_environment(value):
    """Parse systemd's Environment property without emitting its contents."""
    result = {}
    for item in shlex.split(value or ""):
        if "=" in item:
            key, val = item.split("=", 1)
            result[key] = val
    return result


def configured_url(bind):
    """Convert OLLAMA_HOST into a probe URL; reject ambiguous/wildcard binds."""
    if not isinstance(bind, str) or not bind.strip():
        raise ValueError("OLLAMA_HOST is absent")
    value = bind.strip()
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme != "http" or not parsed.hostname or parsed.path not in ("", "/"):
            raise ValueError("OLLAMA_HOST is not a plain HTTP listener")
        host, port = parsed.hostname, parsed.port or 11434
    else:
        if value.startswith("["):
            end = value.find("]")
            if end < 0:
                raise ValueError("OLLAMA_HOST IPv6 binding is malformed")
            host = value[1:end]
            port = int(value[end + 2:]) if value[end + 1:].startswith(":") else 11434
        else:
            host, sep, port_text = value.rpartition(":")
            if not sep:
                host, port = value, 11434
            else:
                port = int(port_text)
        if host in ("", "0.0.0.0", "::", "*"):
            raise ValueError("OLLAMA_HOST is a wildcard and cannot identify a probe destination")
    if not 1 <= int(port) <= 65535:
        raise ValueError("OLLAMA_HOST port is invalid")
    return f"http://{host}:{int(port)}"


def inspect_payload(unit, api, expected_digest=EXPECTED_DIGEST):
    """Validate service, listener, installed/resident state, and context."""
    required = {"ActiveState": "active", "SubState": "running", "UnitFileState": "enabled"}
    for field, expected in required.items():
        if unit.get(field) != expected:
            raise RuntimeError(f"user service {field} is not {expected}")
    env = parse_environment(unit.get("Environment", ""))
    base = configured_url(env.get("OLLAMA_HOST"))
    if urlsplit(base).port != 11434:
        raise RuntimeError("serving port differs from the approved profile")
    version = api("/api/version")
    if version.get("version") != EXPECTED_API_VERSION:
        raise RuntimeError("Ollama API version differs from the approved profile")
    tags = api("/api/tags")
    ps = api("/api/ps")
    models = tags.get("models") if isinstance(tags, dict) else None
    matches = [m for m in models or [] if m.get("name") == MODEL or m.get("model") == MODEL]
    if len(matches) != 1 or matches[0].get("digest") != expected_digest:
        raise RuntimeError("approved model is absent or its digest differs")
    show = api("/api/show", {"name": MODEL})
    details = show.get("details", {})
    if details.get("quantization_level") != "Q4_K_M":
        raise RuntimeError("approved model quantization differs")
    resident = ps.get("models", []) if isinstance(ps, dict) else None
    loaded = [m for m in resident or [] if m.get("name") == MODEL or m.get("model") == MODEL]
    if len(loaded) > 1:
        raise RuntimeError("approved model has ambiguous residency records")
    state = "loaded" if loaded else "installed_but_unloaded"
    effective_context = loaded[0].get("context_length") if loaded else None
    return {"service": "healthy", "listener": "available", "api_version": version.get("version"),
            "model": state, "effective_context": effective_context,
            "context_status": "verified" if effective_context == 65536 else
            ("mismatch" if effective_context is not None else "requires_bounded_probe"),
            "configured_base": base}


def validate_runtime_config(unit_env, process_env, process_owner, gpu_status_valid):
    """Reject changes between the managed unit and live server configuration."""
    expected = {"OLLAMA_CONTEXT_LENGTH": "65536", "OLLAMA_NUM_PARALLEL": "1",
                "OLLAMA_MAX_LOADED_MODELS": "1", "CUDA_VISIBLE_DEVICES": "0,1",
                "OLLAMA_LLM_LIBRARY": "cuda_v12", "OLLAMA_KEEP_ALIVE": "30m"}
    if process_owner != "scotty":
        raise RuntimeError("serving process owner differs from the approved account")
    if not gpu_status_valid:
        raise RuntimeError("expected two healthy NVIDIA devices were not verified")
    for key, value in expected.items():
        if unit_env.get(key) != value or process_env.get(key) != value:
            raise RuntimeError("serving configuration drift detected")
    for key in ("OLLAMA_HOST", "OLLAMA_MODELS"):
        if not unit_env.get(key) or unit_env.get(key) != process_env.get(key):
            raise RuntimeError("serving configuration differs from its supervised unit")


REMOTE_PROBE = r'''import json, pwd, subprocess
u=pwd.getpwnam("scotty")
env={"PATH":"/usr/bin:/bin","HOME":u.pw_dir,"USER":"scotty","LOGNAME":"scotty",
     "XDG_RUNTIME_DIR":"/run/user/"+str(u.pw_uid),
     "DBUS_SESSION_BUS_ADDRESS":"unix:path=/run/user/"+str(u.pw_uid)+"/bus"}
p=subprocess.run(["runuser","-u","scotty","--","env",
 "XDG_RUNTIME_DIR="+env["XDG_RUNTIME_DIR"],
 "DBUS_SESSION_BUS_ADDRESS="+env["DBUS_SESSION_BUS_ADDRESS"],
 "systemctl","--user","show","ollama-hades.service",
 "-p","ActiveState","-p","SubState","-p","UnitFileState","-p","MainPID","-p","Environment"],
 text=True,capture_output=True,check=True)
d={}
for line in p.stdout.splitlines():
 k,sep,v=line.partition("=")
 if sep: d[k]=v
pid=int(d.get("MainPID","0"))
if pid:
 raw=open("/proc/%d/environ"%pid,"rb").read().split(b"\0")
 live={}
 for item in raw:
  k,sep,v=item.partition(b"=")
  if sep and k.decode(errors="ignore") in {"OLLAMA_HOST","OLLAMA_MODELS","CUDA_VISIBLE_DEVICES","OLLAMA_NUM_PARALLEL","OLLAMA_MAX_LOADED_MODELS","OLLAMA_CONTEXT_LENGTH","OLLAMA_LLM_LIBRARY","OLLAMA_KEEP_ALIVE"}:
   live[k.decode()]=v.decode(errors="replace")
 d["ProcessEnvironment"]=live
 d["ProcessOwner"]=subprocess.check_output(["ps","-o","user=","-p",str(pid)],text=True).strip()
gpu=subprocess.run(["nvidia-smi","--query-gpu=name,driver_version,utilization.gpu,memory.used,memory.total","--format=csv,noheader,nounits"],text=True,capture_output=True)
d["GPUStatusValid"]=gpu.returncode==0 and len(gpu.stdout.strip().splitlines())==2 and all("Quadro P4000" in row and "580.178.04" in row for row in gpu.stdout.splitlines())
print(json.dumps(d))
'''


def remote_state(host, key=None):
    cmd = ["ssh"]
    if key:
        cmd.extend(["-i", key, "-o", "IdentitiesOnly=yes"])
    cmd.extend(["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "ConnectTimeout=5", f"codex@{host}", "sudo -n python3 -"])
    result = subprocess.run(cmd, input=REMOTE_PROBE, text=True, capture_output=True, timeout=12)
    if result.returncode:
        raise RuntimeError("strict SSH service inspection failed")
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", required=True, help="Hypnos target from the local infrastructure inventory")
    parser.add_argument("--ssh-key", default=os.environ.get("CODEX_HOMELAB_SSH_KEY"),
                        help="optional local break-glass key path; otherwise use the SSH agent")
    args = parser.parse_args()
    try:
        state = remote_state(args.ssh_host, os.path.expanduser(args.ssh_key) if args.ssh_key else None)
        unit = {key: state.get(key) for key in ("ActiveState", "SubState", "UnitFileState")}
        env = state.get("ProcessEnvironment") or {}
        unit_env = parse_environment(state.get("Environment", ""))
        if not env.get("OLLAMA_HOST"):
            raise RuntimeError("serving process has no OLLAMA_HOST")
        validate_runtime_config(unit_env, env, state.get("ProcessOwner"), state.get("GPUStatusValid"))
        unit["Environment"] = " ".join(shlex.quote(f"{key}={value}") for key, value in env.items())

        def api(path, body=None):
            base = configured_url(env["OLLAMA_HOST"])
            payload = None if body is None else json.dumps(body).encode()
            request = urllib.request.Request(base + path, data=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                method="GET" if body is None else "POST")
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=TIMEOUT) as response:
                return json.loads(response.read(1024 * 1024))

        report = inspect_payload(unit, api)
        report.pop("configured_base")
        report["status"] = ("ready" if report["context_status"] == "verified" else "ready_for_bounded_context_probe")
        if report["context_status"] == "mismatch":
            raise RuntimeError("effective serving context differs from the approved profile")
        report["manager"] = "scotty user systemd"
        report["unit"] = SERVICE
        report["process_owner"] = state.get("ProcessOwner")
        report["gpu_status"] = "healthy"
        report["model_dir_configured"] = bool(env.get("OLLAMA_MODELS"))
        print(json.dumps(report, sort_keys=True))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        diagnostic = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "bounded service probe failed"
        print(json.dumps({"status": "blocked", "diagnostic": diagnostic}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
