# Comparative findings

## Checkpoint 0 — repository setup

**Status:** no candidate comparison performed.

No adapters, common disposable environment, scenario trials, latency measurements, independent outcome checks, or owner-facing evaluations have been completed. There is no evidence to rank the three harness candidates or to claim an ADR-010 winner. The v2 source snapshot available at this checkpoint is recorded in [`V2_CONTROL_BASELINE.md`](V2_CONTROL_BASELINE.md); it is source evidence only and not a controlled product comparison.

Update this report at meaningful checkpoints with exact v2 and v3 revisions, trial conditions, provenance labels, verified outcomes, regressions, limitations, owner feedback, and whether continuing v3 work remains justified.

## Checkpoint 1 — shared fixture foundation

**Status:** fixture smoke checks passed; candidate comparison not run.

The disposable PostgreSQL and Grocy services start on internal Compose networks with digest-pinned images. Fixture smoke checks passed on a clean seed. A separate gateway integration test passed once and independently verified scoped user reads/writes, memory isolation, task checkpoint retrieval, and a compound list change against Grocy after-state. The effect ledger recorded the grocery effect as confirmed only after read-back. This tests the shared synthetic tool/data path, not any harness candidate, model, process-kill recovery, or owner-facing outcome. Details and reset procedure: [`experiment/README.md`](../experiment/README.md).

## Checkpoint 2 — local inference profiles

**Status:** both local model endpoints returned visible output; candidate comparison not run.

The standard Qwen3-8B Q4_K_M profile and stronger Qwen3-14B Q4_K_M profile were downloaded from pinned official model revisions, checksum-verified, and served sequentially by the same digest-pinned `llama.cpp` CPU image. An operator-network test container reached each OpenAI-compatible endpoint and received a non-empty response. The 8B smoke call generated 4 completion tokens in 0.7 seconds; the 14B smoke call generated 6 tokens in 1.6 seconds. These single short calls are availability checks, not performance estimates. One initial 8B probe with a 32-token limit produced no visible text because the budget was consumed in hidden reasoning; the common model setting now disables Qwen's thinking channel. Docker cannot discover the host GPU, so all current measurements use CPU inference. No harness has called the models yet.

V2 source was rechecked at the same public upstream SHA `fe222446c83a4034bfa37ac5a493d6a30b9abe74`. A local checkout was observed at `6a46e18657b17c261a5725de3b0d09b24e7d3f60`, but its branch is divergent and locally modified, so it is not eligible for a matched current comparison. No runtime or owner evaluation was performed. See [`MODEL_PROFILE.md`](MODEL_PROFILE.md) and [`V2_CONTROL_BASELINE.md`](V2_CONTROL_BASELINE.md).

## Checkpoint 3 — protected simulated commitment

**Status:** four shared-fixture commitment test executions passed; no candidate comparison run.

An operator-only approval record binds the authenticated synthetic user, task, target, canonical effect digest, and short expiry. The gateway consumes that approval before recording durable intent and dispatching to a simulator that is not addressable from the candidate operator network. On the seeded `target-ack-loss`, the receiving fixture committed the effect and returned a simulated HTTP 504. The gateway recorded `QUARANTINED`; it did not report success or replay the operation. A subsequent reconciliation read back the simulator's accepted effect and transitioned the ledger to `CONFIRMED`.

The ack-loss test also proved that a missing approval and a changed detail string are denied, a harmless inventory read still succeeds, an alternate user cannot reconcile the effect, and the consumed approval cannot be reused. The independent fixture-admin database read showed `receive_count=1` and `effect_state=CONFIRMED`. Separate approved calls to `target-accept` and `target-reject` produced `CONFIRMED` and `REJECTED` respectively; their independent fixture reads showed one receive and the expected accepted-effect state. The ack-loss path was repeated successfully against a second target after adding code support for reconciling an effect left in `DISPATCHED`; the test did not simulate a process crash or exercise that state. An operator-network probe could not resolve the commitment simulator service. Four targeted test executions cover only the shared synthetic boundary; they do not prove production safety, approval identity quality, revocation handling, duplicate-safe retry, candidate behavior, process-kill recovery, or owner acceptance. V2 upstream remained at `fe222446c83a4034bfa37ac5a493d6a30b9abe74` with no runtime comparison. Implementation builds on v3 revision `4e2ff563f61c4fc03594c70a8c749c4e92ec846f`.

## Checkpoint 4 — disposable shell/Git workspaces

**Status:** a synthetic code repair, test run, Git commit, and cross-user isolation check passed; no candidate comparison run.

Two runner containers use different named volumes and different internal networks. The gateway derives which runner to call from the authenticated fixture identity. The runner has no added capabilities, a read-only root filesystem, no external route, and bounded process/time/output/file controls. A test-runner request reproduced this work: Amber's seeded three-test suite failed, the shell changed the discount implementation, all three tests passed, and Git recorded `Fix discount calculation`. Independent host-side `docker compose exec` then reran the tests and confirmed a clean `main` tree at that commit. Cobalt's independent repository still had the original two failing assertions and a clean `main` tree. Runner-side and operator-network probes could not resolve the other user's runner; Docker inspection confirmed distinct volume mounts and the configured resource controls.

This verifies one deterministic shared shell/Git fixture, not model-driven performance, egress resistance against hostile code, aggregate disk quotas, process interruption recovery, or production security. The workspace volumes currently persist code changes until reset. V2 upstream remained at `fe222446c83a4034bfa37ac5a493d6a30b9abe74`; no runtime comparison or owner evaluation was performed. Implementation builds on v3 revision `121795106804ced49414f88be366edbcd5e76bd1`.
