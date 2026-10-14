# CP82 — identity-bound A2 workspace replay

**Result:** a narrow retry path now prevents a duplicate dispatch when the pinned Pydantic AI Harness resumes the same persisted tool call after a worker dies. Unknown operations remain quarantined. This is contract evidence, not live-model or general shell qualification.

## Defect and correction

CP81's synthetic restart probe sent the same task, command, and `operation_id` through two gateway processes. The gateway ignored that field, created two confirmed effects, and the workspace contained two markers. The original reproduction remains in [`cp81_workspace_replay_probe.json`](../experiment/results/cp81_workspace_replay_probe.json).

CP82 adds a small A2-only Harness wrapper. It forwards `RunContext.tool_call_id` through the upstream `Shell` capability and command-only `WorkspaceBackend`; the adapter hashes that ID with the HADES task ID and adds the resulting identity to the gateway request. The model cannot choose or change the identity. No new table, scheduler, task manager, or effect ledger was added.

The gateway validates the SHA-256 identity, binds it to a canonical digest of the command in the existing `effects.request`, and serializes identity checks under the existing task row lock. An exact replay of a `CONFIRMED` request returns its saved result and original effect ID. A changed command under the same identity returns HTTP 409. A prior unresolved workspace effect is durably moved to `QUARANTINED` and blocks both same-ID and different-ID dispatch attempts. The gateway commits the effect as `DISPATCHED` before calling the runner, so a gateway crash in that window leaves a conservative unresolved record rather than authorizing another command.

## Verification

- `experiment/tests/test_gateway.py`: all eight database-backed gateway tests passed. The workspace endpoint rejects calls without a stable operation identity. The new case verified one exact confirmed replay, same effect ID, rejection of changed arguments, one canonical marker, and quarantine of both same-ID and new-ID retries against a seeded unresolved effect. Existing schema already has the required JSONB request field; no migration was needed.
- `experiment/tests/test_workspace_flow.py`: the existing real shell/Git contract passed with trusted per-call test identities; the regression is included in CI. Its first run caught a synthetic marker left by the gateway test; the gateway test now removes only its exact marker through a separate identified effect, and both suites pass on rerun.
- `test_operation_identity_context.py`: the actual pinned Harness `Shell` call forwarded its tool-call ID through asynchronous workspace dispatch in a network-disabled container.
- `test_step_persistence_interrupted_shell.py`: a worker died after a synthetic dispatch. The SQLite `StepPersistence` journal retained the original tool-call ID as `started`; its interrupted history exposed the call. The caller must inspect unresolved effects before choosing a continuation snapshot.
- `test_confirmed_command_recovery.py`: the A2 worker died after the gateway confirmed a marker command but before Shell received the response. A new worker resumed the persisted tool call, the gateway returned the original effect, and an independent workspace read found exactly one marker. The marker was then removed through the gateway. The canonical HADES task intentionally remained `RUNNING`; this test measures command recovery, not lifecycle finalization.
- After restarting the gateway service with PostgreSQL and workspace state retained, exact replay returned the same confirmed result, changed arguments were rejected, and an independent read found the marker once.
- The strict deterministic A2 Shell-only repository probe passed with four model calls, three candidate commands, and an independent test/source oracle. Candidate task state intentionally remained `RUNNING`; this is contract evidence, not a new model comparison.
- The A2 uncertainty test passed: one quarantined result produced no same-turn retry.

Project-scoped cleanup completed. A post-cleanup inventory found no CP82 containers, networks, volumes, or locally built images; CP75 and CP80 containers remained healthy. Root filesystem free space was 44 GB after cleanup. The disposable project was separate from both shared stacks. No Hypnos inference, privileged firewall work, or HADES v2 access occurred.

## Limits and next gate

The gateway now requires a stable operation identity and rejects missing identities, preventing legacy callers from silently bypassing replay protection. This prevents redispatch only when the caller presents the same task-bound tool-call identity. It does not make arbitrary shell work exactly-once. A regenerated model call with a new tool-call ID is a distinct operation; therefore the resume coordinator must inspect `StepPersistence` unresolved records and recover the original call or reconcile it against the HADES effect before prompting the model again. An unknown workspace result has no general canonical reconciliation path and must remain quarantined for review.

`StepPersistence` continues to show the original run's tool effect as `started` after replay under a new Harness run ID. The orchestrator still needs to reconcile that stale journal entry against the confirmed HADES effect. The historical A, C, and Hermes adapters do not provide the CP82 invocation identity; workspace calls through them now fail closed until their runtime adapters add a persisted identity. This is a compatibility gap, not a scored candidate failure. No memory, task-completion, or semantic model score changes are implied.

The tests are in the A2 CI path. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; ADR-010 remains **NOT READY**.
