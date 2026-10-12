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

The shared synthetic infrastructure, commitment, workspace and UI fixtures have their previously recorded test evidence. Candidate A and C completed the repeated family 1 screen (three attempts for each of three inventory wordings) on Qwen3-8B. For family 2 trajectory 1, each completed three fresh Qwen3-8B attempts with confirmed effects and matching post-write lists. A second compound trajectory failed safely 3/3 on 8B before canonical-name guidance; after a general shared-contract correction, both candidates made the same partial change in 3/3 attempts, omitting Pasta while reporting the list updated. All six candidate effects accurately confirmed only the partial requests; operator and SQL checks exposed the omitted item. On Qwen3-14B, each candidate completed that same trajectory 3/3 with exact task/effect linkage and verified final state. The local CPU profiles report `n_ctx=40,960` and `n_ctx_train=40,960`. A bounded homelab discovery found a functioning Qwen3.6 35B GPU endpoint with an observed effective context of 65,536 and live GPU utilization during generation; four short calls returned 27.65–37.60 tokens/s. The value meets Hermes's 64,000-token floor, but the candidate containers cannot reach it across the deliberately internal Compose network. A new private C/8B wording attempt exceeded five minutes and returned HTTP 502 before a tool call; no effect occurred, and the task needed operator closure. It remains an incomplete single-candidate diagnostic, not comparative evidence. The task-lifecycle fix is in candidate API commit `1335470a79fb54f4f4ebcef36011270489f6f993`; the shared canonical-name correction is in commit `4f9d6c4cab0816d4172870ba2f44b852ca783bae`. This is limited evidence from portions of families 1 and 2, not overall qualification or owner acceptance. Other family 2 variations, families 3–8, interruption recovery, safety qualification, maintenance comparison, the 20-family corpus and owner review remain pending. The v2 living-source record is source-only.
