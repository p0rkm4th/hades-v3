# Comparative findings

## Checkpoint 0 — repository setup

**Status:** no candidate comparison performed.

No adapters, common disposable environment, scenario trials, latency measurements, independent outcome checks, or owner-facing evaluations have been completed. There is no evidence to rank the three harness candidates or to claim an ADR-010 winner. The v2 source snapshot available at this checkpoint is recorded in [`V2_CONTROL_BASELINE.md`](V2_CONTROL_BASELINE.md); it is source evidence only and not a controlled product comparison.

Update this report at meaningful checkpoints with exact v2 and v3 revisions, trial conditions, provenance labels, verified outcomes, regressions, limitations, owner feedback, and whether continuing v3 work remains justified.

## Checkpoint 1 — shared fixture foundation

**Status:** fixture smoke checks passed; candidate comparison not run.

The disposable PostgreSQL and Grocy services start on internal Compose networks with digest-pinned images. Fixture smoke checks passed on a clean seed. A separate gateway integration test passed once and independently verified scoped user reads/writes, memory isolation, task checkpoint retrieval, and a compound list change against Grocy after-state. The effect ledger recorded the grocery effect as confirmed only after read-back. This tests the shared synthetic tool/data path, not any harness candidate, model, process-kill recovery, or owner-facing outcome. Details and reset procedure: [`experiment/README.md`](../experiment/README.md).
