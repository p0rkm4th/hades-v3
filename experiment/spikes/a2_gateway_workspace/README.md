# A2 Harness workspace integration probe

This probe compares two profiles of pinned Pydantic AI Harness `0.56.0` and
Pydantic AI `2.56.0`: `shell_filesystem` exposes `Shell` and `FileSystem`, while
`shell_only` exposes only `Shell`. Both use the same command-only
`WorkspaceBackend` that sends every operation to authenticated HADES
`workspace_exec`. Neither attaches `LocalWorkspaceBackend` or executes a
command on the agent host. The peer is a deterministic Pydantic `FunctionModel`,
so results are contract evidence, not candidate-model qualification.

Both profiles use identical task wording and fixture data. `shell_filesystem`
reads and hashes the file through `FileSystem`, conditionally writes through
`FileSystem`, then tests through `Shell`. `shell_only` reads/hashes, conditionally
updates against the observed hash, and tests using three ordinary shell
commands. An independent oracle reruns tests, verifies source and reads the
task/effect ledger. The task intentionally remains `RUNNING`: this probe tests
workspace composition, not task finalization.

Three matched pairs are counterbalanced in CI. CP80 also has one earlier
exploratory run per profile; all eight local tasks have preserved task IDs and
independent outcome summaries in [`cp80_a2_workspace_profiles.jsonl`](../../results/cp80_a2_workspace_profiles.jsonl).

Limitations: the gateway runner fixes its environment and a 20-second command
timeout. The adapter rejects unsupported environment or timeout settings and
does not automatically retry a command. Background commands, recovery of an
uncertain/quarantined workspace command, container egress enforcement for an A2
container, and live model behavior are not qualified.

CI injects one `QUARANTINED` result through the real workspace adapter and
Pydantic AI Harness `Shell` capability. The pinned runtime propagates
`WorkspaceUnavailableError` and aborts the turn; the regression asserts exactly
one gateway request and no second model turn. This is contract evidence that
the command is not blindly retried in that runtime. It does not recover or
finalize the task, establish cross-process recovery, or qualify live-model
behavior.

## Invocation identity and bounded recovery

The A2 adapter includes `HadesOperationIdentity`, a supported Harness toolset
wrapper that forwards the active `tool_call_id` through the command-only
`WorkspaceBackend`. The adapter hashes it with the HADES task ID; the model does
not supply this field. `workspace_exec` stores that identity and a canonical
command digest in the existing `effects.request` record. Exact confirmed replay
returns the saved result and effect ID, a changed request under that identity
is rejected, and any unresolved workspace effect blocks another dispatch for
the task. The gateway persists `DISPATCHED` before calling the workspace
runner, so a gateway crash at that boundary remains quarantined rather than
being replayed.

`test_confirmed_command_recovery.py` kills an A2 worker after the gateway has
confirmed a synthetic marker command but before Shell receives the result. It
loads the interrupted Pydantic AI Harness `StepPersistence` snapshot, resumes
the original tool-call identity, and independently reads the marker. The same
effect is returned and the marker appears once. Separate offline tests verify
the wrapper identity path and the unresolved-effect journal. This is bounded
contract evidence, not exactly-once arbitrary shell execution: an unknown
command outcome remains quarantined, and the task orchestrator must inspect
unresolved StepPersistence effects before choosing a continuation snapshot.
The legacy A/C adapters do not yet provide this invocation identity.

Run this only with a fresh project-scoped fixture stack, including
`compose.a2-harness.yaml` and the `a2-harness` profile. The candidate test
container attaches only to the internal operator network; it does not share the
workspace or fixture-backend networks. Remove only that named project and its
volumes after the probe.

From `experiment/`, the local sequence is:

```sh
docker compose -p hades-v3-exp-a2-local --profile a2-harness -f compose.yaml -f compose.a2-harness.yaml up -d --build postgres grocy commitment-simulator workspace-amber workspace-cobalt tool-gateway
docker compose -p hades-v3-exp-a2-local --profile a2-harness -f compose.yaml -f compose.a2-harness.yaml run --build --rm --no-deps a2-harness-runner
docker compose -p hades-v3-exp-a2-local --profile a2-harness -f compose.yaml -f compose.a2-harness.yaml down --volumes --remove-orphans
```
