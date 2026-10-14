# Autonomous reuse and qualification campaign

**Authority:** frozen HADES v3 PRD and Bounded Operator architecture
**Starting revision:** CP74, `6886e019069fc197df05ba8ed6781d66e45b51a3`
**Current workstream:** CP75 memory-correction diagnosis and reuse-first assessment
**ADR-010:** NOT READY; owner ratification required

## Objectives and order

| Order | Workstream | State | Dependency / exit evidence |
|---|---|---|---|
| 1 | Baseline, component inventory, reuse-first technology assessment | In progress | Frozen requirements mapped to current code and maintained upstream options |
| 2 | CP75 correction diagnosis and safe correction interface | Complete; candidate memory workflow unqualified | CAS contract verified; A/C failures and restart reads preserved in CP75 report/results |
| 3 | Upstream Pydantic AI Harness proof of concept | Planned, separate candidate revision | Pinned isolated integration; same trusted HADES gateway and independent outcome oracle |
| 4 | At most two durable-engine spikes | Planned; DBOS and Temporal are leading candidates | Demonstrate resume and retry while HADES remains sole task/effect authority; no external effect replay |
| 5 | Compound work, general-purpose agency, recovery, protected actions | Planned | Held-out matched trials and independent final-state/security verification |
| 6 | Deletion-oriented simplification and ADR-010 evidence review | Planned | Replacement parity, reduced maintenance surface, decision-readiness table |

## Verified baseline

- V3 source and `origin/main` were both CP74 `6886e019069fc197df05ba8ed6781d66e45b51a3`; working tree was clean at campaign start.
- CP74 persistence contract and its failed candidate corrections remain unchanged. A and C each had one failed correction (HTTP 404), no canonical mutation, and one successful initial and independently seeded fresh-context read. The 404 request arguments were not retained, so the exact mismatch remains unknown. B was excluded because the available CPU profile is below its documented context minimum.
- Current A uses pinned `pydantic-ai-slim[openai]==2.55.0`; a current upstream Harness option is being assessed under a distinct revision and will not replace scored A silently.
- Current B is a reduced Hermes profile pinned to upstream commit `e4d86423856350825a3a0dc4f52aed89759e11bd`; context-compliant deterministic-peer results remain contract evidence, not model-equivalent CPU scoring.
- C remains the lean comparison baseline. It is not presumed to be the preferred production foundation.
- HADES-infra's local checkout has owner changes and no confirmed canonical remote/branch policy. Drafts remain untouched and uncommitted. Cinder's v2 runtime status is not established by a public source revision alone.
- No Hypnos generation, firewall privilege, production service, or HADES v2 change is authorized by this campaign.

## Evidence categories

Every result must be labeled as **RESEARCH** (upstream source/documentation), **CONTRACT TEST** (strict peer or deterministic integration), **LIVE EXPERIMENT** (actual candidate/model behavior), **OPERATIONAL EVIDENCE** (verified deployed infrastructure), or **OWNER ACCEPTANCE**. These categories are not interchangeable. Preserve historical negative evidence and bind every scored result to source, model, settings, fixtures, and independent oracle.

## Decision path and stop conditions

The highest-value immediate question is whether CP74's shared correction failure came from the query, JSON shape/value, retrieval freshness, or candidate tool serialization. Capture only sanitized classifications, then change the interface only after the cause is known. A keyed conditional update is a candidate improvement, not an assumed fix. A fuzzy search may nominate records; a stable scoped key and current revision/value must authorize mutation.

Research and bounded disposable integrations continue without live GPU access. Stop only the affected operation when it requires new privileged access, production changes, HADES v2 interference, modification of frozen authority, or another Hypnos generation. Publish sanitized, complete checkpoints with normal fast-forward updates and exact-SHA CI.

## Next actionable step

Complete CP76's reuse-first assessment using current official release/docs for the Pydantic AI Harness, Hermes, DBOS/Temporal/Restate/Prefect, Hindsight, MCP, OpenTelemetry, and existing test/fault-injection tools. Validate the existing draft's version claims, compatibility, and license/maintenance evidence, then select at most two bounded offline integration hypotheses. Preserve Candidate A/B/C scoring and the shared HADES authority boundary. Do not revisit the already blocked CP71 firewall dependency or run Hypnos inference.
## Current checkpoint (2026-10-14): CP75 complete, CP76 next

- Stable-key/revision CAS implementation and gateway regressions are complete; existing schema migration, task/domain identity, idempotency, stale/cross-domain rejection, and atomicity are verified.
- A/C each ran three held-out CPU correction cases. Scalar/list mutations were persisted correctly but tasks stayed `WAITING` for missing model checkpoint; structured correction prompts made no tool call, falsely claimed success, and were correctly `FAILED`. Restarted scalar fresh-context recall passed for both; C list recall failed to call memory tools. CP74 outcomes remain unchanged. Detailed results: `docs/CP75_MEMORY_CAS_REPORT.md` and `experiment/results/cp75_memory_cas.jsonl`.
- Related suites: gateway 6, lifecycle 14, finalization 16 all pass. No Hypnos generation or firewall preflight occurred. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`.
- Cinder is current on the cross-note finding; v2 remains owned by Cinder and untouched.
- Next action: finish CP76 upstream reuse research, then decide whether either bounded durable execution or upstream Pydantic AI Harness integration merits a pinned offline spike. Do not build more memory infrastructure or tune the correction prompt to these examples. ADR-010 remains NOT READY.
