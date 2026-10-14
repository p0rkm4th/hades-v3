# CP73 — evidence-driven completion and restart recovery

## Result

CP73 removes one narrow lifecycle defect: a bounded effectful task can now reach durable `COMPLETED` without a model-generated administrative checkpoint, when an immutable trusted completion contract and persisted independent evidence prove every requested operation. The gateway rechecks the task, user and domain, exact effect request and digest, consumed approval, terminal effect row, and canonical target state. The original task/effect ledger remains the authority. A final user response must be persisted and provider failure prevents completion; response delivery remains explicitly `PERSISTED_PENDING_DELIVERY`.

This contract is limited to exact external commitment sets. Arbitrary free-text tasks still require the existing completion claim/evidence path. Partial or unmatched effects, uncertainty, wrong identity, absent/mismatched approval, provider failure, and memory mutation do not complete. Memory writes remain fail-closed as `WAITING` until task-linked durable memory-effect evidence exists. A confirmed effect with no usable final response is preserved in `WAITING` for response recovery rather than being erased or reported as delivered.

## Matched CPU recovery trials

The same synthetic appointment task, immutable one-effect contract, approval flow, Qwen3-8B Q4_K_M CPU endpoint, and isolated simulator were used for three repetitions each. The model server reports a 40,960-token context; this is below Hermes's 64,000-token minimum. Candidate order was A then C. Each scored trial interrupted the candidate API and gateway after the simulator received the original dispatch but before its delayed acknowledgment, reconciled that same effect against canonical simulator state, restarted the candidate API after reconciliation but before a final answer was durably written, then resumed the original task.

| Candidate | Repetitions | Completed after both restarts | Canonical receives | Effects | Independent final-answer check |
|---|---:|---:|---:|---:|---|
| Pydantic AI (A) | 3 | 3/3 `COMPLETED` | exactly 1 per task | same original effect ID, `CONFIRMED` | 3/3 accurately reported the Amber 16:00 reservation and confirmation |
| Lean loop (C) | 3 | 3/3 `COMPLETED` | exactly 1 per task | same original effect ID, `CONFIRMED` | 3/3 accurately reported the Amber 16:00 reservation and confirmation |
| Reduced Hermes (B) | not run | — | — | — | No claim: this CPU endpoint is below Hermes's minimum context. Existing CP69 deterministic-peer integration is not a recovery result. |

Every trial retained its original task ID and effect ID, canonical target state `ACCEPTED`, `receive_count=1`, and a persisted final response. No extra effects, unauthorized operations, or memory mutations were found. The resume trace includes the idempotent original `commitment_submit`, which returned the prior ledger result; it did not dispatch a second canonical operation. Pydantic's resumed responses used 5,621–5,634 prompt tokens, 111–115 completion tokens, and 21.2–50.9 seconds. Lean used 5,631–5,644 prompt tokens, 105–108 completion tokens, and 19.9–21.8 seconds. The interrupted process's in-memory usage counters were lost at SIGKILL; total per-task model-generation counts and first-turn tokens therefore remain unknown and are not inferred from aggregate llama.cpp logs. Each resumed turn made one idempotent commitment tool call; each trial also had an initial generation that dispatched the original operation, so at least two model generations occurred, but further retries/counts are not independently attributable. The evidence runner and sanitized records are [run_cp73_completion_recovery.py](../experiment/tests/run_cp73_completion_recovery.py) and [cp73_completion_recovery.jsonl](../experiment/results/cp73_completion_recovery.jsonl).

These trials distinguish an orchestrator/lifecycle defect from candidate behavior: both A and C produced correct final answers after restart, while trusted infrastructure verified completion independently of any model completion checkpoint. They do not qualify either harness generally, compare A against C, establish live GPU behavior, or test Hermes on a context-compliant recovery runtime.

## Fault injection and lifecycle regressions

The focused lifecycle/API/integration suites cover: exact one-of-one and multi-operation contract matching; confirmed partial completion rejected even if the model says the task is done; unrelated task/user/domain/target/effect/approval rejected; uncertain or not-yet-visible dispatch quarantined without replay; a one-shot canonical reconciliation HTTP failure followed by repeated reconciliation of the original effect; idempotent repeated submit; final-answer persistence and repeated finalization; provider failure after confirmed effect; contradictory terminal transition rejection; and memory writes staying `WAITING`. The gateway, rather than an orchestrator success flag or model trace, fetches and validates the persisted ledger, approval, and canonical simulator state.

The two CP72 gaps were exercised as follows:

1. **Reconciliation interruption:** integration injection makes the canonical simulator fail one reconciliation read. The gateway retains the effect as quarantined, and a later reconciliation confirms the same original effect without dispatch. This tests a recoverable network failure during reconciliation, but not a process kill at every internal reconciliation instruction boundary.
2. **Reconciled, response not yet persisted:** the matched A/C runner kills and restarts the candidate API after canonical reconciliation and before the final answer/task transition; all six resumes complete with one receive and durable response.

Canonical `NOT_RECEIVED`/unobservable cases remain quarantined and do not dispatch again in integration regression coverage. They were not run as a three-repetition scored model comparison for A and C. The persistent-acceptance path has three matched model repetitions each; fault tests establish recovery contracts, not candidate semantic behavior. The test runner currently preserves first-turn failure classification but loses exact first-turn usage at forced process death; this is an instrumentation gap to close before making generation-efficiency claims.

## Changed contract and safety boundaries

The completion criteria are created only through authenticated orchestrator task creation, normalized and stored on the existing task checkpoint, immutable thereafter, and unavailable to candidate tool schemas. Criteria enumerate the exact required target and details; their canonical digest is matched to the persisted effect and approval. The trusted gateway independently reads canonical simulator state and requires the same effect ID/target with at least one canonical receive. The task cannot complete if additional, missing, uncertain, rejected, or mismatched effects exist. No general-purpose success inference from natural language was added.

Task terminal states are stable: retrying the same terminal state is idempotent; contradictory terminal transitions are rejected. Consequential submissions require a running original task. Successful external effect, objective satisfaction, model response, durable response persistence, and delivery are recorded as distinct facts. In particular, `COMPLETED` means the bounded objective and response are durably proven/persisted; it does not claim the user has received the response.

## Provenance, runtime, and limitations

- Source parent: `39309dca28aca89ba08ab0184aab111865361dcd`; CP73 implementation source was the local uncommitted tree during trials. The publication commit and CI SHA are recorded in the repository history after publication.
- Model: Qwen3-8B Q4_K_M; `llama.cpp` image `ghcr.io/ggml-org/llama.cpp@sha256:fc9b506e89c1a1cfdd7bc056480f54dc657c1c04d76839a08642dc280b8ed2f6`; effective/training context 40,960; temperature 0; output ceiling 1,024; CPU-only. No Hypnos generation or GPU route was used.
- Candidate API image ID: `sha256:696a378e64bcc3ca97be76b80db8e4ab0f8deb3fec1822e282fc75e212cac0a4`; gateway image ID: `sha256:dde33528cef55c358c41a5b737a31c0be548490910a82bbed1923d8ad9b9b02c`. Images were built from the CP73 working tree before the trial.
- Regression verification: 73 discovered tests passed, 2 skipped; focused suites also passed (12 lifecycle, 15 candidate finalization, 5 gateway recovery, 1 gateway baseline). Python compilation and `git diff --check` passed. Exact public CI verification is recorded after publication.
- Trial resources used unique Compose project `hades-v3-exp-cp73-recovery`; results were inspected before project-scoped cleanup. Existing v3 and v2 Compose projects were not selected for cleanup.
- Exact task and independent persisted state are in the sanitized JSONL evidence. Synthetic approval identifiers are withheld. No private network addresses or credentials are included.
- CP72's published failures remain unchanged. No HADES v2 runtime was accessed. HADES-infra access/Cinder/firewall-helper drafts remain untouched and uncommitted; the HADES-infra remote/branch policy and Cinder's response remain unresolved.

## Next work and decision status

Next: investigate task-linked durable memory writes and fresh-context correction/retrieval, preserving `WAITING` until the memory effect has independent task-linked evidence. Then continue compound operations and protected-action recovery. CP73 does not resolve general arbitrary-task completion, response delivery acknowledgement, total generation accounting after forced termination, broad crash-state coverage, or the current v2 comparison baseline. ADR-010 remains **NOT READY**; production implementation remains unauthorized.
