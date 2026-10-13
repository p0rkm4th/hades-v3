"""Shared evidence rules for ending a candidate task turn."""

from __future__ import annotations


READ_TOOLS = {
    "inventory_read",
    "shopping_list_read",
    "infrastructure_read",
    "memory_read",
    "memory_search",
    "workspace_read",
}
WRITE_TOOLS = {
    "shopping_list_change",
    "memory_write",
    "memory_correct",
    "workspace_exec",
    "commitment_submit",
    "commitment_reconcile",
}
TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def decide_turn_finalization(
    current_state: str,
    response_text: str | None,
    tool_evidence: list[dict],
    completion_claim: dict | None,
    effect_states: list[str] | None = None,
) -> tuple[str, str]:
    """Return canonical state and reason without treating HTTP success as proof."""
    if current_state in TERMINAL_STATES or current_state == "WAITING":
        return current_state, "preserved_existing_state"

    if any(item.get("approval_pending") for item in tool_evidence):
        return "WAITING", "approval_pending"
    resolved_ids = {
        item.get("effect_id") for item in tool_evidence
        if item.get("tool") == "commitment_reconcile" and item.get("state") == "CONFIRMED"
    }
    if any(item.get("uncertain") and item.get("effect_id") not in resolved_ids for item in tool_evidence):
        return "WAITING", "effect_outcome_uncertain"

    claim = completion_claim or {}
    pending = claim.get("pending")
    if pending is None:
        pending = []
    if not isinstance(pending, list):
        return "FAILED", "invalid_completion_claim"
    if pending:
        return "RUNNING", "authorized_steps_remain"

    if not isinstance(response_text, str) or not response_text.strip():
        return "FAILED", "no_final_model_response"

    relevant = [item for item in tool_evidence if item.get("tool") in READ_TOOLS | WRITE_TOOLS]
    latest_by_tool = {}
    for item in relevant:
        latest_by_tool[item.get("tool")] = item
    if any(item.get("status") != "ok" for item in latest_by_tool.values()):
        return "FAILED", "tool_error_prevents_completion"

    writes = [
        item for item in relevant
        if item.get("tool") in WRITE_TOOLS
        and not (item.get("uncertain") and item.get("effect_id") in resolved_ids)
    ]
    effect_states = effect_states or []
    if any(state in {"REJECTED", "FAILED", "CANCELLED"} for state in effect_states):
        return "FAILED", "effect_failed"
    if effect_states and any(state != "CONFIRMED" for state in effect_states):
        return "WAITING", "effect_outcome_not_confirmed"
    if effect_states and not claim:
        return "FAILED", "effect_completion_not_claimed"
    if writes:
        if not claim or not claim.get("completed"):
            return "FAILED", "write_completion_not_claimed"
        for item in writes:
            if item.get("state") in {"REJECTED", "FAILED", "CANCELLED"}:
                return "FAILED", "write_failed"
            if item.get("state") != "CONFIRMED":
                return "WAITING", "write_outcome_not_confirmed"
            if item.get("tool") == "shopping_list_change" and not item.get("verified_after"):
                return "WAITING", "write_readback_missing"
            if item.get("tool") == "workspace_exec" and item.get("exit_code") != 0:
                return "WAITING", "workspace_command_not_verified"
        return "COMPLETED", "verified_write_and_explicit_completion"

    successful_reads = [item for item in relevant if item.get("tool") in READ_TOOLS]
    if successful_reads:
        if not claim or not claim.get("completed"):
            return "FAILED", "read_completion_not_claimed"
        if effect_states and not claim.get("completed"):
            return "FAILED", "effect_completion_not_claimed"
        return "COMPLETED", "successful_read_response"
    if claim and claim.get("completed"):
        return "COMPLETED", "explicit_response_completion"
    return "FAILED", "response_has_no_completion_evidence"


def validate_finalization(finalization: dict, checkpoint: dict, effect_states: list[str]) -> str | None:
    """Return a rejection reason unless an orchestrator proof justifies completion."""
    if not isinstance(finalization, dict) or finalization.get("response_nonempty") is not True:
        return "a nonempty final model response is required"
    if checkpoint.get("pending"):
        return "pending work prevents task completion"
    if not checkpoint.get("completed"):
        return "at least one completed step is required"
    if any(state != "CONFIRMED" for state in effect_states):
        return "every task effect must be confirmed before completion"

    evidence = finalization.get("tool_evidence")
    if not isinstance(evidence, list):
        return "orchestrator tool evidence is required"
    read_proof = any(
        isinstance(item, dict)
        and item.get("tool") in READ_TOOLS
        and item.get("status") == "ok"
        for item in evidence
    )
    resolved_ids = {
        item.get("effect_id") for item in evidence
        if isinstance(item, dict) and item.get("tool") == "commitment_reconcile" and item.get("state") == "CONFIRMED"
    }
    write_evidence = []
    for item in evidence:
        if (isinstance(item, dict) and item.get("tool") in WRITE_TOOLS
                and not (item.get("uncertain") and item.get("effect_id") in resolved_ids)):
            write_evidence.append(item)
    if finalization.get("completion_claim") is not True:
        return "a completion claim is required"
    if effect_states:
        if len(write_evidence) < len(effect_states):
            return "each task effect requires corresponding write evidence"
        if any(item.get("status") != "ok" or item.get("state") != "CONFIRMED" for item in write_evidence):
            return "write evidence is not confirmed"
        if any(item.get("tool") == "shopping_list_change" and not item.get("verified_after") for item in write_evidence):
            return "write read-back evidence is required"
        if any(item.get("tool") == "workspace_exec" and item.get("exit_code") != 0 for item in write_evidence):
            return "workspace command evidence is not successful"
        return None
    if read_proof:
        return None
    if finalization.get("completion_claim"):
        return None
    return "a successful read or explicit completion claim is required"
