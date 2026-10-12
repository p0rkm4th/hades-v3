"""Run a fresh, independently verified A/C family 2 compound screen."""

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", "experiment/compose.yaml"]
TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
PROMPT = "Take Oats off my shopping list, and add two Eggs. What will the list show?"
SEED = {"Milk": 1.0, "Oats": 1.0}
EXPECTED = {"Milk": 1.0, "Eggs": 2.0}
ORDER = ("lean", "pydantic", "lean", "pydantic", "lean", "pydantic")
DEFAULT_OUTPUT = "experiment/results/family2_eggs_oats_screen_cp45.jsonl"
TERMINAL_EFFECTS = {"CONFIRMED", "REJECTED", "FAILED", "CANCELLED"}


def compose(*args, timeout=60, check=True):
    return subprocess.run(
        COMPOSE + list(args), cwd=ROOT, capture_output=True, text=True,
        timeout=timeout, check=check,
    )


def sql_json(query):
    result = compose(
        "exec", "-T", "postgres", "psql", "-U", "fixture_writer",
        "-d", "hades_lab", "-Atc", query,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else None


def gateway(method, path, payload=None):
    script = r'''import json,sys,urllib.request
method,path,payload=sys.argv[1],sys.argv[2],json.loads(sys.argv[3])
body=None if payload is None else json.dumps(payload).encode()
req=urllib.request.Request('http://tool-gateway:8080'+path,data=body,method=method,headers={'Authorization':'Bearer fixture-token-amber','Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=20) as response: print(json.dumps(json.load(response)))'''
    result = compose(
        "exec", "-T", "candidate-api", "python", "-c", script,
        method, path, json.dumps(payload),
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def list_quantities():
    rows = gateway("GET", "/v1/shopping-list")["items"]
    return {row["name"]: float(row["amount"]) for row in rows}


def model_profile():
    script = r'''import json,os,urllib.request
base=os.environ['MODEL_URL'].rstrip('/')
with urllib.request.urlopen(base+'/models',timeout=5) as response: value=json.load(response)
models=value.get('data') or []
meta=(models[0].get('meta') or {}) if models else {}
print(json.dumps({'model_name':os.environ.get('MODEL_NAME'),'model_url':os.environ.get('MODEL_URL'),'model_id':models[0].get('id') if models else None,'n_ctx':meta.get('n_ctx'),'n_ctx_train':meta.get('n_ctx_train'),'request_timeout_seconds':os.environ.get('MODEL_REQUEST_TIMEOUT_SECONDS')}))'''
    result = compose("exec", "-T", "candidate-api", "python", "-c", script)
    return json.loads(result.stdout.strip().splitlines()[-1])


def reset_seed():
    current = list_quantities()
    result = gateway("POST", "/v1/shopping-list/changes", {
        "remove": list(current),
        "add": [{"name": name, "amount": amount} for name, amount in SEED.items()],
    })
    observed = list_quantities()
    if result.get("state") != "CONFIRMED" or observed != SEED:
        raise RuntimeError(f"synthetic list reset did not verify: {result}, {observed}")
    return {"task_id": result.get("task_id"), "effect_id": result.get("effect_id")}


def task_record(task_id):
    safe = task_id.replace("'", "''")
    task = sql_json(
        "SELECT json_build_object('task_id',task_id,'state',state,'checkpoint',checkpoint)::text "
        f"FROM tasks WHERE task_id='{safe}'"
    )
    effects = sql_json(
        "SELECT coalesce(json_agg(json_build_object('effect_id',effect_id,'state',state,"
        "'kind',effect_kind,'resource',resource_key,'request',request,'result',result) "
        "ORDER BY created_at),'[]'::json)::text "
        f"FROM effects WHERE task_id='{safe}'"
    ) or []
    return {"task": task, "effects": effects}


def close_task_for_review(task_id):
    task = gateway("GET", f"/v1/tasks/{task_id}")
    if task.get("state") not in {"RUNNING", "WAITING"}:
        return None
    checkpoint = task.get("checkpoint") or {}
    checkpoint.setdefault("summary", "Operator closed disposable family 2 trial after outcome inspection")
    checkpoint.setdefault("completed", [])
    checkpoint.setdefault("pending", [])
    checkpoint["operator_review_required"] = True
    checkpoint["operator_closed_after_trial"] = True
    return gateway("POST", f"/v1/tasks/{task_id}/checkpoint", {
        "state": "FAILED", "checkpoint": checkpoint,
    })


def attempt(candidate):
    body = {
            "candidate": candidate,
            "user_token": TOKEN,
            "messages": [{"role": "user", "content": PROMPT}],
    }
    script = r'''import json,sys,urllib.error,urllib.request
body=json.loads(sys.argv[1]); req=urllib.request.Request('http://127.0.0.1:8080/api/turn',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
try:
 with urllib.request.urlopen(req,timeout=600) as response: print(json.dumps(json.load(response)))
except urllib.error.HTTPError as error:
 try: value=json.loads(error.read())
 except json.JSONDecodeError: value={'error':'candidate request failed'}
 value['http_status']=error.code; print(json.dumps(value))'''
    result = compose(
        "exec", "-T", "candidate-api", "python", "-c", script,
        json.dumps(body), timeout=630, check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        raise RuntimeError("candidate container returned no structured response; inspect its task/effects before resetting")
    value = json.loads(lines[-1])
    return value, value.get("task_id") if value.get("http_status", 200) >= 400 else None


def main():
    global PROMPT, EXPECTED
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--label", default="cp45-eggs-oats-8b")
    parser.add_argument("--prompt", default=PROMPT)
    parser.add_argument("--expected-json", default=None)
    parser.add_argument("--order", default=",".join(ORDER))
    args = parser.parse_args()
    PROMPT = args.prompt
    if not re.fullmatch(r"[a-z0-9-]{1,48}", args.label):
        raise SystemExit("label must use 1-48 lowercase letters, digits, or hyphens")
    if args.expected_json:
        EXPECTED = json.loads(args.expected_json)
    if not isinstance(EXPECTED, dict) or not EXPECTED or not all(
        isinstance(name, str) and isinstance(amount, (int, float)) and amount > 0
        for name, amount in EXPECTED.items()
    ):
        raise SystemExit("expected after-state must be a nonempty JSON object")
    order = tuple(args.order.split(","))
    if len(order) != 6 or set(order) != {"lean", "pydantic"} or order.count("lean") != 3 or order.count("pydantic") != 3:
        raise SystemExit("order must contain three lean and three pydantic attempts")
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT):
        raise SystemExit("evidence output must stay under the HADES v3 workspace")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing evidence: {output.name}")
    profile = model_profile()
    if not profile.get("model_id") or not profile.get("n_ctx"):
        raise RuntimeError(f"model endpoint did not report identity and context: {profile}")

    for index, candidate in enumerate(order, start=1):
        reset = reset_seed()
        before = list_quantities()
        result, error_task_id = attempt(candidate)
        task_id = result.get("task_id") or error_task_id
        if not task_id:
            raise RuntimeError("candidate response did not identify a task; inspect fixture before proceeding")
        record = task_record(task_id)
        after = list_quantities()
        states = {effect["state"] for effect in record["effects"]}
        if not states.issubset(TERMINAL_EFFECTS):
            raise RuntimeError(
                f"task {task_id} has an unresolved effect; preserve fixture for review"
            )
        closed = close_task_for_review(task_id)
        final_task = task_record(task_id)
        row = {
            "attempt_order": index,
            "run_label": args.label,
            "candidate": candidate,
            "model_profile": profile,
            "prompt": PROMPT,
            "reset": reset,
            "attempt": result,
            "task_after_candidate": record["task"],
            "effects_after_candidate": record["effects"],
            "task_after_operator_review": final_task["task"],
            "effects_final": final_task["effects"],
            "operator_closed_task": closed,
            "before_list": before,
            "after_list": after,
            "expected_list": EXPECTED,
            "postcondition_pass": after == EXPECTED,
        }
        with output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({
            "candidate": candidate,
            "task_id": task_id,
            "task_state_after_candidate": (record["task"] or {}).get("state"),
            "tool_calls": result.get("tool_calls", []),
            "effect_states": sorted(states),
            "after": after,
            "postcondition_pass": after == EXPECTED,
        }), flush=True)

        if not states.issubset(TERMINAL_EFFECTS):
            raise RuntimeError("unresolved effects; do not reset the synthetic fixture")
        reset_seed()

    if list_quantities() != SEED:
        raise RuntimeError("final synthetic list reset did not verify")
    print(json.dumps({"evidence": output.name, "model_profile": profile, "final_seed": list_quantities()}), flush=True)


if __name__ == "__main__":
    main()
