# CP78 — Pydantic AI Harness workspace composition

**Classification:** CONTRACT TEST; not live-model qualification
**Candidate:** Separate A2 proof of concept; historical Candidate A was not changed or rescored
**Date:** 2026-10-14

## Question

Can upstream Pydantic AI Harness `Shell` and `FileSystem` perform a bounded repository edit through HADES's existing authenticated workspace gateway, while the gateway remains the only task/effect authority?

## Setup

The disposable candidate used `pydantic-ai-harness==0.56.0` and
`pydantic-ai-slim==2.56.0`, with the exact transitive pins in
[`requirements.txt`](../experiment/spikes/a2_gateway_workspace/requirements.txt).
The runner image was based on
`python:3.14-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83`.
The final local runner image ID was
`sha256:6178ef27abab599d617c165b2a57505ff5d595e2102f8655bac3ad6fd831ee4d`.
The adapter implements the supported command-only `WorkspaceBackend` contract
and sends commands to the authenticated `workspace_exec` gateway for the
original task. It rejects environment and timeout overrides that the gateway
cannot honor. No local shell backend, host mount, SSH, Docker socket, live
model, Hypnos endpoint, or HADES v2 resource was used.

The candidate container was read-only, dropped all Linux capabilities, and was
attached only to the internal operator network. Workspace and database service
names did not resolve from that candidate network. This is a bounded topology
check, not a complete adversarial egress qualification.

The deterministic `FunctionModel` read a synthetic Python file and its hash,
conditionally wrote the correction, and ran its tests. An independent oracle
then reran tests, checked the resulting source, and inspected the gateway task
and effect records. The task intentionally remained `RUNNING`; completion was
outside this workspace-composition experiment.

## Results

| Repetition | Model calls | Candidate workspace commands | Oracle command | Confirmed workspace effects | Independent source/tests |
|---|---:|---:|---:|---:|---|
| 1 | 4 | 18 | 1 | 19 | Pass |
| 2 | 4 | 18 | 1 | 19 | Pass |
| 3 | 4 | 18 | 1 | 19 | Pass |

All three runs had the expected task identity, only `WORKSPACE_COMMAND` effects,
and no memory or other effects. Candidate and oracle operations were confirmed
in the gateway ledger. The tested source and unit tests matched the independent
fixture oracle. Project-scoped containers, networks, volumes, runner image, and
temporary probe environment were removed after the runs.

## Interpretation and limits

The supported Harness abstractions can use the HADES workspace gateway without
creating a second effect authority. This is useful integration evidence, but
the deterministic peer does not establish model quality, task finalization,
owner usability, or scored Candidate A performance.

The combined `Shell` plus `FileSystem` profile incurred 18 candidate gateway
commands for this small task. That overhead is material and should be compared
against a Shell-only profile before choosing the more elaborate composition.
The gateway currently fixes the command environment and 20-second timeout;
the adapter rejects unsupported overrides. Uncertain command outcomes are not
retried by the adapter. Background work, recovery of quarantined workspace
commands, full egress resistance, and upstream `Coder` behavior remain
unqualified. `Coder()` was not used; its inspected default shell wait exceeds
the existing gateway bound and is incompatible as configured.

Two setup defects occurred before the three scored repetitions and were
corrected: the initial `FileSystem` declaration omitted its read tool, and the
probe initially assumed a 64-character hash although the Harness exposed a
12-character hash. Both failed before fixture mutation or candidate effect
dispatch. The corrected final profile passed three clean repetitions.

The prior docs-only commit `7e66e62cb6ef755f7969f0ff2ff6b17aba228111` had an
exact-SHA CI failure at “Start disposable fixtures.” The unauthenticated log
API withheld the cause. An equivalent fresh local Compose startup and uncached
build of affected images succeeded; these do not identify the hosted-runner
cause. Preserve that failure as unresolved. The new A2 CI path is independently
project-scoped and always cleans up; its exact-SHA result is tracked after
publication.

## Disposition

Keep A2 as a separate replacement hypothesis, not a replacement of historical
Candidate A. The narrow gateway-backed `WorkspaceBackend` is viable for further
evaluation. Before accepting the composition, compare Shell-only command
efficiency and exercise failure/recovery semantics using the existing gateway
and effect ledger. Do not add a new file authority or weaken the gateway
contract. ADR-010 remains **NOT READY**.
