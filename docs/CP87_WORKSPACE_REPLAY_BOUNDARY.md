# CP87 — Workspace command replay boundary

**Date:** 2026-10-14  
**Scope:** Source review and isolated A2 recovery contract tests; no gateway deployment or shell command against a real workspace  
**Classification:** Contract tests plus source review

## Existing mechanism

The shared workspace gateway uses the existing task/effect ledger. Candidate adapters bind an operation ID to the task ID and persisted model tool-call ID; the A2 Harness adapter also adds a deterministic ordinal for multiple backend commands from one Shell call. The gateway stores a digest of the command with the effect. Under the same task and operation ID, a matching confirmed effect returns its stored result and effect ID, a changed command is rejected, and an uncertain effect is quarantined. It writes `DISPATCHED` before runner I/O and blocks another workspace dispatch while an unresolved command exists.

This prevents blind redispatch when the original call identity survives. It does not establish exactly-once execution for arbitrary shell effects. A new tool-call identity is a distinct operation; an effect ledger cannot infer whether identical command text with a new identity means a retry or an intentional second command. Quarantined shell effects have no generic canonical-state reconciler, so unknown outcomes must remain blocked for inspection/review.

## Restart evidence and limits

The pinned A2 Harness `StepPersistence` snapshot preserves the interrupted `tool_call_id`. Its interrupted continuation also offers a default snapshot that omits the pending call, so the caller must inspect unresolved effects before choosing a resume path. The A2 test-only resume gate allows only an absent pre-dispatch call or matching confirmed original call, and blocks `WAITING` tasks and any unresolved effect. This gate is not integrated into the scored A/C runtime.

Two isolated tests passed in cached A2 runner image `sha256:90331becfbeb7bd15a10623367b457466963cc147ba9fd4e15b037650d6c3387`, with network disabled, read-only source, no capabilities, and disposable `/tmp`:

- `test_resume_gate.py`: absent or confirmed original calls allowed; mismatched task/state, absent pending call, and uncertain effects blocked.
- `test_step_persistence_interrupted_shell.py`: after the synthetic marker command and worker death, StepPersistence retained one started effect and the original tool-call ID; no replay occurred. The default continuation omitted that interrupted call.

Previously recorded A2 confirmed-command recovery evidence shows that resuming the original persisted call returns the same confirmed effect rather than writing a second marker. These are deterministic synthetic contract observations, not live-model or production-runtime qualification.

## Candidate implications

- **A2:** best-supported route for same-call process recovery because the upstream step journal preserves the call identity. The CP83 DBOS and CP84 finalizer probes further exercised confirmed-result replay; unknown shell outcomes still require review.
- **A / C:** adapters forward provider tool-call IDs to the gateway, but persistent conversation/step identity and cross-process answer recovery are not qualified. Since CP88, the shared candidate API parks a sequential stateless resume after a confirmed workspace effect instead of issuing a new model turn. Since CP90, the gateway permits new dispatch only for `RUNNING` tasks, preserves exact confirmed replay, and quarantines unresolved effects even if a candidate reaches the route directly. This closes the previously identified **sequential** blind-replay path; it does not restore the original answer or establish safe concurrent same-task turns.
- **B / Hermes:** the current MCP proxy does not supply the workspace operation identity and fails closed for that route.

No additional ledger, scheduler, or command authority was introduced. The current sequential A/C path is fail-closed after a confirmed effect or unresolved outcome, but it does not resume the original answer. Automatic deduplication by command digest would still conflate retries with intentional repeated commands. The next A/C recovery experiment should serialize same-task turns, preserve and authenticate the original step identity, inspect the canonical task/effect snapshot before continuation, and keep outcomes without a canonical reconciler quarantined. No additional test was run in CP92; this is a source comparison against CP88/90 implementation and their already published gateway tests, not new runtime evidence.
