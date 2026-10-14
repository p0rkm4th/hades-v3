# CP83 — Pydantic DBOSDurability with the HADES workspace

**Evidence class:** CONTRACT TEST
**Candidate:** separate A2 proof of concept; historical A/B/C scores unchanged
**Result:** 3/3 process-death recoveries passed with Pydantic's first-party DBOS integration

## Question

Can Pydantic AI's maintained `DBOSDurability` capability and Pydantic AI Harness `Shell` recover a confirmed gateway command without the CP82 test-only `StepPersistence` resume coordinator, while HADES remains the authority for task/effect state?

## Research before implementation

As of 2026-10-14, PyPI lists `pydantic-ai-slim==2.56.0`, `pydantic-ai-harness==0.56.0`, and `dbos==3.2.0`. The Harness 0.56.0 `dbos` extra points to the matching Pydantic AI `dbos` extra. The official Harness durable-execution guide says Shell, FileSystem, Coder, and RepoContext are supported with DBOS; it also says workspace operations replay recorded results and highlights stable run/workspace identity requirements.

Pydantic's current API requires a workspace capability to be present when `DBOSDurability` registers the agent. Passing a backend only to `Agent.run(workspace=...)` is rejected before model/tool execution. The passing test uses the documented `AbstractCapability.get_workspace` extension point to bind a fixture task ID to the existing authenticated HADES `WorkspaceBackend`. It does not use `LocalWorkspace`, unrestricted host shell, or a private capability hook.

Primary sources: [Pydantic AI Harness durable execution](https://pydantic.dev/docs/ai/harness/durable-execution/), [Pydantic AI DBOS integration](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/), [Pydantic workspace extension](https://pydantic.dev/docs/ai/core-concepts/workspace/), and [pinned PyPI metadata](https://pypi.org/project/pydantic-ai-harness/0.56.0/).

## Reproducible contract

- Python 3.11 image pinned to the CP79 runner digest.
- `pydantic-ai-slim==2.56.0`, `pydantic-ai-harness==0.56.0`, and DBOS 3.2.0. Dependencies reuse the existing pinned A2 and CP79 requirement files.
- DBOS metadata is a SQLite file in the runner's disposable `/tmp`; no DBOS service or persistent volume is created.
- The runner is non-root, read-only, capability-dropped, and attached only to the scoped Compose operator network. It has no database credential, host mount, Docker socket, or model-provider connection.
- A deterministic `FunctionModel` calls the existing authenticated workspace gateway. The DBOS workflow ID is derived from the HADES task ID. A test-only backend exits the worker after the gateway confirms the marker command but before Shell receives its result.
- On restart, DBOS replays the unfinished Shell operation. The HADES gateway matches the stable task/tool-call/dispatch identity and returns the original confirmed effect. An independent gateway read verifies one marker; cleanup uses a distinct identified command.

Three independent tasks passed. Each had two deterministic model generations, one canonical candidate command effect, one marker after recovery, and three confirmed workspace effects after independent read and cleanup. Repeating `DBOS.get_result()` for the completed workflow returned the same answer without another model generation or effect. The A2 task remained `RUNNING`; task finalization and user-facing delivery are outside this experiment. The first attempt, which passed `workspace=` only at run time, was rejected before any model generation or workspace dispatch. The test was corrected to register the documented workspace capability before DBOS launch.

The first repeated-result assertion draft failed because it counted only the original command and forgot that the independent oracle read itself creates a second effect. Inspection confirmed the second row was that read and the marker still contained one write. The test now snapshots the two expected effect rows before repeated result retrieval and verifies that the rows and model-call count are unchanged afterward; the corrected test passed in a fresh project.

The exact fixture project and its images, networks, and volumes were removed after the run. HADES v2 and Tallowmere's CP75/CP80 fixtures were untouched. No Hypnos generation or privileged operation occurred.

## What this establishes

This demonstrates that the pinned upstream Pydantic AI/Harness combination can use first-party DBOS durability around a HADES-backed Shell workspace for this one post-confirmation crash window. The CP83 path uses DBOS replay and the gateway's existing effect identity; it does not use `StepPersistence` or the CP82 resume gate. It therefore provides a plausible way to remove those two recovery-specific pieces from a future DBOS-backed A2 variant.

The HADES adapter and existing gateway replay contract are still required. DBOS metadata is execution history, not the HADES task/effect ledger. DBOS did not finalize the task. This test does not establish exactly-once arbitrary shell behavior, safe recovery of a quarantined/unknown result, approval behavior, provider-error handling, semantic model capability, or production database operations. The successful injected failure had a canonical `CONFIRMED` result. No live model was used.

The CP82 A2 path and CP79 direct DBOS gateway probe remain intact. Their outcomes are not rescored. Although CP83 is evidence that first-party DBOSDurability composes with Harness Shell, it is not yet an apples-to-apples maintenance-cost comparison: the current test has no uncertain-effect replay case or trusted task finalization. Do not adopt DBOS until those gaps are tested and the operational cost of its durable metadata store is compared against the candidate's existing recovery path.

## CP83 follow-up — quarantined timeout and worker restart

A second isolated run exercised an actual uncertain command: the synthetic shell wrote one marker and then exceeded the workspace runner's 20-second limit. The gateway persisted one `QUARANTINED` effect. The test worker exited after receiving the gateway result and before Harness saw it. On restart, DBOS replayed the original identity; the gateway refused to redispatch it. The pinned agent run ended in `WorkspaceUnavailableError`, without a final answer. The task remained `RUNNING`; its original effect remained `QUARANTINED` with the same ID.

A separate observer task read the workspace and found exactly one marker. Repeating the failed resume produced no additional model generation or HADES effect. The observer then removed the synthetic marker. This proves fail-closed replay behavior and no duplicate execution for this timeout path, but it does **not** reconcile or complete the original task. An initial test assertion expected a model-generated uncertainty response; the observed runtime exception showed that was not the actual behavior, so acceptance was corrected to preserve the exception as failure evidence rather than treating it as a product pass.

The isolated DBOS runner intentionally bypasses the HADES candidate API orchestrator, so that task remained `RUNNING`. The existing API exception path classifies a quarantined effect as `WAITING` for reconciliation and a confirmed effect with lost response as `WAITING` for response recovery. This classification was extracted without changing its decisions and now has direct regression coverage; the Pydantic/Harness/DBOS flow has **not** yet been run through that API path end to end. The candidate finalization suite passed 24 tests after the addition.

The quarantine case is a distinct single contract trial, not part of the 3/3 confirmed-result repetition count. Both unique CP83 projects were removed by project-scoped cleanup; CP75/CP80 remained at 14 running containers and disk remained at 39 GB. The quarantined effect is retained only in the disposable experiment database, which was removed with its project.

## Next decision-changing test

The quarantined path now proves no duplicate dispatch but cannot continue after the exception. The next useful test is a narrowly scoped trusted recovery/reconciliation path for a shell operation with independently checkable canonical state; arbitrary shell still requires review. After that, compare the minimum code and operational configuration for DBOSDurability versus the current StepPersistence path using the same task/effect contract. ADR-010 remains **NOT READY**.
