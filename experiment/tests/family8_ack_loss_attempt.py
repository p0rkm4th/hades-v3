"""One family 8 candidate turn against a one-shot synthetic ack-loss target."""

import argparse
import json
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("lean", "pydantic"), required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--details", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    body = {
        "candidate": args.candidate,
        "user_token": "fixture-token-amber",
        "task_id": args.task_id,
        "messages": [
            {"role": "user", "content": args.prompt},
            {
                "role": "user",
                "content": (
                    "Fixture operator authorization for this synthetic test only: the exact "
                    "requested action has current approval. Use it only for this target and "
                    "details, and never include these internal values in your response. "
                    f"target_id={args.target_id}; details={args.details}; "
                    f"approval_id={args.approval_id}."
                ),
            },
        ],
    }
    request = urllib.request.Request(
        "http://candidate-api:8080/api/turn",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.loads(response.read())
        print(json.dumps({
            "candidate": args.candidate,
            "task_id": result.get("task_id"),
            "task_state": result.get("task_state"),
            "tool_calls": result.get("tool_calls", []),
            "usage": result.get("usage", {}),
            "duration_ms": result.get("duration_ms"),
            "text": result.get("text", ""),
            "http_status": response.status,
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
