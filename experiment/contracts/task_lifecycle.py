"""Shared task completion rules used by candidates and the trusted gateway."""

READ_TOOLS = {
    "infrastructure_read", "inventory_read", "shopping_list_read", "memory_read",
    "memory_search",
}
WRITE_TOOLS = {
    "shopping_list_change", "workspace_exec", "commitment_submit",
    "commitment_reconcile", "memory_write", "memory_correct",
}


def _verified_reads(evidence):
    return any(item.get("tool") in READ_TOOLS and item.get("status") == "ok" for item in evidence)


def decide_turn_finalization(current_state, response, evidence, claim, effect_states=None, effect_records=None):
    """Decide state from observed work, preserving externally meaningful states."""
    if current_state != "RUNNING":
        return current_state, "existing_state_preserved"
    evidence = evidence or []
    effect_states = effect_states or []
    effect_records = effect_records or []
    if any(item.get("approval_pending") for item in evidence):
        return "WAITING", "approval_required"
    resolved_ids = {str(item.get("effect_id")) for item in evidence
                    if item.get("tool") == "commitment_reconcile" and item.get("state") == "CONFIRMED"}
    unresolved = [item for item in evidence if item.get("uncertain")
                  and str(item.get("effect_id")) not in resolved_ids]
    if unresolved:
        return "WAITING", "effect_outcome_uncertain"
    states = [item.get("state") for item in effect_records] or effect_states
    if any(state in {"REJECTED", "FAILED", "CANCELLED"} for state in states):
        return "FAILED", "effect_failed"
    if any(state != "CONFIRMED" for state in states):
        return "WAITING", "effect_outcome_uncertain"
    progress = next((item.get("checkpoint") for item in reversed(evidence)
                     if item.get("kind") == "progress_checkpoint"), None)
    if progress and progress.get("pending"):
        return "RUNNING", "authorized_steps_remain"
    if claim and claim.get("pending"):
        return "RUNNING", "authorized_steps_remain"
    if not isinstance(response, str) or not response.strip():
        return "FAILED", "no_final_model_response"
    if any(item.get("status") == "error" and not (item.get("uncertain")
           and str(item.get("effect_id")) in resolved_ids) for item in evidence):
        return "FAILED", "tool_error_prevents_completion"
    writes = [item for item in evidence if item.get("tool") in WRITE_TOOLS]
    writes = [item for item in writes if not (item.get("uncertain")
              and str(item.get("effect_id")) in resolved_ids)]
    effects = [item for item in effect_states]
    if effect_records:
        effects = [item.get("state") for item in effect_records]
    if not writes and not effects and _verified_reads(evidence):
        return "COMPLETED", "successful_read_response"
    if not writes and not effects:
        return "FAILED", "completion_without_verified_outcome"
    if not claim:
        return "FAILED", "write_completion_not_claimed"
    if claim.get("pending") or not claim.get("completed"):
        return "RUNNING", "authorized_steps_remain"
    if any(item.get("status") != "ok" or item.get("state") != "CONFIRMED" for item in writes):
        return "WAITING", "effect_outcome_uncertain"
    return "COMPLETED", "verified_write_and_explicit_completion"


def validate_finalization(proof, checkpoint, effects):
    """Validate gateway-supplied completion against read/write evidence and DB effects."""
    if not isinstance(proof, dict) or not isinstance(checkpoint, dict) or not isinstance(effects, list):
        return "completion proof is malformed"
    if not proof.get("response_nonempty"):
        return "a nonempty final response is required"
    evidence = proof.get("tool_evidence")
    if not isinstance(evidence, list) or not all(isinstance(item, dict) for item in evidence):
        return "tool evidence is required"
    if checkpoint.get("pending"):
        return "pending task steps prevent completion"
    if not checkpoint.get("completed"):
        return "completed task steps are required"
    reads = [e for e in evidence if e.get("tool") in READ_TOOLS and e.get("status") == "ok"]
    writes = [e for e in evidence if e.get("tool") in WRITE_TOOLS]
    resolved_ids = {str(item.get("effect_id")) for item in evidence
                    if item.get("tool") == "commitment_reconcile" and item.get("state") == "CONFIRMED"}
    if any(item.get("status") == "error" and not (item.get("uncertain")
           and str(item.get("effect_id")) in resolved_ids) for item in evidence):
        return "tool errors prevent completion"
    if not writes and not effects:
        if reads and proof.get("task_type") == "READ_ONLY":
            return None
        return "completion requires verified read or write evidence"
    if proof.get("task_type") != "EFFECTFUL" or proof.get("completion_claim") is not True:
        return "effectful completion requires an explicit completion claim"
    if not writes:
        return "each task effect requires corresponding write evidence"
    db_by_id = {str(e.get("effect_id")): e for e in effects if e.get("effect_id")}
    evidence_by_id = {}
    for item in writes:
        effect_id = item.get("effect_id")
        if not effect_id:
            if item.get("tool") in {"memory_write", "memory_correct"} and not effects and item.get("state") == "CONFIRMED" and item.get("status") == "ok":
                continue
            return "write evidence must identify its persisted effect"
        evidence_by_id.setdefault(str(effect_id), []).append(item)
    if set(evidence_by_id) != set(db_by_id):
        return "write evidence must match each persisted effect ID exactly"
    for effect_id, db_effect in db_by_id.items():
        if db_effect.get("state") != "CONFIRMED":
            return "all task effects must be confirmed"
        valid = False
        for item in evidence_by_id[effect_id]:
            kind = db_effect.get("effect_kind")
            allowed = {
                "GROCERY_LIST": {"shopping_list_change"},
                "WORKSPACE_COMMAND": {"workspace_exec"},
                "EXTERNAL_COMMITMENT": {"commitment_submit", "commitment_reconcile"},
            }.get(kind, set())
            if (item.get("tool") in allowed and item.get("status") == "ok"
                    and item.get("state") == "CONFIRMED"
                    and (item.get("tool") != "shopping_list_change" or item.get("verified_after") is not None)
                    and (item.get("tool") != "workspace_exec" or item.get("exit_code") == 0)):
                valid = True
        if not valid:
            return "persisted effect lacks matching verified write evidence"
    return None
