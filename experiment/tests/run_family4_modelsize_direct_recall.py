"""Matched one-turn direct-recall screen for A/C on the selected model profile."""

import argparse
import json
import time
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
MEMORY_KEY = "meeting_agenda_order"
MEMORY_VALUE = "updates, blockers, then decisions"
PROMPT = "What order did I choose for the monthly planning meeting agenda?"
ORDER = ("pydantic", "lean", "lean", "pydantic", "pydantic", "lean")


def request_json(method, url, payload=None, timeout=600):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.output, "w", encoding="utf-8") as output:
        for index, candidate in enumerate(ORDER, 1):
            seeded = request_json("POST", GATEWAY + "/v1/memory", {
                "key": MEMORY_KEY,
                "value": MEMORY_VALUE,
            }, timeout=40)
            assert seeded["value"] == MEMORY_VALUE, seeded
            started = time.monotonic()
            result = request_json("POST", CANDIDATE_API + "/api/turn", {
                "candidate": candidate,
                "user_token": TOKEN,
                "messages": [{"role": "user", "content": PROMPT}],
            })
            task = request_json("GET", GATEWAY + f"/v1/tasks/{result['task_id']}", timeout=40)
            record = {
                "profile": "Qwen3-14B-Q4_K_M-cpu-n_ctx40960",
                "candidate": candidate,
                "attempt": index,
                "task_id": result["task_id"],
                "task_state": task["state"],
                "tools": task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", []),
                "tool_evidence": result.get("tool_evidence", []),
                "usage": result.get("usage", {}),
                "duration_ms": result.get("duration_ms"),
                "wall_ms": round((time.monotonic() - started) * 1000),
                "text": result.get("text", ""),
            }
            line = json.dumps(record, ensure_ascii=False)
            print(line, flush=True)
            output.write(line + "\n")
            output.flush()
            if task["state"] != "COMPLETED":
                raise RuntimeError(f"candidate task failed: {result['task_id']}")
            time.sleep(1)


if __name__ == "__main__":
    main()
