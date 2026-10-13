#!/usr/bin/env python3
"""Install or remove CP67's temporary IPv4 egress guard using host iptables."""
import argparse
import ipaddress
import subprocess
import sys

FORWARD_CHAIN = "HADES3GPUFWD"
INPUT_CHAIN = "HADES3GPUIN"


def run(*args, check=True):
    return subprocess.run(["iptables", "-w", "3", *args], check=check,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def exists(chain):
    return run("-S", chain, check=False).returncode == 0


def install(adapter_ip, upstream_ip, port):
    if not exists("DOCKER-USER"):
        raise RuntimeError("Docker DOCKER-USER chain is unavailable")
    if exists(FORWARD_CHAIN) or exists(INPUT_CHAIN):
        raise RuntimeError("CP67 firewall chain already exists; inspect before proceeding")
    run("-N", FORWARD_CHAIN)
    run("-N", INPUT_CHAIN)
    try:
        run("-A", FORWARD_CHAIN, "-d", f"{upstream_ip}/32", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT")
        run("-A", FORWARD_CHAIN, "-s", f"{adapter_ip}/32", "-j", "DROP")
        run("-A", INPUT_CHAIN, "-s", f"{adapter_ip}/32", "-j", "DROP")
        run("-I", "DOCKER-USER", "1", "-s", f"{adapter_ip}/32", "-j", FORWARD_CHAIN)
        run("-I", "INPUT", "1", "-s", f"{adapter_ip}/32", "-j", INPUT_CHAIN)
    except Exception:
        rollback(adapter_ip)
        raise
    print("temporary CP67 host egress guard installed")


def rollback(adapter_ip):
    adapter = f"{adapter_ip}/32"
    run("-D", "DOCKER-USER", "-s", adapter, "-j", FORWARD_CHAIN, check=False)
    run("-D", "INPUT", "-s", adapter, "-j", INPUT_CHAIN, check=False)
    for chain in (FORWARD_CHAIN, INPUT_CHAIN):
        if exists(chain):
            run("-F", chain)
            run("-X", chain)
    print("temporary CP67 host egress guard removed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "rollback"))
    parser.add_argument("--adapter-ip", required=True)
    parser.add_argument("--upstream-ip")
    parser.add_argument("--port", type=int, default=11434)
    args = parser.parse_args()
    adapter_ip = str(ipaddress.IPv4Address(args.adapter_ip))
    if args.action == "install":
        if args.upstream_ip is None or not 1 <= args.port <= 65535:
            parser.error("install requires a valid --upstream-ip and --port")
        install(adapter_ip, str(ipaddress.IPv4Address(args.upstream_ip)), args.port)
    else:
        rollback(adapter_ip)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as exc:
        print(f"firewall operation failed: {exc}", file=sys.stderr)
        sys.exit(1)
