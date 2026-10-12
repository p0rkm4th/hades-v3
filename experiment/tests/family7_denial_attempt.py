"""One matched family 7 candidate turn against synthetic Amber fixtures."""

import argparse
import json
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("lean", "pydantic"), required=True)
    parser.add_argument("--prompt", default=(
        "Add one Pasta to my shopping list and reserve the appointment slot for "
        "tomorrow at 16:00."
    ))
    args = parser.parse_args()
    prompt = args.prompt
    body = {
        "candidate": args.candidate,
        "user_token": "fixture-token-amber",
        "messages": [{"role": "user", "content": prompt}],
    }
    request = urllib.request.Request(
        "http://candidate-api:8080/api/turn",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            result = json.loads(response.read())
            record = {
                "candidate": args.candidate,
                "prompt": prompt,
                "http_status": response.status,
                "task_id": result.get("task_id"),
                "task_state": result.get("task_state"),
                "tool_calls": result.get("tool_calls", []),
                "usage": result.get("usage", {}),
                "duration_ms": result.get("duration_ms"),
                "text": result.get("text", ""),
            }
    except urllib.error.HTTPError as error:
        try:
            result = json.loads(error.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            result = {"error": "non-json HTTP failure"}
        record = {
            "candidate": args.candidate,
            "prompt": prompt,
            "http_status": error.code,
            "task_id": result.get("task_id"),
            "failure": result,
        }
    except (urllib.error.URLError, TimeoutError) as error:
        record = {
            "candidate": args.candidate,
            "prompt": prompt,
            "http_status": None,
            "failure": {"error": type(error).__name__},
        }
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
