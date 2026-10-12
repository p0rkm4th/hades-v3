# ADR-010 — harness recommendation

**Status:** NOT READY — initial integration probes expose a Hermes/model context incompatibility; comparative evidence is insufficient.

No harness is recommended at this checkpoint. A and C each completed nine family 1 calls: three repeated attempts for each of three kitchen-inventory wordings. All 18 responses matched fixture state, queried only `inventory_read`, and had completed task records with no memory or effect mutation. These repeated synthetic results are useful progress but cover one scenario family on one 8B model profile; CPU timings are not a meaningful ranking. A newly detected task-lifecycle defect was fixed and the pre-fix attempts were excluded. Candidate B (reduced Hermes) starts and exposes its authenticated gateway API but rejects the selected Qwen3-8B profile before tool execution: verified model context is 40,960 tokens, below Hermes's enforced 64,000-token minimum. Do not bypass that requirement or overstate model capacity. Whether another common local profile can meet the floor remains open.

A recommendation still requires the full eight-family screen, repeated controlled trials, independent outcome verification, safety-gate results, restart and maintenance exercises, eligible stronger-model comparison, living v2 observations, and owner-facing evaluation specified by the experiment plan and historical review. The exact family 1 evidence and its limitations are in [COMPARISON_REPORT.md](COMPARISON_REPORT.md).

Do not interpret NOT READY as evidence that a particular candidate failed or that v3 should replace HADES v2.
