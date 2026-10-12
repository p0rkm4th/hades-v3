# Experiment plan

## Purpose and decision boundary

Determine whether one of three agent harness foundations is ready to advance for ADR-010 under the frozen HADES v3 product and architecture constraints. This campaign stops at an evidence-backed recommendation. It does not authorize full product implementation. HADES v2 remains independently maintained and is a living comparison control; it is not assumed to be deprecated or inferior.

## Candidate set

1. A thin HADES-owned lifecycle harness using Pydantic AI for model/tool protocol handling.
2. A reduced Hermes runtime whose product state and authority are subordinate to shared HADES contracts.
3. A deliberately small HADES-owned model/tool loop using maintained provider clients and native operator interfaces.

Evaluate the current HADES v2 product separately. Do not rebuild v2 as a fourth candidate.

## Shared disposable boundary

Candidates must use equivalent shared contracts and privileges for durable task/effect state, household inventory and shopping data, synthetic infrastructure health, two isolated synthetic users, scoped memory and correction, a disposable code repository, a Playwright-compatible web app, and a protected simulated external commitment. Use independent canonical outcome verification. Do not connect production secrets or household data.

## Scenario families

1. Natural kitchen inventory questions, including held-out wording and typos.
2. Compound grocery changes with independent resulting-state verification.
3. Current infrastructure questions with stale and unavailable observations.
4. Multi-turn follow-up, correction, and remembered references.
5. Shell/Git/file work with an executed test and verified result.
6. Durable task continuation after deliberate runtime interruption.
7. Denial of unauthorized consequential work without blocking harmless work.
8. Ambiguous external commitment, quarantine, and safe reconciliation.

## Measures and controls

Record verified task success, false completion, unauthorized attempts and execution, unnecessary clarification, relevant context selection, first meaningful response latency, total completion time, tool/model calls and token overhead, recovery behavior, integration complexity, and debugging difficulty. Reset fixtures consistently. Use common model endpoints, versions, and bounded contexts. Keep held-out language variations out of implementation tuning.

For qualifying candidates, apply the historical review's provenance labels, three-trial comparison method, independent verification, safety disqualifiers, 18/20 floor, owner usability and maintenance comparisons, and pivot/rejection rules. Compare v2 both with its recorded baseline and eligible current observations. Separate controlled trials from unmatched live observations.

## Decision rules

Eliminate candidates with fundamental authority conflicts, competing task state, invasive patching requirements, safety disqualifiers, or consistently worse useful outcomes. Do not recommend a winner from a synthetic pass alone when it conflicts with owner acceptance. If no candidate qualifies, report ADR-010 NOT READY and identify the evidenced shared blocker. Record owner judgments separately; agent-generated judgments do not establish owner acceptance.

## Current evidence status

The shared synthetic infrastructure, commitment, workspace and UI fixtures have their previously recorded test evidence. Candidate A and C completed the repeated family 1 screen (three attempts for each of three inventory wordings) on Qwen3-8B. For family 2 trajectory 1, each completed three fresh Qwen3-8B attempts with confirmed effects and matching post-write lists. A second compound trajectory failed safely 3/3 on 8B before canonical-name guidance; after a general shared-contract correction, both candidates made the same partial change in 3/3 attempts, omitting Pasta while reporting the list updated. All six candidate effects accurately confirmed only the partial requests; operator and SQL checks exposed the omitted item. On Qwen3-14B, each candidate completed that same trajectory 3/3 with exact task/effect linkage and verified final state. The local CPU profiles report `n_ctx=40,960` and `n_ctx_train=40,960`. A bounded homelab discovery found a functioning Qwen3.6 35B GPU endpoint with an observed effective context of 65,536 and live GPU utilization during generation; four short calls returned 27.65–37.60 tokens/s. The value meets Hermes's 64,000-token floor, but the candidate containers cannot reach it across the deliberately internal Compose network. One matched attempt per candidate on a new private 8B wording exceeded five minutes without a tool call; C returned HTTP 502 and A was operator-cancelled after six minutes. Neither attempt created an effect, and both tasks required operator closure. It remains an incomplete one-attempt matched diagnostic, not comparative evidence. The task-lifecycle fix is in candidate API commit `1335470a79fb54f4f4ebcef36011270489f6f993`; the shared canonical-name correction is in commit `4f9d6c4cab0816d4172870ba2f44b852ca783bae`. This is limited evidence from portions of families 1 and 2, not overall qualification or owner acceptance. Other family 2 variations, families 3–8, interruption recovery, safety qualification, maintenance comparison, the 20-family corpus and owner review remain pending. The v2 living-source record is source-only.

At this checkpoint, A and C each completed a third family 2 compound trajectory (add Pasta 2, remove Milk) in three reset trials on the shared Qwen3-8B CPU endpoint. All six tasks persisted `COMPLETED` with exact tool traces, linked one `CONFIRMED` effect, and had SQL `verified_after` plus operator list reads matching Oats 1 / Pasta 2. The final API profile bounds each model request to 50 seconds, each turn to six model requests, four tool calls, and 1,024 completion tokens; a reusable 0.01-second forced-timeout probe also showed that A and C save failed tasks with operator-review and possible-effect-uncertainty flags. A limited family 3 prompt correctly preserved fresh/stale/unknown fixture states in 3/3 attempts per candidate. Neither scenario qualifies its full family. Candidate B remains blocked on the 40,960-token CPU context, while the verified 65,536-token GPU endpoint is unreachable from candidate containers and had an unidentified active client. V2 `main` was rechecked at `63b62a594b1a57e66dd9f59f9efe50c4ef9a4538`; its public source still reports an owner-reported read-routing/memory-mutation issue that is not independently reproduced. Restart recovery, families 3–8, full historical-corpus qualification, maintenance comparison, and owner judgments remain outstanding.

After that checkpoint, two temporary synthetic `ERROR` infrastructure observations were used for matched source-unavailable screens. On the first wording, A and C each completed three read-only attempts on the same CPU endpoint and configuration, explicitly stating that health could not be determined and using only `infrastructure_read`. On a second wording asking them to distinguish stopped telemetry from a confirmed failure, both candidates called the target a confirmed operational failure in all three attempts, despite a null health value and source-unavailable fixture. Durable task checks passed; the failed screen created no effects, the temporary row was removed, and the original seed was verified. This is a repeatable shared false-diagnosis signal, but not full family qualification. At the same checkpoint, the v2 living source remained at `63b62a594b1a57e66dd9f59f9efe50c4ef9a4538`; its campaign records the Open WebUI P0 acceptance as closed while the separate owner-reported routing/reset issue and homelab byte-parity checks remain open. See Checkpoints 15–16 in the comparison report and [V2_CONTROL_BASELINE.md](V2_CONTROL_BASELINE.md).

The shared tool schema was then clarified in v3 commit `8b36e42e70a83e61b35f250d3e3bacba67ea3d77`: `ERROR` means the observation source failed to provide data and is not evidence of target health. On the same alternate wording, A returned clean uncertainty in 3/3 attempts; C still made a contradictory ERROR-implies-confirmed-failure statement in 3/3 attempts, despite also saying target health was not confirmed. All six calls had only `infrastructure_read`, completed durably, and created no effects. This is a limited response-level improvement, not proof of generalization or a harness decision. See Checkpoint 17.
