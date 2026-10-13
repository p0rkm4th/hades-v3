#!/usr/bin/env python3
"""Install or remove a checkpoint-scoped temporary IPv4 egress guard."""
import argparse
import ipaddress
import subprocess
import sys

def chain_names(checkpoint):
    if checkpoint not in {"CP67", "CP68", "CP71"}:
        raise ValueError("unsupported checkpoint")
    return f"H3{checkpoint}FWD", f"H3{checkpoint}IN"


def run(*args, check=True):
    return subprocess.run(["iptables", "-w", "3", *args], check=check,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def exists(chain):
    return run("-S", chain, check=False).returncode == 0


def install(adapter_ip, upstream_ip, port, forward_chain, input_chain):
    if not exists("DOCKER-USER"):
        raise RuntimeError("Docker DOCKER-USER chain is unavailable")
    if exists(forward_chain) or exists(input_chain):
        raise RuntimeError("checkpoint firewall chain already exists; inspect before proceeding")
    run("-N", forward_chain)
    run("-N", input_chain)
    try:
        run("-A", forward_chain, "-d", f"{upstream_ip}/32", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT")
        run("-A", forward_chain, "-s", f"{adapter_ip}/32", "-j", "DROP")
        run("-A", input_chain, "-s", f"{adapter_ip}/32", "-j", "DROP")
        run("-I", "DOCKER-USER", "1", "-s", f"{adapter_ip}/32", "-j", forward_chain)
        run("-I", "INPUT", "1", "-s", f"{adapter_ip}/32", "-j", input_chain)
    except Exception:
        rollback(adapter_ip, forward_chain, input_chain)
        raise
    print("temporary host egress guard installed")


def rollback(adapter_ip, forward_chain, input_chain):
    adapter = f"{adapter_ip}/32"
    run("-D", "DOCKER-USER", "-s", adapter, "-j", forward_chain, check=False)
    run("-D", "INPUT", "-s", adapter, "-j", input_chain, check=False)
    for chain in (forward_chain, input_chain):
        if exists(chain):
            run("-F", chain)
            run("-X", chain)
    print("temporary host egress guard removed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "rollback"))
    parser.add_argument("--adapter-ip", required=True)
    parser.add_argument("--checkpoint", choices=("CP67", "CP68", "CP71"), default="CP67")
    parser.add_argument("--upstream-ip")
    parser.add_argument("--port", type=int, default=11434)
    args = parser.parse_args()
    forward_chain, input_chain = chain_names(args.checkpoint)
    adapter_ip = str(ipaddress.IPv4Address(args.adapter_ip))
    if args.action == "install":
        if args.upstream_ip is None or not 1 <= args.port <= 65535:
            parser.error("install requires a valid --upstream-ip and --port")
        install(adapter_ip, str(ipaddress.IPv4Address(args.upstream_ip)), args.port,
                forward_chain, input_chain)
    else:
        rollback(adapter_ip, forward_chain, input_chain)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as exc:
        print(f"firewall operation failed: {exc}", file=sys.stderr)
        sys.exit(1)
