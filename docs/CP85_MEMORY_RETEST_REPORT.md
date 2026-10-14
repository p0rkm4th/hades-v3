# CP85 — Held-out memory correction under resource-capped CPU inference

**Date:** 2026-10-14
**Candidate source baseline:** `b2175ceedf8429a0e4c7fcba9cc7c9963d072841`
**Classification:** resource-limited matched screening; not a model-quality or harness score
**Result:** both A and C timed out before tool selection; no memory changed

## Question and setup

This bounded retest introduced one held-out structured preference: change lab-report headings to short, body format to bullets, and preserve the citations setting. A and C received identical task wording, task/effect contracts, tools, fixtures, model, context, temperature, output limit, and provider timeout. This does not rescore CP81's prior scalar, planning-note, or reminder-list results.

The new project was `hades-v3-exp-cp85-mem-20261014`. Preflight verified that the project did not exist, Compose generated unique project-scoped networks and volumes, all networks were `internal`, and no service exposed a host port, fixed container name, or privileged mode. The candidate API had only the project operator network: it resolved the model and gateway aliases but not PostgreSQL, Grocy, the simulator, or either workspace. It was read-only, non-root, and dropped all capabilities. The Qwen model file was mounted read-only. Shared CP75/CP80 containers and their endpoints were not contacted or restarted.

The profile was Qwen3-8B Q4_K_M, SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`; llama.cpp image digest `fc9b506e89c1a1cfdd7bc056480f54dc657c1c04d76839a08642dc280b8ed2f6`; effective `n_ctx=40960` from the server's `/props`; temperature 0; maximum output 1,024; provider timeout 50 seconds. The model server was limited to four CPUs and 12 GB RAM to bound interference. Candidate A used Pydantic AI 2.55.0; C used the lean loop in the same candidate API revision. Candidate image digest was `sha256:1052d8d2bd8f762460566a798f6026e2125771dddc516b605b2b5ebaf841bcc7`; gateway image digest was `sha256:4b280984265f0ae7edf15b37ad5d7c656ffe4f7b9c7c0c4a3b37515e055c44ab`. Each task retained the existing 16-generation/18-tool ceiling. Hermes was not eligible at this context.

The initial runner image was the existing cached CP75 test-runner image (`sha256:0485000e94746e8b05001fd05600cf5580817ac0915072375aa6d7cf418e43e5`) with the current CP81 case runner mounted read-only. It was used only as an ephemeral test driver on CP85's internal networks; no CP75 container or volume was accessed. Base Compose file SHA-256: `04bfac410f58bb271d10876de424a23c99659e184c048cb35cafeb83e1f7f7d5`.

## Results

| Candidate | Trial | Provider outcome | Tool calls | Effects | Canonical state | Durable task |
|---|---:|---|---:|---:|---|---|
| A / Pydantic AI | 1 | HTTP 502, `ModelAPIError: Request timed out`; server log showed three canceled requests | 0 | 0 | Original JSON and revision 1 unchanged | `FAILED` |
| C / lean | 1 | HTTP 502, `TimeoutError`; server log showed one canceled request | 0 | 0 | Original JSON and revision 1 unchanged | `FAILED` |

Independent PostgreSQL reads confirmed both tasks were `FAILED` and had zero effects. The candidate had not selected `memory_search` or `memory_correct`, so neither correction nor recall was scored. The candidate API reported no completed generation count; canceled upstream requests are recorded separately and must not be treated as successful generations. These failures diagnose the four-CPU resource-capped endpoint condition, not the CAS contract or the candidates' memory-selection capability.

The same agent task wording and settings were used for A and C. The provider timeout occurred before tool selection for both; A's provider path retried three times while C made one timed-out request. This is an observed runtime difference under this constrained condition, but a single repetition cannot establish a candidate reliability difference. CP81's earlier outcomes remain unchanged.

## Stop and cleanup

Before any CPU-cap increase, host load reached 19.64 on 20 cores and available memory fell from 17 GB to about 9.5 GB while the model was resident. No further generation was sent. The CP85 model server was stopped, then only project `hades-v3-exp-cp85-mem-20261014` was removed with its own containers, networks, and volumes. Post-cleanup inventory found zero resources carrying that project label; all 14 CP75/CP80 containers remained running. Available memory recovered to 19 GB and disk remained at 44 GB free.

Five uniquely tagged CP85 images remain for the cleanup lead to review; they were not pruned. Their IDs are candidate API `1052d8d2bd8f762460566a798f6026e2125771dddc516b605b2b5ebaf841bcc7`, gateway `4b280984265f0ae7edf15b37ad5d7c656ffe4f7b9c7c0c4a3b37515e055c44ab`, simulator `ba8bd2b012477c6c3907bf6c47a327c05f67ef36ecc12b5e59b3a6c0a7444cae`, Amber workspace `67727910e98a982891806710deab90bb9be16f0305e95c6d7bc0292cc023f01a`, and Cobalt workspace `fb3bc129b6266da377a2c7180e784fe7d3f105580b9409c4ae840ea4c5e77f31`. Listed virtual sizes are approximately 284 MB, 220 MB, 220 MB, 314 MB, and 314 MB (layers may be shared). The local model image and model file were reused. No persistent test data remains.

## Interpretation and next step

CP85 does not complete the requested held-out correction/recall qualification. The resource cap was chosen to protect concurrent work; removing it after observing a timeout would risk saturating the host and alter the test condition. Do not repeat this task under a larger cap during this run. Continue with deterministic CAS, stale-revision, cross-domain, exact-retry, changed-retry, and lifecycle tests; revisit model-equivalent memory trials only when an isolated endpoint has adequate reserved CPU/memory capacity.

ADR-010 remains **NOT READY**. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; no GPU, privileged host, HADES v2, production, or frozen-document activity occurred.

## Publication and CI

CP85 was published at `998cdc9fc61fd833b4a551d6f8ee8b638a233650`, and remote `main` matched. Exact-SHA CI run [38594357498](https://github.com/p0rkm4th/hades-v3/actions/runs/38594357498) failed at the pre-existing fixture startup step before tests ran: Docker Hub returned `toomanyrequests` while pulling Postgres/Grocy. The new CP85 Compose configuration step was not reached. An attempt to rerun only the failed GitHub Actions job was rejected with HTTP 403 because the connected GitHub integration lacks Actions write access. This is an external CI dependency; it is preserved as failure evidence and is not evidence of a CP85 test failure.

A subsequent sanitized documentation checkpoint, `5a54d083f715829ccceeb3b4cf03acea24afdc91`, passed the complete Prototype CI run [38595098048](https://github.com/p0rkm4th/hades-v3/actions/runs/38595098048), including all gateway, lifecycle, recovery, DBOS/Harness, adapter, and strict CP69 offline tests. This later green run does not change CP85's resource-limited candidate outcome or the original startup failure.

The next sanitized campaign/control-handoff checkpoint `d47433a1550d007b29e84879df2dc1a2f5534cac` also passed its exact-SHA full CI run [38596642984](https://github.com/p0rkm4th/hades-v3/actions/runs/38596642984). The CP85 candidate result remains an unscored pre-tool timeout; no repeat inference was sent.

The current public `db5adc4f4277310c7c009f63f79d917db8864344` checkpoint passed full CI as well ([38598208988](https://github.com/p0rkm4th/hades-v3/actions/runs/38598208988)); no CP85 retry or other model request occurred.
