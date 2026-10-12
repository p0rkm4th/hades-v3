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

The PostgreSQL/Grocy synthetic fixture and scoped gateway passed their documented checks. Four targeted commitment executions and the disposable shell/Git workspace test passed with independent fixture verification. The Playwright-compatible UI exists and has a mocked browser smoke test; candidate integration is partial. The lean loop and Pydantic AI each completed one live, read-only kitchen query against Amber's fixture through the shared gateway; the observed pantry values matched the seeded state, and SQL read-back found no effects for those task IDs. These one-shot probes are integration checks only, not comparable trials. The reduced Hermes service starts and its bearer-authenticated API health/models routes return HTTP 200, but its first candidate request is rejected before tool execution because Hermes requires 64,000 context tokens while the shared Qwen3-8B endpoint reports `n_ctx=40,960` and `n_ctx_train=40,960`. Do not misstate the server capacity or count this as a scenario outcome. No candidate has completed the three-trial scenario protocol, interruption recovery, maintenance exercise, stronger-model comparison, or owner evaluation. The v2 living source recheck remains source-only and is recorded separately.
