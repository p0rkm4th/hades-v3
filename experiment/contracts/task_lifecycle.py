"""Shared task completion rules used by candidates and the trusted gateway."""

import hashlib
import json
import re

READ_TOOLS = {
    "infrastructure_read", "inventory_read", "shopping_list_read", "memory_read",
    "memory_search",
}
WRITE_TOOLS = {
    "shopping_list_change", "workspace_exec", "commitment_submit",
    "commitment_reconcile", "memory_write", "memory_correct",
}
MEMORY_WRITES = {"memory_write", "memory_correct"}
_PROVIDER_DIAGNOSTICS = (
    re.compile(r"\b(?:model|inference|llm) provider\b.{0,100}\b(?:rate[- ]?limit(?:ing|ed)?|retry|error|unavailable|failed)\b", re.I),
    re.compile(r"\bprovider\b.{0,100}\b(?:rate[- ]?limit(?:ing|ed)?|429|too many requests|temporarily unavailable)\b", re.I),
    re.compile(r"\b(?:rate[- ]?limit(?:ing|ed)?)\b.{0,100}\b(?:provider|retry|try again|request)\b", re.I),
)


def provider_diagnostic(text):
    return isinstance(text, str) and any(pattern.search(text) for pattern in _PROVIDER_DIAGNOSTICS)


def _verified_reads(evidence):
    return any(item.get("tool") in READ_TOOLS and item.get("status") == "ok" for item in evidence)


def commitment_digest(target_id, details):
    canonical = json.dumps(
        {"target_id": target_id, "details": details}, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def normalize_completion_contract(contract):
    """Accept only the small, typed external-commitment criterion in CP73."""
    if not isinstance(contract, dict) or set(contract) != {"version", "kind", "required"}:
        raise ValueError("completion contract must contain version, kind, and required")
    if contract["version"] != 1 or contract["kind"] != "external_commitment_set":
        raise ValueError("unsupported trusted completion contract")
    required = contract["required"]
    if not isinstance(required, list) or not 1 <= len(required) <= 16:
        raise ValueError("completion contract requires 1 to 16 exact effects")
    normalized = []
    targets = set()
    for item in required:
        if not isinstance(item, dict) or set(item) != {"effect_kind", "target_id", "details"}:
            raise ValueError("each required effect must specify kind, target, and details")
        target_id, details = item["target_id"], item["details"]
        if (item["effect_kind"] != "EXTERNAL_COMMITMENT"
                or not isinstance(target_id, str) or not re.fullmatch(r"[a-z0-9-]{1,80}", target_id)
                or target_id in targets
                or not isinstance(details, str) or not details.strip() or len(details) > 1000):
            raise ValueError("invalid or duplicate exact commitment requirement")
        details = details.strip()
        targets.add(target_id)
        normalized.append({
            "effect_kind": "EXTERNAL_COMMITMENT", "target_id": target_id,
            "details": details, "effect_digest": commitment_digest(target_id, details),
        })
    return {"version": 1, "kind": "external_commitment_set", "required": normalized}


def validate_trusted_effect_contract(contract, task_identity, effects, approvals, canonical_states):
    """Prove every registered operation against task, approval, ledger, and target state."""
    try:
        normalized = normalize_completion_contract({
            "version": contract.get("version"), "kind": contract.get("kind"),
            "required": [
                {key: item[key] for key in ("effect_kind", "target_id", "details")}
                for item in contract.get("required", [])
            ],
        })
    except (AttributeError, KeyError, TypeError, ValueError):
        return "trusted completion contract is malformed"
    if normalized != contract:
        return "trusted completion contract digest or shape changed"
    if not isinstance(task_identity, dict) or not task_identity.get("task_id"):
        return "task identity is unavailable"
    if not isinstance(effects, list) or len(effects) != len(normalized["required"]):
        return "persisted effects do not exactly match required operations"
    if not isinstance(approvals, dict) or not isinstance(canonical_states, dict):
        return "trusted authorization or canonical state evidence is unavailable"
    effect_by_target = {}
    for effect in effects:
        request = effect.get("request") or {}
        target_id = request.get("target_id")
        if target_id in effect_by_target:
            return "multiple persisted effects match one required operation"
        effect_by_target[target_id] = effect
    for required in normalized["required"]:
        target_id = required["target_id"]
        effect = effect_by_target.get(target_id)
        if effect is None:
            return "required operation has no persisted effect"
        request = effect.get("request") or {}
        if (str(effect.get("task_id")) != str(task_identity.get("task_id"))
                or effect.get("user_id") != task_identity.get("user_id")
                or effect.get("domain_id") != task_identity.get("domain_id")):
            return "effect identity does not match the original task"
        effect_id = str(effect.get("effect_id", ""))
        if (effect.get("effect_kind") != required["effect_kind"]
                or effect.get("resource_key") != f"commitment:{target_id}"
                or request.get("target_id") != target_id
                or request.get("details") != required["details"]
                or request.get("effect_digest") != required["effect_digest"]
                or effect.get("state") != "CONFIRMED"):
            return "persisted effect does not match the exact required operation"
        approval_id = str(request.get("approval_id", ""))
        approval = approvals.get(approval_id)
        if (approval is None
                or str(approval.get("task_id")) != str(task_identity.get("task_id"))
                or approval.get("user_id") != task_identity.get("user_id")
                or approval.get("domain_id") != task_identity.get("domain_id")
                or approval.get("target_id") != target_id
                or approval.get("effect_digest") != required["effect_digest"]
                or not approval.get("consumed_at")
                or approval["consumed_at"] > approval["expires_at"]):
            return "persisted effect lacks its exact consumed authorization"
        canonical = canonical_states.get(effect_id)
        if (not isinstance(canonical, dict)
                or canonical.get("state") != "ACCEPTED"
                or str(canonical.get("effect_id")) != effect_id
                or canonical.get("target_id") != target_id
                or not isinstance(canonical.get("receive_count"), int)
                or canonical["receive_count"] < 1):
            return "canonical target state does not confirm the exact effect"
    return None


def decide_turn_finalization(current_state, response, evidence, claim, effect_states=None, effect_records=None,
                            turn_error=None, trusted_completion_contract=None):
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
    writes = [item for item in evidence if item.get("tool") in WRITE_TOOLS]
    if any(item.get("tool") in MEMORY_WRITES and item.get("status") == "ok" for item in writes) and not any(
        item.get("tool") in MEMORY_WRITES
        and item.get("status") == "ok"
        and any(record.get("effect_id") == item.get("effect_id")
                and record.get("effect_kind") == "MEMORY_MUTATION"
                and record.get("state") == "CONFIRMED" for record in (effect_records or []))
        for item in writes
    ):
        # A successful memory response without its identity-linked ledger row
        # cannot establish whether the requested change is safe to retry.
        return "WAITING", "memory_effect_evidence_unproven"
    if turn_error:
        if writes or effect_states or effect_records:
            return "WAITING", "final_response_pending"
        return "FAILED", "model_generation_failed"
    if not isinstance(response, str) or not response.strip():
        if writes or effect_states or effect_records:
            return "WAITING", "final_response_pending"
        return "FAILED", "no_final_model_response"
    if any(item.get("status") == "error" and not (item.get("uncertain")
           and str(item.get("effect_id")) in resolved_ids) for item in evidence):
        return "FAILED", "tool_error_prevents_completion"
    writes = [item for item in writes if not (item.get("uncertain")
              and str(item.get("effect_id")) in resolved_ids)]
    effects = [item for item in effect_states]
    if effect_records:
        effects = [item.get("state") for item in effect_records]
    if not writes and not effects and _verified_reads(evidence):
        return "COMPLETED", "successful_read_response"
    if not writes and not effects:
        return "FAILED", "completion_without_verified_outcome"
    if trusted_completion_contract is not None:
        try:
            contract = normalize_completion_contract({
                "version": trusted_completion_contract.get("version"),
                "kind": trusted_completion_contract.get("kind"),
                "required": [
                    {key: item[key] for key in ("effect_kind", "target_id", "details")}
                    for item in trusted_completion_contract.get("required", [])
                ],
            })
        except (AttributeError, KeyError, TypeError, ValueError):
            return "WAITING", "completion_review_required"
        if (contract != trusted_completion_contract or len(contract["required"]) != len(effects)
                or any(state != "CONFIRMED" for state in effects)):
            return "WAITING", "completion_review_required"
        return "COMPLETED", "trusted_success_criteria_satisfied"
    if not claim:
        return "WAITING", "completion_review_required"
    if claim.get("pending") or not claim.get("completed"):
        return "RUNNING", "authorized_steps_remain"
    if any(item.get("status") != "ok" or item.get("state") != "CONFIRMED" for item in writes):
        return "WAITING", "effect_outcome_uncertain"
    return "COMPLETED", "verified_write_and_explicit_completion"


def validate_finalization(proof, checkpoint, effects, task_identity=None, canonical_memory=None):
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
                "MEMORY_MUTATION": {"memory_write", "memory_correct"},
            }.get(kind, set())
            memory_valid = kind != "MEMORY_MUTATION"
            if kind == "MEMORY_MUTATION":
                request = db_effect.get("request") or {}
                result = db_effect.get("result") or {}
                canonical = (canonical_memory or {}).get(effect_id)
                expected_tool = request.get("operation")
                memory_valid = (
                    item.get("tool") == expected_tool
                    and expected_tool in MEMORY_WRITES
                    and db_effect.get("resource_key") == f"memory:{request.get('memory_key')}"
                    and item.get("memory_key") == request.get("memory_key")
                    and task_identity is not None
                    and str(db_effect.get("task_id")) == str(task_identity.get("task_id"))
                    and db_effect.get("user_id") == task_identity.get("user_id")
                    and db_effect.get("domain_id") == task_identity.get("domain_id")
                    and canonical is not None
                    and canonical.get("memory_key") == request.get("memory_key")
                    and canonical.get("value") == request.get("value")
                    and result.get("value") == canonical.get("value")
                )
            if (item.get("tool") in allowed and item.get("status") == "ok"
                    and item.get("state") == "CONFIRMED"
                    and (item.get("tool") != "shopping_list_change" or item.get("verified_after") is not None)
                    and (item.get("tool") != "workspace_exec" or item.get("exit_code") == 0)
                    and memory_valid):
                valid = True
        if not valid:
            return "persisted effect lacks matching verified write evidence"
    return None
