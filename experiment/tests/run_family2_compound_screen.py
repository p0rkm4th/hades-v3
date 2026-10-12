"""Run one matched, repeated A/C family 2 shopping-list screen on the operator network."""

import json
import urllib.error
import urllib.request


TOKEN = "fixture-token-amber"
GATEWAY = "http://tool-gateway:8080"
CANDIDATE_API = "http://candidate-api:8080"
PROMPT = "Please put two Pasta on the shopping list and take Milk off."
SEED = {"Milk": 1.0, "Oats": 1.0}
EXPECTED = {"Oats": 1.0, "Pasta": 2.0}
ORDER = ("lean", "pydantic", "lean", "pydantic", "lean", "pydantic")


def gateway(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        GATEWAY + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.loads(response.read())


def list_quantities():
    rows = gateway("GET", "/v1/shopping-list")["items"]
    return {row["name"]: float(row["amount"]) for row in rows}


def reset_seed():
    current = list_quantities()
    result = gateway("POST", "/v1/shopping-list/changes", {
        "remove": list(current),
        "add": [{"name": name, "amount": amount} for name, amount in SEED.items()],
    })
    observed = list_quantities()
    assert result["state"] == "CONFIRMED", result
    assert observed == SEED, observed
    return {"task_id": result["task_id"], "effect_id": result["effect_id"]}


results = []
for candidate in ORDER:
    reset = reset_seed()
    payload = {
        "candidate": candidate,
        "user_token": TOKEN,
        "messages": [{"role": "user", "content": PROMPT}],
    }
    request = urllib.request.Request(
        CANDIDATE_API + "/api/turn",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as error:
        details = error.read().decode(errors="replace")
        try:
            failed_task_id = json.loads(details).get("task_id", "unavailable")
        except json.JSONDecodeError:
            failed_task_id = "unavailable"
        raise RuntimeError(
            f"{candidate} failed as task {failed_task_id} after reset {reset['task_id']}; "
            f"inspect its task/effect before another reset: {details}"
        ) from error

    task_id = result["task_id"]
    task = gateway("GET", f"/v1/tasks/{task_id}")
    trace = result.get("tool_calls", [])
    checkpoint = task.get("checkpoint", {}).get("candidate_turn", {})
    observed = list_quantities()
    assert task["state"] == "COMPLETED", task
    assert checkpoint.get("state") == "COMPLETED", task
    assert checkpoint.get("tools") == trace, task
    assert trace == ["inventory_read", "shopping_list_change"], trace
    assert observed == EXPECTED, observed
    results.append({
        "candidate": candidate,
        "reset_task_id": reset["task_id"],
        "task_id": task_id,
        "state": task["state"],
        "tool_calls": trace,
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms"),
        "verified_after": observed,
        "text": result.get("text", ""),
    })

final_reset = reset_seed()
print(json.dumps({"results": results, "final_reset": final_reset, "final_seed": list_quantities()}, indent=2))
