# CP81 — bounded memory correction completion

**Status:** gateway/lifecycle correction implemented; repeated A/C memory qualification remains pending.
**Baseline:** public CP80 `1228dae4e0f85ced036345e0fd8e12372df7562f`.
**Classification:** contract implementation and unit regressions. No new live-model or GPU result is claimed.

## Failure reproduced

CP75 recorded successful scalar/list CAS mutations with one confirmed task-linked `MEMORY_MUTATION` effect and the intended canonical value, while both A and C left the task `WAITING` because the model omitted `task_checkpoint(COMPLETED)`. CP75's structured correction cases made no tool call and falsely claimed success; the task was `FAILED` and the canonical value did not change. These original outcomes remain unchanged in [the CP75 report](CP75_MEMORY_CAS_REPORT.md) and [trial records](../experiment/results/cp75_memory_cas.jsonl).

The missing-checkpoint case had enough durable evidence only for a task whose required correction had been independently fixed before the candidate turn. Completing an arbitrary task from a confirmed memory write would be unsafe: the agent might select the wrong record or value, or the request might include additional work. CP81 therefore adds an exact one-correction criterion that only the authenticated orchestrator may store when creating the task.

## Contract

The version 1 `memory_correction` completion contract identifies exactly one `memory_key`, positive `expected_revision`, and desired JSON `value`. It is immutable after task creation and supports only `memory_correct`; it cannot authorize `memory_write` or multiple corrections. The gateway finalizer independently verifies, locking the canonical row through the task-state commit:

- The effect belongs to the original task, authenticated user, and memory domain.
- There is exactly one persisted effect and it is a confirmed `MEMORY_MUTATION` for the exact resource key.
- The request is the exact keyed CAS correction with the contract's revision and value.
- The persisted result and current canonical row contain the requested value at `expected_revision + 1`.
- A nonempty final response was produced without provider failure, and no task steps remain pending.

Missing, partial, extra, mismatched, or unconfirmed effects remain incomplete. A model claim without the CAS effect stays `WAITING`. Provider failure after a confirmed mutation preserves the mutation and leaves response delivery `WAITING`. Ordinary memory writes and tasks without this trusted criterion retain their existing fail-closed completion path. The framework's orchestration decision is not accepted by itself; gateway verification remains authoritative. This contract does not solve interpretation of arbitrary natural-language corrections: its authenticated caller must bind the exact key, current revision, and intended replacement from trusted user intent before the candidate acts. CP81 uses predetermined synthetic scenarios; general caller-side intent binding remains unqualified.

## Regression evidence

- `test_task_lifecycle.py`: 16 passing tests, including exact contract normalization, task identity, exact persisted value/revision, missing/extra effects, wrong identity, and stale revision rejection.
- `test_candidate_finalization.py`: 20 passing tests, including completion with no model checkpoint, read-only fallback rejection for a correction contract, no-op claim rejection, and provider failure after a confirmed effect remaining `WAITING`.
- `test_gateway.py` now includes a database-backed integration case: an orchestrator-created contract rejects a false success claim before mutation, then completes only after the exact CAS mutation and canonical row verification, with exact retry returning the same effect and changed retry rejected. The first exact-SHA CI run (`5505974`, run `38517855031`) failed because the existing external-commitment branch matched every stored contract; the type-specific routing fix passed at `cdd05fa` (run `38518135796`) and with canonical row locking at `f2a54d3` (run `38518447109`). The expanded exact-retry test then failed at `0dd40bb`/`e8b4c25` (runs `38518781301`/`38518948134`). Public annotations exposed only a generic step failure, and GitHub requires repository-admin rights to download logs. Code inspection found the test read effects from the checkpoint response, which intentionally omits them; it now performs a separate task read. The corrected gateway integration and exact-retry checks passed at `879219d` (run `38519360238`). Local integration execution against shared CP75/CP80 fixtures remains deferred pending cleanup-lead coordination.
- Python compilation and `git diff --check` passed. No persistent test project was created; no shared resource, HADES v2 service, Hypnos route, or firewall was touched.

## Qualification still required

The new rule proves a narrow trusted completion path, not that models reliably identify and correct memories. CP75 still shows A/C selection failures and no repeat coverage. `run_cp81_memory_case.py` now defines three CP75-independent held-out cases: scalar coffee preference, structured weekly-note format, and list-valued weekday reminder. It provides one bounded correction or fresh-task recall turn and records task/effect/canonical-memory oracles. For each case, run at least three matched A/C repetitions: correct the value, independently preserve task ID and output, restart only the approved disposable candidate/gateway project, then run fresh-task recall with the original correction-task ID. Exact and changed retries remain covered by gateway integration tests. A true fresh-context retrieval must follow the candidate's own mutation; independently seeding the final value does not count. Current CP75 and CP80 fixture stacks remain untouched while the cleanup lead's coordination is pending.

The runner is intended for the disposable `test-runner` image, which has the fixture database credentials and `psycopg`; candidate containers receive neither. It now emits separate tool-selection, canonical mutation, durable task, and answer-correctness results. The answer oracle only checks expected phrases and explicit negations for these synthetic cases; it is not a general semantic evaluator, so retain the answer for independent review. Three focused answer-oracle unit tests pass. The runner has only been syntax-checked in this workspace, not run against a candidate, because the existing CP75/CP80 resource ownership and release remain unconfirmed. Do not use Compose commands that start, rebuild, restart, or remove those projects. Once Tallowmere identifies an approved disposable project, each correction/recall pair must include a verified restart of only that project's candidate API and gateway between phases; record the exact project and services in the trial evidence. No service restart or model-mediated result is claimed by CP81 so far.

DBOS remains a reuse candidate, not an adopted task/effect authority. CP71 remains blocked on host firewall privilege. No Hypnos generations are authorized. ADR-010 remains NOT READY.
