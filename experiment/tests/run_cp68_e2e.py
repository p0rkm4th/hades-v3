"""Run three repeated full-runtime CP69 trials against the strict Ollama peer."""
from __future__ import annotations

import hashlib
import json
import os
import time
import argparse
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

import psycopg

API = os.environ["CANDIDATE_API_URL"]
GATEWAY = os.environ["GATEWAY_URL"]
DATABASE_URL = os.environ["DATABASE_URL"]
SCRIPTED_STATE = "http://cp68-scripted-ollama:11434/__test/state"
PROMPT = (
    "Read the synthetic infrastructure observations. Report the synthetic router's "
    "observed state and health, and report the backup and lab host states honestly. "
    "Do not infer health where no value was observed."
)
EXPECTED_TOOL = ["infrastructure_read"]
CASES = [("pydantic", "pydantic"), ("hermes", "hermes"), ("lean", "lean")]


def get_json(url, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def post_json(url, payload, timeout=240):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def memory_counts():
    with psycopg.connect(DATABASE_URL) as conn:
        return dict(conn.execute(
            "SELECT user_id, count(*) FROM scoped_memory GROUP BY user_id"
        ).fetchall())


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", nargs="+", choices=[name for name, _ in CASES], default=[name for name, _ in CASES])
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 3:
        parser.error("repetitions must be between 1 and 3")
    cases = [(name, harness) for name, harness in CASES if name in args.candidates]
    memory_before = memory_counts()
    results = []
    for candidate, harness in cases:
        user_token = "fixture-token-amber"
        for repetition in range(1, args.repetitions + 1):
            prior = get_json(SCRIPTED_STATE)["attempts"]
            payload = {
                "candidate": candidate,
                "user_token": user_token,
                "messages": [{"role": "user", "content": PROMPT}],
            }
            started = time.monotonic()
            status, response = post_json(API, payload)
            latency_ms = round((time.monotonic() - started) * 1000)
            check(status == 200, f"{candidate} trial {repetition} candidate response status {status}")
            task_id = response.get("task_id")
            check(bool(task_id), f"{candidate} trial {repetition} omitted task id")
            check(response.get("tool_calls") == EXPECTED_TOOL,
                  f"{candidate} trial {repetition} tool trace was {response.get('tool_calls')!r}")
            answer = (response.get("text") or "").casefold()
            for phrase in ("synthetic router", "fresh", "health ok", "synthetic backup", "stale",
                           "synthetic lab host", "unknown", "no health value"):
                check(phrase in answer, f"{candidate} trial {repetition} answer omitted {phrase!r}")

            task = get_json(f"{GATEWAY}/v1/tasks/{urllib.parse.quote(task_id, safe='')}", user_token)
            check(task.get("state") == "COMPLETED",
                  f"{candidate} trial {repetition} durable state {task.get('state')!r}")
            check(task.get("effects") == [], f"{candidate} trial {repetition} has effects")
            check(response.get("task_state") == "COMPLETED",
                  f"{candidate} trial {repetition} returned stale task state")

            attempts = get_json(SCRIPTED_STATE)["attempts"][len(prior):]
            own = [attempt for attempt in attempts if attempt["harness"] == harness]
            expected_stages = (["tool_search", "tool_dispatch", "answer"] if candidate == "hermes"
                               else ["tool_request", "answer"])
            check(len(own) == len(expected_stages),
                  f"{candidate} trial {repetition} used unexplained model generations: {len(own)}")
            check([attempt["stage"] for attempt in own] == expected_stages,
                  f"{candidate} trial {repetition} generation stages were {[a['stage'] for a in own]!r}")
            first_tools = own[0]["available_tools"]
            expected_model_tool = "tool_search" if candidate == "hermes" else "infrastructure_read"
            check(first_tools.count(expected_model_tool) == 1,
                  f"{candidate} trial {repetition} model lacked the expected tool")
            check(all(attempt.get("configuration_matches") is True for attempt in own),
                  f"{candidate} trial {repetition} inference configuration drifted")
            check(all(attempt.get("native_history_valid") is True for attempt in own),
                  f"{candidate} trial {repetition} emitted non-native Ollama tool history")
            check(all(attempt.get("native_tools_valid") is True for attempt in own),
                  f"{candidate} trial {repetition} emitted non-native Ollama tool declarations")
            observation_generation = own[-1]
            check(observation_generation["genuine_observation_received"] is True,
                  f"{candidate} trial {repetition} final generation did not receive the gateway observation")
            check(len(observation_generation["observation_sha256"]) == 64,
                  f"{candidate} trial {repetition} observation digest is invalid")
            if candidate == "hermes":
                selected = own[1].get("selected_tool", "")
                check(selected.endswith("__infrastructure_read"),
                      f"Hermes selected the wrong deferred tool {selected!r}")
            results.append({
                "candidate": candidate, "harness": harness, "repetition": repetition,
                "task_id": task_id, "task_state": task["state"], "tool_trace": response["tool_calls"],
                "answer": response["text"], "generation_count": len(own), "latency_ms": latency_ms,
                "effects": len(task["effects"]),
                "observation_sha256": observation_generation["observation_sha256"],
                "model": "cp68-scripted-model", "effective_context": 65536,
                "temperature": 0, "max_output_tokens": 1024,
                "usage": response.get("usage"),
                "protocol_peer": "strict-native-ollama",
                "native_history_valid": all(attempt.get("native_history_valid") is True for attempt in own),
                "native_tools_valid": all(attempt.get("native_tools_valid") is True for attempt in own),
                "stages": [attempt["stage"] for attempt in own],
            })
            print(json.dumps(results[-1], sort_keys=True), flush=True)

    check(memory_counts() == memory_before, "synthetic memory rows changed during read-only trials")
    check(len(results) == args.repetitions * len(cases), "not all requested trial records completed")
    print(json.dumps({"checkpoint": "CP69_OFFLINE_E2E", "trials": len(results),
                      "candidates": {candidate: args.repetitions for candidate, _ in cases},
                      "all_completed": True, "memory_rows_unchanged": True}, sort_keys=True), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as output:
            for result in results:
                output.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
            output.write(json.dumps({"checkpoint": "CP69_OFFLINE_E2E", "trials": len(results),
                                     "candidates": {candidate: args.repetitions for candidate, _ in cases},
                                     "all_completed": True, "memory_rows_unchanged": True},
                                    sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
