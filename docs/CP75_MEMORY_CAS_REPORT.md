# CP75 — Stable-key memory correction

**Status:** CAS contract tests pass; candidate end-to-end memory correction is not qualified.
**Baseline:** CP74, `6886e019069fc197df05ba8ed6781d66e45b51a3`.
**Model profile:** local Qwen3-8B Q4_K_M, llama.cpp image `fc9b506e89c1a1cfdd7bc056480f54dc657c1c04d76839a08642dc280b8ed2f6`, 40,960 context, 16 threads, temperature 0, 1,024 output tokens. Candidate API image: `sha256:9e1f4bc10dbb17b22c9a07fb36257a6eab5e47220d85da117fc582ae6f00ab24`. No Hypnos/GPU inference was used. Hermes was not scored because this profile is below its 64,000-token minimum.

## Contract change

CP74's failure was a type-shape mismatch: the model found the intended memory, then supplied the old JSON value in a shape that did not equal the canonical JSON value. The former natural-language query plus model-reproduced expected value was a brittle mutation authority.

Memory search/read now return a stable `memory_key` and integer `revision`. Corrections submit that identity, revision, and replacement value to `/v1/memory/correct-by-key`. The gateway scopes the key to the authenticated user/domain and active task, checks the revision, updates the canonical row and inserts the task-linked effect atomically. An exact retry returns its original effect; a changed retry is rejected. Stale revisions fail without mutation. The legacy fuzzy mutation endpoint returns 410 and directs callers to read/search followed by keyed CAS. Existing databases receive an idempotent revision migration; fresh fixtures create the column directly. `memory_write` now also requires an active task, and the tests/runner seed fixtures through the isolated test database writer instead of a taskless gateway mutation.

The gateway, rather than the candidate, validates the persisted effect against task/user/domain, operation, key, value, revision and canonical row at finalization. Memory changes still require durable task-linked evidence. No model answer or HTTP status alone completes a task.

## Verification

Focused gateway tests cover the migration on a legacy table, fresh schema, exact key/revision, stale revision, cross-user scope, exact and changed retry, missing task identity, gateway finalization validation, and transaction rollback when effect confirmation is rejected. Full related suites passed:

- `test_gateway.py`: 6 tests
- `test_task_lifecycle.py`: 14 tests
- `test_candidate_finalization.py`: 16 tests

The disposable CP75 project was used with `--no-deps` test-runner invocations. Only its gateway and candidate API were restarted. No external/Hypnos generation or privileged network operation occurred.

## Candidate trials

Each candidate received three held-out, independently seeded correction requests: a scalar preference, a structured JSON preference, and a list preference. These were single observations per scenario, not statistical qualification.

| Candidate | Scalar | Structured JSON | List | Fresh-context retrieval |
|---|---|---|---|---|
| Pydantic AI (A) | CAS mutation correct; one confirmed effect; answer correct; task `WAITING` because model omitted checkpoint | No tool call; model claimed success; task `FAILED`; canonical value unchanged | CAS mutation correct; one confirmed effect; answer correct; task `WAITING` | Scalar retrieved accurately after gateway/API restart; read-only task `COMPLETED` |
| Lean loop (C) | CAS mutation correct; one confirmed effect; answer correct; task `WAITING` because model omitted checkpoint | No tool call; model claimed success; task `FAILED`; canonical value unchanged | CAS mutation correct; one confirmed effect; answer correct; task `WAITING` | Scalar retrieved accurately after restart; list retrieval after restart made no tool call and failed |

On same-task resume, A read the confirmed original effect and correctly avoided another mutation, but again narrated that it would persist a completion checkpoint without calling the tool; task remained `WAITING`. C's list correction used one additional `memory_read` and one additional generation. A and C otherwise showed the same outcome pattern on the three correction prompts. Full sanitized per-trial task IDs, effect IDs, generation counts, durations and oracle results are in [CP75 JSONL](../experiment/results/cp75_memory_cas.jsonl).

These results separate two issues. The CAS contract fixes unsafe/brittle value matching and produces correct, durable writes when the candidate calls it. End-to-end task completion and consistent memory-tool selection remain candidate/model failures. Canonical state and effect records corroborated every scored outcome; task terminal state was not accepted as the sole oracle. The structured case specifically falsifies any claim that the CAS interface alone makes agents reliably correct memories: both candidates generated unsupported success claims without dispatching a tool, and the gateway rejected completion.

## Remaining work

- Repeat held-out correction/retrieval trials before claiming a reliable memory workflow.
- Improve and test a general completion interaction only if it preserves the independent lifecycle contract; do not auto-complete arbitrary natural-language tasks from a confirmed memory mutation.
- Evaluate a keyed/versioned CAS correction through Hermes's actual runtime using a context-compliant deterministic peer. Do not represent that as model-equivalent evidence.
- Continue the reuse-first technology assessment after this checkpoint. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; no firewall or GPU checks were repeated.

ADR-010 remains **NOT READY**. No production implementation is authorized.
