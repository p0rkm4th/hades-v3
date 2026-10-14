# A2 Harness workspace integration probe

This probe uses Pydantic AI Harness `Shell` and `FileSystem` with a command-only
`WorkspaceBackend` that sends each operation to the authenticated HADES
`workspace_exec` route. It does not attach `LocalWorkspaceBackend` or execute
model-provided commands on the agent host. The model is a deterministic
Pydantic `FunctionModel` peer; this is protocol/integration evidence, not
candidate-model qualification.

The scripted Harness reads the current file and hash through `FileSystem`,
conditionally writes the correction through `FileSystem`, then runs the tests
through `Shell`. An independent check reruns the tests and verifies the source,
then reads the task/effect ledger through the gateway. The task intentionally
remains `RUNNING`: this probe tests workspace composition, not task finalization.

Limitations: the gateway runner fixes its environment and a 20-second command
timeout. The adapter rejects unsupported environment or timeout settings and
does not implement a retry for a command with an uncertain outcome. Background
commands, recovery of a quarantined workspace command, container egress
enforcement for an A2 container, and live model behavior are not qualified.

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
