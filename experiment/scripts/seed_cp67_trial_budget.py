#!/usr/bin/env python3
"""Initialize CP67's durable per-harness generation budget before adapter start."""
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--deadline-epoch", required=True, type=float)
parser.add_argument("--pydantic-used", type=int, default=0)
parser.add_argument("--hermes-used", type=int, default=0)
parser.add_argument("--lean-used", type=int, default=0)
parser.add_argument("--state", default="/state/budget.json")
args = parser.parse_args()
counts = {"pydantic": args.pydantic_used, "hermes": args.hermes_used, "lean": args.lean_used}
if any(value < 0 or value > 2 for value in counts.values()) or sum(counts.values()) > 6:
    parser.error("generation counts exceed the authorized trial limit")
state = Path(args.state)
if state.exists():
    parser.error("budget state already exists; refusing to reset counters")
state.write_text(json.dumps({"deadline_epoch": args.deadline_epoch,
                             "generation_counts": counts}, sort_keys=True), encoding="utf-8")
state.chmod(0o600)
os.chown(state, 10001, 10001)
os.chown(state.parent, 10001, 10001)
print("CP67 budget initialized")
