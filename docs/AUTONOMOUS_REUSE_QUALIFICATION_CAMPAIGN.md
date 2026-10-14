# Autonomous reuse and qualification campaign

**Authority:** frozen HADES v3 PRD and Bounded Operator architecture
**Starting revision:** CP75, `18a4af6738a5e0f4dce079a8302726a766eae49a`
**Current workstream:** CP76 reuse-first assessment; select bounded A2 and DBOS spikes
**ADR-010:** NOT READY; owner ratification required

## Objectives and order

| Order | Workstream | State | Dependency / exit evidence |
|---|---|---|---|
| 1 | Baseline, component inventory, reuse-first technology assessment | Research synthesis complete; A2/DBOS integration evidence pending | Frozen requirements mapped to current code and official upstream options; facts separated from hypotheses |
| 2 | CP75 correction diagnosis and safe correction interface | Complete; candidate memory workflow unqualified | CAS contract verified; A/C failures and restart reads preserved in CP75 report/results |
| 3 | Upstream Pydantic AI Harness proof of concept | Selected, not started; separate A2 revision | Pinned isolated integration; same trusted HADES gateway and independent outcome oracle |
| 4 | Durable-engine integration spike | DBOS selected first; Temporal deferred | Demonstrate resume/retry while HADES remains sole task/effect authority; no external effect replay |
| 5 | Compound work, general-purpose agency, recovery, protected actions | Planned | Held-out matched trials and independent final-state/security verification |
| 6 | Deletion-oriented simplification and ADR-010 evidence review | Planned | Replacement parity, reduced maintenance surface, decision-readiness table |

## Verified baseline

- At CP75 campaign start, V3 source and `origin/main` were both CP74 `6886e019069fc197df05ba8ed6781d66e45b51a3`; working tree was clean. CP75 is now published at `18a4af6738a5e0f4dce079a8302726a766eae49a`.
- CP74 persistence contract and its failed candidate corrections remain unchanged. A and C each had one failed correction (HTTP 404), no canonical mutation, and one successful initial and independently seeded fresh-context read. The 404 request arguments were not retained, so the exact mismatch remains unknown. B was excluded because the available CPU profile is below its documented context minimum.
- Current A uses pinned `pydantic-ai-slim[openai]==2.55.0`; a current upstream Harness option is being assessed under a distinct revision and will not replace scored A silently.
- Current B is a reduced Hermes profile pinned to upstream commit `e4d86423856350825a3a0dc4f52aed89759e11bd`; context-compliant deterministic-peer results remain contract evidence, not model-equivalent CPU scoring.
- C remains the lean comparison baseline. It is not presumed to be the preferred production foundation.
- HADES-infra's local checkout has owner changes and no confirmed canonical remote/branch policy. Drafts remain untouched and uncommitted. Cinder's v2 runtime status is not established by a public source revision alone.
- No Hypnos generation, firewall privilege, production service, or HADES v2 change is authorized by this campaign.

## Evidence categories

Every result must be labeled as **RESEARCH** (upstream source/documentation), **CONTRACT TEST** (strict peer or deterministic integration), **LIVE EXPERIMENT** (actual candidate/model behavior), **OPERATIONAL EVIDENCE** (verified deployed infrastructure), or **OWNER ACCEPTANCE**. These categories are not interchangeable. Preserve historical negative evidence and bind every scored result to source, model, settings, fixtures, and independent oracle.

## Decision path and stop conditions

CP75 resolved CP74's 404 root cause as a mismatched JSON value shape and implemented stable-key/revision CAS with task-linked evidence. The correction contract is verified; model-mediated correction and completion remain unqualified. Next use the CP76 reuse hypotheses to test whether upstream durable execution and Harness capabilities reduce custom burden without creating another authority.

Research and bounded disposable integrations continue without live GPU access. Stop only the affected operation when it requires new privileged access, production changes, HADES v2 interference, modification of frozen authority, or another Hypnos generation. Publish sanitized, complete checkpoints with normal fast-forward updates and exact-SHA CI.

## Next actionable step

Start the two selected offline hypotheses as separately pinned, disposable work: (1) A2 Pydantic AI Harness using the existing isolated shell/workspace boundary; (2) DBOS with a disposable system database and a simulator operation mediated by the current HADES gateway. Begin with the DBOS integration design and prove that retries cannot dispatch an effect outside the existing effect ID/reconciliation contract. Do not introduce a persistent service or change A/B/C scores. CP71 stays `BLOCKED_EXTERNAL_DEPENDENCY`; no firewall checks or Hypnos inference.

## CP76 checkpoint (2026-10-13): research synthesis complete, spikes next

- Stable-key/revision CAS implementation and gateway regressions are complete; existing schema migration, task/domain identity, idempotency, stale/cross-domain rejection, and atomicity are verified.
- A/C each ran three held-out CPU correction cases. Scalar/list mutations were persisted correctly but tasks stayed `WAITING` for missing model checkpoint; structured correction prompts made no tool call, falsely claimed success, and were correctly `FAILED`. Restarted scalar fresh-context recall passed for both; C list recall failed to call memory tools. CP74 outcomes remain unchanged. Detailed results: `docs/CP75_MEMORY_CAS_REPORT.md` and `experiment/results/cp75_memory_cas.jsonl`.
- Related suites: gateway 6, lifecycle 14, finalization 16 all pass. No Hypnos generation or firewall preflight occurred. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`.
- Cinder is current on the cross-note finding; v2 remains owned by Cinder and untouched.
- Current A lock remains `pydantic-ai-slim[openai]==2.55.0`; current B remains pinned to historical Hermes commit `e4d86423856350825a3a0dc4f52aed89759e11bd`. A separate current Pydantic AI Harness candidate is warranted by the upstream capability surface; current Hermes release features are not credited to historical B.
- Selected two bounded research hypotheses: A2 Pydantic AI Harness and DBOS Transact. Temporal, Restate, and Prefect are documented alternatives, not additional deployments. Existing Hindsight remains a recall candidate while the CP75 CAS contract remains the canonical mutation path.
- CP76 findings, current versions/licenses, architecture gaps, build-versus-reuse rationale, and official source links are in `docs/REUSE_FIRST_TECHNOLOGY_ASSESSMENT.md`. This is **RESEARCH**, not runtime qualification. No package was installed; no service, Docker resource, v2 environment, firewall, or GPU route changed.
- CP75 trial outcomes remain unchanged. Candidate memory workflow is still unqualified: completion checkpoint omission and structured-value no-tool behavior remain open.
- Next: begin DBOS spike using disposable state and the existing effect authority, then separate A2 Harness proof of concept. Do not install a persistent workflow service, modify scored candidates, revisit CP71's unchanged firewall blocker, or run Hypnos inference. ADR-010 remains NOT READY.
