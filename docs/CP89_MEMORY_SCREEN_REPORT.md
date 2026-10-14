# CP89 — matched CPU memory screen and replay-boundary update

**Date:** 2026-10-14
**Classification:** bounded live CPU experiment plus offline contract tests
**Result:** memory CAS remained correct; A and C timed out before tool selection on repeated attempts of CP81's structured correction case

## Scope and setup

The owner authorized a fresh, independently owned CP81 fixture project even though the existing CP75/CP80 projects remain unreleased. Project `hades-v3-cp81-memory-20261014-a` used only synthetic Amber memory records. Its Compose configuration had a unique project name, internal networks, no published ports, no fixed container names, and no privileged services. Only its Postgres, gateway, candidate API, and model server were started. The candidate API could reach only the project operator network; model weights were mounted read-only.

No images were built or downloaded. Cached candidate image `sha256:1052d8d2bd8f762460566a798f6026e2125771dddc516b605b2b5ebaf841bcc7`, gateway image `sha256:4b280984265f0ae7edf15b37ad5d7c656ffe4f7b9c7c0c4a3b37515e055c44ab`, runner image `sha256:0485000e94746e8b05001fd05600cf5580817ac0915072375aa6d7cf418e43e5`, and llama.cpp image `sha256:fc9b506e89c1a1cfdd7bc056480f54dc657c1c04d76839a08642dc280b8ed2f6` were reused. The candidate API source was bind-mounted read-only from source revision `33ab8587f43272f8bc482c6ccfa92ab1457ba0f9`. Model Qwen3-8B Q4_K_M had SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`; `/props` reported `n_ctx=40960`. A used Pydantic AI 2.55.0 and OpenAI 3.29.0 with `max_retries=0`; C used the shared direct OpenAI-compatible client. Both had temperature 0, 1,024 output-token limit, and a 50-second provider timeout.

## Candidate observations

Five synthetic tasks were attempted. The structured correction reused CP81's existing `weekly_structured` wording and fixture contract; it is a repeat observation, not a held-out prompt. A and C received identical wording and contracts in each profile.

| Candidate | Model-server CPU cap | Task | Outcome | Independent verification |
|---|---:|---|---|---|
| A | 4 | Structured correction, repetition 1 | HTTP 502 `ModelAPIError`; one request; no response | Task `FAILED`; no tool/effect; memory still revision 1 |
| C | 4 | Same structured correction, repetition 1 | HTTP 502 `TimeoutError`; one request; no response | Task `FAILED`; no tool/effect; memory still revision 1 |
| A | 8 | Structured correction, repetition 2 | HTTP 502 `ModelAPIError`; one request; no response | Task `FAILED`; no tool/effect; memory still revision 1 |
| C | 8 | Same structured correction, repetition 2 | HTTP 502 `TimeoutError`; one request; no response | Task `FAILED`; no tool/effect; memory still revision 1 |
| A | 4 | Scalar correction, one screen | HTTP 502 `ModelAPIError`; one request; no response | Task `FAILED`; no tool/effect; memory still revision 1 |

Task and memory references are hashed in [the JSONL record](../experiment/results/cp89-memory-screen-20261014.jsonl); raw answer text and prompts are not recorded. Every candidate request made one upstream attempt and produced zero successful generations. There was no mutation to restart or recall. CP81's prior scalar, structured, and list results and CP85's negative result remain unchanged.

The first matched pair used four CPUs. After both requests timed out, the same disposable model container was recreated with an eight-CPU cap while no model request was active; A and C then repeated the same structured wording. Both again timed out. This is a separate matched profile, not a retroactive adjustment to CP85. Host load peaked around 12 on a 20-core system; free disk remained 39 GB. The experiment stopped after the second matched structured pair rather than raising the timeout or CPU cap further. These results are evidence of a current provider/model latency limitation for this task profile, not a memory-CAS defect or harness ranking.

## Contract checks

- The gateway's keyed-CAS integration test passed. It confirmed same-task exact retry returns the existing effect identity, changed retry rejects, stale revision rejects, cross-user and cross-domain requests reject, and canonical state/effect commit is atomic.
- The candidate finalization suite passed 24/24 offline tests. It includes a confirmed bounded memory correction completing without a model checkpoint, rejection of a model success claim with no durable mutation, fail-closed arbitrary memory writes, and provider failure after an effect.
- CP88's exact-SHA CI passed at `33ab8587f43272f8bc482c6ccfa92ab1457ba0f9`, run [38607008722](https://github.com/p0rkm4th/hades-v3/actions/runs/38607008722), including the database-backed stateless-resume guard test and workflow cleanup.

These contract tests establish gateway and finalizer rules; they do not convert CP89's failed model attempts into memory successes. The CP81 candidate workstream remains mixed and unqualified. Hermes was not run because 40,960 context is below its documented 64,000-token minimum.

## Workspace replay limitation

CP88's sequential stateless-resume guard is covered by a database-backed regression. A further source review identified an untested concurrency boundary: `/api/turn` does not reserve a durable per-task turn lease. Two simultaneous turns may both pass the resume guard before an effect appears. The gateway serializes each effect-creation transaction and blocks a second command while the first is unresolved, but it cannot infer that a new operation identity after the first becomes `CONFIRMED` is a replay rather than a legitimate next command. This remains an unqualified duplicate-risk case. No second ledger or process-local lock was introduced; a process-local lock would not solve multi-process/restart behavior. Durable invocation history or task-turn serialization integrated with the existing task authority is still required for automatic continuation.

## Resources and cleanup

At start, `/home` had 39 GB free. Existing images and model file were reused, with no downloads or image builds. At close, Tern stopped all four containers in the new project to release CPU and memory. The project still owns four internal networks and nine uniquely prefixed volumes, including its small synthetic Postgres data volume. Per the cleanup lead's ownership, Tern has not deleted these resources and requested review/release through the protected handoff. CP75 and CP80 were untouched and remain in use. No Hypnos, GPU, firewall, HADES v2, or production activity occurred.

## Decision impact

CP89 does not distinguish A from C: both made one request and timed out before the same tool on the repeated structured case at both tested CPU caps. The scalar timeout for A is one additional observation, not a repeated score. Earlier CP81 successes still show A/C scalar correction and fresh-context recall, while structured selection and list recall remain failures. CP89 did not complete the requested held-out structured/scalar/list qualification. ADR-010 remains **NOT READY**. Any next memory model experiment needs an independently reserved model/runtime and an adequately justified request-latency profile; changing the timeout or tuning prompts after these observations would be a new comparison condition. No further CPU or GPU inference is authorized by this CP89 report.
