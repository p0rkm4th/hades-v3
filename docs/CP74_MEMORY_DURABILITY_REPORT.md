# CP74 — task-linked memory durability and fresh-context retrieval

**Status:** Contract integration passes; live candidate correction failed safely; memory continuity is not qualified.
**Date:** 2026-10-13
**Base source:** CP73 `6e368455c5c2ab398b6723b2dff102a67c08d61a`

## Objective

Close the proven gap in which candidate memory mutations had no durable task-linked effect identity, then measure correction and fresh-context retrieval without treating model text as proof of persistence.

## Contract correction

Agent memory writes and corrections now include the active task ID. The gateway locks the authenticated RUNNING task and records the mutation in the existing effect ledger. The canonical memory update and `MEMORY_MUTATION` transition from `INTENDED` to `CONFIRMED` occur in one PostgreSQL transaction. Exact retry returns the same effect; changed retry for the task/key is rejected. The gateway finalizer checks the actual persisted effect ID, operation, resource key, task/user/domain identity, persisted request and result values, and the current canonical memory row. An orchestrator success flag alone cannot establish completion. Setup writes without task linkage remain available but cannot prove a task's success. Known no-effect rejection (HTTP 404 for a correction with no exact match) is a failure, not an uncertain effect.

No second task/effect ledger, scheduler, or memory authority was introduced. The frozen architecture and HADES v2 were not modified.

Final review also found that candidate tool-evidence collection copied the returned memory key for corrections but omitted it for `memory_write`. The evidence collector now includes that key, and a lifecycle regression proves successful task-linked `memory_write` can be validated only when its persisted effect and canonical row match. This is a contract-path fix; it does not change the scored candidate results.

## Candidate observations

The matched model was local Qwen3-8B Q4_K_M on the pinned llama.cpp runtime, 40,960-token context, 16 threads, temperature 0, 1,024 output cap, and 50-second model request timeout. Candidate API image ID was `sha256:0b7d160f44c6bd23b978a62d3958e81b9f27d0f9c6162d7b4cba9f2bd0e7e794`; gateway image ID was `sha256:228ef56ae059db15c4ccce0918e9fb0ed73c3928947d290860e4d82dde3d25f5`; model image digest was `sha256:fc9b506e89c1a1cfdd7bc056480f54dc657c1c04d76839a08642dc280b8ed2f6`.

| Candidate | Initial recall | Correction request | Fresh-context read of independently seeded corrected value |
|---|---|---|---|
| Pydantic AI (A) | Correct; one `memory_search`; task `COMPLETED`; 5,280 prompt / 59 completion tokens; 13.111 s | One `memory_correct`; HTTP 404; task `FAILED`; 5,384 / 84 tokens; 50.413 s; no effect and original value unchanged | Correct; one `memory_search`; task `COMPLETED`; 5,287 / 45 tokens; 15.895 s |
| Lean loop (C) | Correct; one `memory_search`; task `COMPLETED`; 5,277 / 52 tokens; 11.756 s | One `memory_correct`; HTTP 404; task `FAILED`; 5,365 / 70 tokens; 18.278 s; no effect and original value unchanged | Correct; one `memory_search`; task `COMPLETED`; 5,284 / 47 tokens; 10.074 s |

The candidates both failed to construct a correction request matching the stored memory. The sanitized evidence lacks the precise submitted query/expected-value fields, so the responsible mismatch cannot be isolated. Since both used the same model/profile and failed at the same tool boundary, the result does not meaningfully rank the harnesses. The fresh-context corrected value was explicitly seeded by independent fixture setup after correction failures; it was not a candidate mutation. The recorded C timeout with a dirty initial fixture is preserved as an excluded diagnostic, not scored.

Hermes was not run: the available CPU profile's 40,960 context is below its 64,000 minimum. This is not a Hermes failure. No Hypnos inference, GPU route, privileged firewall helper, or HADES v2 service was used.

Detailed sanitized turn records are in [`cp74_memory_continuity.jsonl`](../experiment/results/cp74_memory_continuity.jsonl).

## Independent regression evidence

- Gateway integration: 2 tests passed, including effect identity, exact retry, changed replay rejection, finalization against canonical memory, fresh task read, and cross-domain denial.
- Lifecycle contract: 14 tests passed after adding a successful linked `memory_write` proof and canonical-value mismatch check, alongside unlinked mutation fail-closed and identity checks.
- Candidate finalization: 16 tests passed, including known rejected correction becoming `FAILED` without an effect.
- Python compilation, compose configuration, and whitespace checks passed before publication.

These tests prove the persistence contract and failure handling, not that either model can reliably formulate corrections. Repetition remains one matched observation per stage; the next memory qualification must use at least three held-out matched repetitions and include restart before fresh-context recall.

## Isolation, cleanup, and next work

All services used the uniquely scoped `hades-v3-exp-cp74-memory` disposable Compose project with local synthetic fixture data. The project was removed after evidence capture; cleanup was limited to CP74 resources. HADES v2, HADES-infra drafts, Hypnos, and existing v3 fixture projects were not changed.

Next: preserve this negative candidate result, add bounded diagnostic evidence sufficient to identify correction matching without exposing private data, then run a held-out three-repetition A/C correction and restart/retrieval experiment. Hermes needs an eligible context-compliant runtime. ADR-010 remains **NOT READY**; no production implementation is authorized.
