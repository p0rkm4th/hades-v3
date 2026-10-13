#!/usr/bin/env python3
"""Initialize a durable per-harness generation budget before adapter start."""
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--deadline-epoch", required=True, type=float)
parser.add_argument("--limit-per-harness", type=int, default=2)
parser.add_argument("--limit-total", type=int, default=6)
parser.add_argument("--pydantic-used", type=int, default=0)
parser.add_argument("--hermes-used", type=int, default=0)
parser.add_argument("--lean-used", type=int, default=0)
parser.add_argument("--state", default="/state/budget.json")
args = parser.parse_args()
counts = {"pydantic": args.pydantic_used, "hermes": args.hermes_used, "lean": args.lean_used}
if (args.limit_per_harness < 1 or args.limit_total < 1
        or any(value < 0 or value > args.limit_per_harness for value in counts.values())
        or sum(counts.values()) > args.limit_total):
    parser.error("generation counts exceed the configured trial limit")
state = Path(args.state)
if state.exists():
    parser.error("budget state already exists; refusing to reset counters")
state.write_text(json.dumps({"deadline_epoch": args.deadline_epoch,
                             "generation_counts": counts}, sort_keys=True), encoding="utf-8")
state.chmod(0o600)
print("trial budget initialized")
