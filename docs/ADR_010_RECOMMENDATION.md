# ADR-010 — harness recommendation

**Status:** NOT READY — initial integration probes expose a Hermes/model context incompatibility; comparative evidence is insufficient.

No harness is recommended at this checkpoint. Candidate A (Pydantic AI) and C (lean loop) each completed one read-only kitchen smoke probe through the shared fixture, with matching seeded output. These are single integration checks, not controlled comparisons. Candidate B (reduced Hermes) starts and exposes its authenticated gateway API but rejects the selected Qwen3-8B profile before tool execution: verified model context is 40,960 tokens, below Hermes's enforced 64,000-token minimum. Do not bypass that requirement or overstate model capacity. Whether another common local profile can meet the floor remains open.

A recommendation still requires the full eight-family screen, repeated controlled trials, independent outcome verification, safety-gate results, restart and maintenance exercises, eligible stronger-model comparison, living v2 observations, and owner-facing evaluation specified by the experiment plan and historical review. The exact one-shot evidence and its limitations are in [COMPARISON_REPORT.md](COMPARISON_REPORT.md).

Do not interpret NOT READY as evidence that a particular candidate failed or that v3 should replace HADES v2.
