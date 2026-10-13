import argparse
import json
import os
import urllib.request
import urllib.error


parser = argparse.ArgumentParser()
parser.add_argument("--candidate", choices=("lean", "pydantic", "hermes"), required=True)
parser.add_argument("--user", choices=("amber", "cobalt"), default="amber")
parser.add_argument("--prompt", required=True)
args = parser.parse_args()
payload = {
    "candidate": args.candidate,
    "user_token": f"fixture-token-{args.user}",
    "messages": [{"role": "user", "content": args.prompt}],
}
request = urllib.request.Request(
    os.environ.get("CANDIDATE_API_URL", "http://candidate-api:8080/api/turn"),
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=600) as response:
        print(json.dumps(json.loads(response.read()), indent=2))
except urllib.error.HTTPError as error:
    print(json.dumps({"http_status": error.code, "response": error.read().decode(errors="replace")}, indent=2))
    raise
