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
