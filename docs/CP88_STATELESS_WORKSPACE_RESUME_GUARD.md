# CP88 — Fail-closed stateless workspace resume

**Date:** 2026-10-14  
**Scope:** Candidate API safety correction and offline regression; no live workspace dispatch  
**Classification:** Source change plus deterministic contract test

## Reproduced safety gap

The shared candidate `/api/turn` endpoint persists task/effect state but does not persist its own model conversation or tool-call journal. After a process dies with a confirmed `WORKSPACE_COMMAND` effect and before the final response/task transition is stored, a fresh request can resume the task using caller-supplied messages. A new model call may create a different tool-call ID; the gateway correctly treats that as a distinct operation and can dispatch it again. Gateway idempotency cannot infer that different identities represent a retry rather than a legitimate second command.

The uncertain-effect path remains fail-closed: `DISPATCHED`/`QUARANTINED` effects block further workspace dispatch. The exposed duplicate risk is a confirmed operation with a lost response and a new identity.

## Correction

The candidate API now inspects the authenticated task/effect snapshot before resuming an active task. If any confirmed workspace command exists, it does not start a new model turn. A `RUNNING` task is sent through `transition_task` to `WAITING` with `operator_review_required`; an already `WAITING` task remains there. If the task response omits its effect list, resume is also parked because absence of effects cannot be assumed. The endpoint returns HTTP 409 with a sanitized explanation. No effect is reissued and no claim of completion or delivery is made.

This is a conservative stopgap for the stateless A/B/C API. It intentionally sacrifices automatic continuation after a confirmed workspace effect until a runtime persists and authenticates the original invocation history and reconciles it against the HADES ledger. The separate A2 StepPersistence probe shows a path for preserving the call ID, but its HADES-aware resume gate remains test-only. This change does not claim exactly-once arbitrary shell execution or add another ledger.

## Regression evidence

`experiment/candidates/test_workspace_identity.py` now verifies:

- A `RUNNING` task with a confirmed workspace effect is parked in `WAITING` with operator review.
- A `WAITING` task is returned as blocked without a contradictory transition.
- A pure task or one containing only a non-workspace effect is not blocked by this guard.
- A missing effect snapshot is parked fail-closed.
- Pydantic A retains `max_retries=0`, and A/C workspace dispatch still binds to the persisted call identity.
- A route-level `/api/turn` request with a confirmed workspace effect returns HTTP 409, requests the `WAITING` transition, and makes no candidate model call. The route test stubs gateway persistence; existing database-backed gateway CI separately exercises task/effect transitions.

The regression passed in the cached pinned candidate image with current source mounted read-only, `--network none`, no capabilities, and no fixture service. It sent no model/provider request. The earlier CP85 and CP81 outcomes are unchanged. The full exact-SHA CI run is pending.

## Limitations

The candidate task remains incomplete and requires operator review; this guard does not reconstruct a lost answer or resume the original call. Memory, commitment, and other effect types follow their existing state contracts. A2's durable original-call continuation is separate and must not be routed through this stateless guard without a verified invocation-history integration.
