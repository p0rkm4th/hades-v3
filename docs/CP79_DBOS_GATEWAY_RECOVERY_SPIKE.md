# CP79 — DBOS recovery through the HADES gateway

**Evidence class:** CONTRACT TEST
**Status:** published; exact-SHA CI passed
**Scope:** disposable HADES v3 fixtures, no model or live infrastructure

## Question

Can a mature durable execution runtime resume an interrupted operation while HADES remains the only authority for user identity, approval, effect records, reconciliation, and task completion?

## Method

Pinned DBOS Transact 3.2.0 in a separate runner. Its workflow metadata used a project-scoped SQLite volume. The runner could reach only the operator network and authenticated as a fixture user; it had no database credentials, orchestrator secret, host access, or model connection. A separate fixture setup and verifier had operator credentials.

Three independent synthetic tasks each had an exact task-scoped approval and a commitment target configured to accept once while losing the acknowledgment. The worker was terminated after the gateway returned and before DBOS recorded the step result. A restarted worker reopened the same DBOS state and resumed each workflow. The HADES gateway returned the original effect identity; HADES reconciliation then checked canonical target state. An independent verifier inspected task, approval, effect, and target records before asking the trusted gateway finalizer to persist completion and the response.

## Results

- **3/3** workflows resumed after process death.
- Each resumed submission made exactly two DBOS step attempts but preserved the original task and effect IDs.
- Every task had one confirmed effect, one canonical target receive, the correct consumed approval, and the expected target state.
- The independent verifier observed no additional effects and finalized all three tasks as `COMPLETED`; the response was persisted as pending delivery.
- No model, candidate harness, GPU, Hypnos endpoint, firewall helper, HADES v2 service, or persistent DBOS service was used.
- Project-scoped containers, networks, and volumes were removed after the run.

This supports the narrow claim that DBOS can resume an execution step around the existing idempotent HADES gateway. It does **not** establish exactly-once delivery by DBOS, model behavior, production durability, or a benefit over candidate-native recovery. The independent HADES finalizer—not DBOS—proved and recorded task completion. DBOS state was temporary workflow metadata, not a second task/effect authority.

## Preserved setup failure

Initial runs using Python 3.13 and 3.14 Bookworm images failed before any commitment request. Their bundled SQLite 3.40.1 returned `NULL` for DBOS's SQLite schema default `unixepoch('subsec')`, violating a non-null timestamp column. This was a runner-image/SQLite compatibility failure; no effect was dispatched. A diagnostic container confirmed the behavior. The successful runner uses the pinned Python 3.11 Bookworm image, whose SQLite timestamp behavior is compatible. This experiment pins DBOS and the runner base; it does not modify HADES services.

DBOS documents SQLite as suitable for local development/testing and recommends PostgreSQL for production deployment; this spike deliberately used disposable SQLite metadata. See the [DBOS quickstart](https://docs.dbos.dev/quickstart), [database connection guide](https://docs.dbos.dev/python/tutorials/database-connection), and [configuration reference](https://docs.dbos.dev/python/reference/configuration).

## Cleanup and reproducibility

The CI job runs setup, crash/restart, independent verification, then project-scoped teardown with volumes. Local verification found no CP79- or A2-named containers, networks, or volumes after teardown. Reproducible sources are in `experiment/spikes/cp79_dbos_gateway/` and `experiment/compose.cp79-dbos.yaml`.

Tagged CP79 and A2 runner/fixture images remain in the local Docker image store as reproducible build artifacts. No container depends on them. They are not required by the active HADES v3 services; preserving them avoids unnecessary rebuilds while CP79/A2 evidence is under review. The storage-cleanup lead may remove the specifically tagged images after confirming no concurrent experiment needs them. Do not prune shared Docker build cache as part of this experiment; it is global and can be in use by other work.

Exact-SHA CI run [38512629038](https://github.com/p0rkm4th/hades-v3/actions/runs/38512629038) passed for `cde1ff32a67eb902aefaec42a1cd60730366629b`, including gateway/lifecycle regressions, A2 contract, CP79 setup/restart/verification/teardown, and strict CP69 offline qualification.

## Decision

Keep DBOS as a bounded integration candidate, not as a second authority. Before considering adoption, compare its restart behavior and operational burden against the current harness recovery paths, and demonstrate a decision-relevant reduction in HADES-specific code. No scored A/B/C result changes. ADR-010 remains **NOT READY**.
