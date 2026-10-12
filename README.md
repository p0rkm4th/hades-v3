# HADES v3 harness comparison

This repository contains a bounded engineering experiment comparing three agent harness approaches against shared synthetic authority, state, tool, context, and verification contracts. It evaluates whether any candidate merits further qualification under ADR-010. It is not a production HADES implementation and does not assume that v3 should replace the independently maintained HADES v2 system.

The experiment compares a thin Pydantic AI harness, a reduced Hermes runtime, and a lean custom model/tool loop. HADES v2 is evaluated separately as a living external control. The prototype is intended to use disposable data and synthetic identities only; no production credentials, household data, live infrastructure mutations, or financial commitments belong here.

## Current status

The shared PostgreSQL/Grocy fixture, scoped tool gateway, approval-gated simulated commitment, separate disposable shell/Git workspaces, CPU-served Qwen3 models, and synthetic chat UI are available. Family 2 CP52/55 failed 0/3 per candidate on Qwen3-8B with an omitted addition, including the counterbalanced repeat; CP53/54 on Qwen3-14B passed 7/12 attempts, with five zero-effect pre-tool timeouts. These are narrow profile-sensitive results, not candidate qualification. In family 6, A/C each failed 0/3 valid Qwen3-8B recoveries but passed 3/3 on Qwen3-14B; one 14B preparation timeout per candidate had no effects. A prior homelab probe found an existing Qwen3.6 35B GPU endpoint with effective serving context 65,536, observed generation-time GPU use, and 27.65–37.60 tokens/s. Current strict SSH checks cannot verify remote hosts, and the isolated candidate network has no route to that endpoint. Matched trials therefore continue on identical CPU profiles; no harness is recommended yet. Trial evidence and limitations are in [`docs/COMPARISON_REPORT.md`](docs/COMPARISON_REPORT.md). V2 source and evidence limits are in [`docs/V2_CONTROL_BASELINE.md`](docs/V2_CONTROL_BASELINE.md); current campaign state is in [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md).

## Scope and safety

See [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md). The frozen local product and architecture specifications govern this experiment; they are intentionally not reproduced in this repository pending a separate content-level public-safety review. The repository publishes bounded summaries and synthetic experiment artifacts only.

## Reproducibility

The fixture and optional model profiles are described in [`experiment/README.md`](experiment/README.md). Exact local model/runtime identities are pinned in [`docs/MODEL_PROFILE.md`](docs/MODEL_PROFILE.md). Any reported result must include the candidate revision, model/runtime identity, fixture reset, trial provenance, and independent outcome verification. Unrun tests and uncollected measurements must remain labeled as such.
