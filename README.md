# HADES v3 harness comparison

This repository contains a bounded engineering experiment comparing three agent harness approaches against shared synthetic authority, state, tool, context, and verification contracts. It evaluates whether any candidate merits further qualification under ADR-010. It is not a production HADES implementation and does not assume that v3 should replace the independently maintained HADES v2 system.

The experiment compares a thin Pydantic AI harness, a reduced Hermes runtime, and a lean custom model/tool loop. HADES v2 is evaluated separately as a living external control. The prototype is intended to use disposable data and synthetic identities only; no production credentials, household data, live infrastructure mutations, or financial commitments belong here.

## Current status

The shared PostgreSQL/Grocy fixture, scoped tool gateway, approval-gated simulated commitment, separate disposable shell/Git workspaces, CPU-served Qwen3 models, and synthetic chat UI are available. Candidates A and C each completed three repeated attempts for each of three kitchen-inventory wordings (9 calls per candidate) against the same Qwen3-8B profile. The results matched seeded inventory and independently checked Grocy state; the trial evidence and limitations are in [`docs/COMPARISON_REPORT.md`](docs/COMPARISON_REPORT.md). Reduced Hermes reaches its API but cannot run against the selected Qwen context profile because Hermes requires at least 64,000 tokens and Qwen3-8B supports 40,960. No harness is recommended yet. The exact v2 source revisions and evidence limits are in [`docs/V2_CONTROL_BASELINE.md`](docs/V2_CONTROL_BASELINE.md). Current evidence and blockers are in [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md).

## Scope and safety

See [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md). The frozen local product and architecture specifications govern this experiment; they are intentionally not reproduced in this repository pending a separate content-level public-safety review. The repository publishes bounded summaries and synthetic experiment artifacts only.

## Reproducibility

The fixture and optional model profiles are described in [`experiment/README.md`](experiment/README.md). Exact local model/runtime identities are pinned in [`docs/MODEL_PROFILE.md`](docs/MODEL_PROFILE.md). Any reported result must include the candidate revision, model/runtime identity, fixture reset, trial provenance, and independent outcome verification. Unrun tests and uncollected measurements must remain labeled as such.
