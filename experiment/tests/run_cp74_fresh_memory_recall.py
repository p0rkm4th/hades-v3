"""Run one real fresh-context memory read for a candidate against the fixture."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request


GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
TOKEN = "fixture-token-amber"
PROMPT = (
    "What is currently saved as my answer style for synthetic lab status updates? "
    "Please retrieve the stored preference."
)


def get_json(path: str):
    req = urllib.request.Request(
        GATEWAY + path, headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("pydantic", "lean"), required=True)
    parser.add_argument("--memory-key", default="answer_style")
    parser.add_argument("--expected-style", required=True)
    args = parser.parse_args()
    memory_path = "/v1/memory/" + urllib.parse.quote(args.memory_key, safe="")
    before = get_json(memory_path)
    if before.get("value", {}).get("style") != args.expected_style:
        raise SystemExit("fixture value does not match the declared independent oracle")

    request = urllib.request.Request(
        CANDIDATE_API + "/api/turn",
        data=json.dumps({
            "candidate": args.candidate,
            "user_token": TOKEN,
            "messages": [{"role": "user", "content": PROMPT}],
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read())
    task = get_json("/v1/tasks/" + urllib.parse.quote(result["task_id"], safe=""))
    after = get_json(memory_path)
    answer = result.get("text", "")
    tools = task.get("checkpoint", {}).get("candidate_turn", {}).get("tools", [])
    passed = (
        task.get("state") == "COMPLETED"
        and tools == ["memory_search"]
        and args.expected_style.casefold() in answer.casefold()
        and before.get("value") == after.get("value")
        and not task.get("effects")
    )
    print(json.dumps({
        "candidate": args.candidate,
        "task_state": task.get("state"),
        "tools": tools,
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms"),
        "answer": answer,
        "fixture_unchanged": before.get("value") == after.get("value"),
        "effect_count": len(task.get("effects", [])),
        "passed": passed,
    }, ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
