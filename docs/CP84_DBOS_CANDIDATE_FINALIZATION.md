# CP84 — DBOS replay through the HADES candidate finalizer

**Date:** 2026-10-14
**Base checkout:** `8b7593413fbcc417ee6c3a5ae9aee965b31b94f7` plus the CP84 experiment sources in this checkpoint
**Classification:** deterministic **CONTRACT TEST**, not a live-model result or A/B/C score
**Result:** 3/3 clean matched crash-and-resume trials passed after two test-driver defects were found and preserved

## Question

Can first-party Pydantic AI `DBOSDurability` carry the existing Pydantic candidate tool contract through two process-death windows and still let HADES's existing gateway finalizer decide task completion from the durable task/effect ledger?

## Configuration and isolation

- Pydantic AI `2.56.0`, DBOS `3.2.0`; the deterministic `FunctionModel` was named `cp84-strict-peer`. No live provider, model server, GPU, or Hypnos request was used.
- The runner reused `experiment/candidates/api.py`'s `VISIBLE_TOOLS`, `gateway_call`, `SYSTEM_PROMPT`, and `finalize_turn`. A Pydantic AI `Agent` ran inside one DBOS workflow with a three-generation ceiling and sequential tool execution. The task ID determined the DBOS workflow ID.
- The test was not the candidate HTTP `Handler` and did not use the Harness `Shell` capability. It qualifies Pydantic Agent + DBOS + shared gateway/finalizer composition only. CP83 separately tested Harness Shell + DBOS without the HADES finalizer.
- The candidate runner was non-root, read-only, dropped all capabilities, had no Docker socket or model endpoint, and attached only to the project-scoped internal operator network. In-run checks confirmed it could resolve the gateway but not the database, workspace, or Grocy service names.
- A fresh `hades-v3-exp-cp84-dbos-finalization` Compose project was preflighted with no host ports or fixed container names. Five project-scoped volumes and four internal networks were removed with the exact project name after the run. No CP75/CP80 resources were touched.
- Compose input hashes: `compose.yaml` `04bfac410f58bb271d10876de424a23c99659e184c048cb35cafeb83e1f7f7d5`; CP83 overlay `432848240d61f62ce9b00fc1b2c64a2cd8437e729c674362fb3ab903d5f6fdba`; CP84 overlay `32b54006806796ad9fcaada3d3db14af44d049ff16546675ae63d525c544783b`. Runner image ID: `sha256:392cbe29b22b43825f47c62a25fb508ecf2842e5c3ab80d458cc26568fb5b2d9`.

## Procedure and results

Each successful repetition used the same synthetic task, tool schemas, fixture, and deterministic peer:

1. The peer requested one `workspace_exec` that appends a single marker.
2. The test process exited immediately after the gateway returned `CONFIRMED`, before the Pydantic tool call received its result.
3. A restarted process resumed the same DBOS workflow and original tool-call ID. The HADES gateway returned the original effect result.
4. The peer emitted one explicit completion checkpoint and a useful final answer.
5. The process exited after DBOS had durably returned the workflow result but before calling `finalize_turn`; the HADES task remained `RUNNING` with its one confirmed effect.
6. A later process fetched the same DBOS result and called the existing HADES finalizer. The task became `COMPLETED`.
7. A separate observer task read exactly one marker (`x`). Repeating resume/result retrieval did not add a generation or effect, and the finalizer preserved the terminal task. The marker was removed through an identified workspace operation.

All three repetitions passed. Each used exactly three deterministic model generations and two tool calls (`workspace_exec`, `task_checkpoint`), retained the same task/effect identities, recorded one confirmed workspace effect, and made zero memory mutations. The final answers matched the scripted oracle and the independent workspace read.

Per-trial records, including two earlier failed test-driver attempts, are in [`cp84-dbos-candidate-finalization-20261014.jsonl`](../experiment/results/cp84-dbos-candidate-finalization-20261014.jsonl).

## Preserved test-driver failures

- The first attempt called Pydantic's `RunUsage` property as a method. It stopped before finalization with the HADES task still `RUNNING`; the one effect was `CONFIRMED`. An independent observer verified one marker, then removed it. This is a test-driver/API misuse, not a candidate score.
- The second attempt removed the result prefix twice. The task had in fact reached `COMPLETED` with one confirmed effect, but the driver lost the result text and failed parsing. An independent observer again verified one marker, then removed it. This is invalid harness evidence, not a semantic pass.
- After fixing those driver defects, three new clean repetitions passed. The failed trials remain in the result JSONL and are not counted as passes.

## What this establishes

This provides the first deterministic integration evidence that a Pydantic agent run using the shared HADES tools can cross a confirmed-effect process death, recover the same tool-call identity, cross a second process death before HADES finalization, and complete through the existing trusted finalizer without duplicate execution. DBOS execution history remains separate from, and subordinate to, the HADES task/effect ledger.

The test does **not** show a live-model ability, Hermes compatibility, A/C/B ranking, arbitrary-shell exactly-once behavior, uncertain-effect reconciliation, full container or host restart, HTTP Handler delivery, or a reduction in maintained production code. DBOS used SQLite in runner tmpfs; production persistence, workflow-history privacy/retention, payload protection, retries, cancellation, and operations remain unqualified. No DBOS service was installed or adopted.

## Resource cleanup

Post-cleanup inventory: zero CP84 containers, networks, and volumes; 14 CP75/CP80 containers remained running. Disk remained at 44 GB free. The five uniquely tagged CP84 images were retained for the cleanup lead to review; no image pruning was performed. No shared, v2, Hypnos, or production resources were modified.

ADR-010 remains **NOT READY**. The next useful test is not another success-only replay: compare this integrated DBOS path against the existing A2 recovery path for quarantined/unknown outcomes and delivery recovery, including DBOS history privacy and operational burden.
