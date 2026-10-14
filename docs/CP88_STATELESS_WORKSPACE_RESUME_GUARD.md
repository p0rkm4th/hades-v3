# CP88 — Fail-closed stateless workspace resume

**Date:** 2026-10-14  
**Scope:** Candidate API safety correction and offline regression; no live workspace dispatch  
**Classification:** Source change plus deterministic contract test

## Reproduced safety gap

The shared candidate `/api/turn` endpoint persists task/effect state but does not persist its own model conversation or tool-call journal. After a process dies with a confirmed `WORKSPACE_COMMAND` effect and before the final response/task transition is stored, a fresh request can resume the task using caller-supplied messages. A new model call may create a different tool-call ID; the gateway correctly treats that as a distinct operation and can dispatch it again. Gateway idempotency cannot infer that different identities represent a retry rather than a legitimate second command.

The uncertain-effect path remains fail-closed: `DISPATCHED`/`QUARANTINED` effects block further workspace dispatch. The exposed duplicate risk is a confirmed operation with a lost response and a new identity.

## Correction

The candidate API now inspects the authenticated task/effect snapshot before resuming an active task. If any confirmed workspace command exists, it does not start a new model turn. A `RUNNING` task is sent through `transition_task` to `WAITING` with `operator_review_required`; when all recorded effects are terminal, stale uncertainty annotation is cleared without changing their effect records. An already `WAITING` task remains there. If the task response omits its effect list, resume is also parked because absence of effects cannot be assumed. The endpoint returns HTTP 409 with a sanitized explanation. No effect is reissued and no claim of completion or delivery is made.

This is a conservative stopgap for the stateless A/B/C API. It intentionally sacrifices automatic continuation after a confirmed workspace effect until a runtime persists and authenticates the original invocation history and reconciles it against the HADES ledger. The separate A2 StepPersistence probe shows a path for preserving the call ID, but its HADES-aware resume gate remains test-only. This change does not claim exactly-once arbitrary shell execution or add another ledger.

## Regression evidence

`experiment/candidates/test_workspace_identity.py` now verifies:

- A `RUNNING` task with a confirmed workspace effect is parked in `WAITING` with operator review.
- A `WAITING` task is returned as blocked without a contradictory transition.
- A pure task or one containing only a non-workspace effect is not blocked by this guard.
- A missing effect snapshot is parked fail-closed.
- Pydantic A retains `max_retries=0`, and A/C workspace dispatch still binds to the persisted call identity.
- A route-level `/api/turn` request with a confirmed workspace effect returns HTTP 409, requests the `WAITING` transition, and makes no candidate model call. The route test stubs gateway persistence; existing database-backed gateway CI separately exercises task/effect transitions.
- The transition request carries the orchestrator finalization marker required by the gateway's `RUNNING` to `WAITING` authorization rule. This adapter test stubs the gateway call; it verifies the request contract, while the database-backed gateway suite covers orchestrator-only waiting transitions separately.
- A settled confirmed effect clears only the task's stale `effect_outcome_uncertain` annotation while parking; an incomplete/missing effect snapshot does not clear it.

The regression passed in the cached pinned candidate image with current source mounted read-only, `--network none`, no capabilities, and no fixture service. It sent no model/provider request. The earlier CP85 and CP81 outcomes are unchanged. The database-backed CP88 integration and full exact-SHA workflow passed at source commit `33ab8587f43272f8bc482c6ccfa92ab1457ba0f9`, run [38607008722](https://github.com/p0rkm4th/hades-v3/actions/runs/38607008722). The workflow's isolated cleanup step also passed.

A database-backed integration test in the existing CP69 strict-offline CI fixture creates one synthetic task, runs a harmless `pwd` workspace command to produce a confirmed effect, resumes through the candidate HTTP route, then independently checks the persisted `WAITING` checkpoint, unchanged single workspace effect ID/operation ID, unchanged memory row counts, and unchanged scripted-model request count. It passed in the exact-SHA CI run above.

## Limitations

The candidate task remains incomplete and requires operator review; this guard does not reconstruct a lost answer or resume the original call. It covers a sequential resume after the confirmed effect is visible in the ledger. It does not serialize concurrent `/api/turn` requests: two turns can both pass the preflight before either command is recorded, and a later distinct tool-call identity is not provably a retry rather than a legitimate next command. That concurrency case is source-level unqualified and remains a duplicate-risk boundary. The gateway's task-row lock serializes each effect-creation transaction, not the whole model turn. Memory, commitment, and other effect types follow their existing state contracts. A2's durable original-call continuation is separate and must not be routed through this stateless guard without a verified invocation-history integration.
