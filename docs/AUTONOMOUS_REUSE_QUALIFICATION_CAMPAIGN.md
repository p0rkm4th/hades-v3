# Autonomous reuse and qualification campaign

**Authority:** frozen HADES v3 PRD and Bounded Operator architecture
**Starting revision:** CP75, `18a4af6738a5e0f4dce079a8302726a766eae49a`
**Current workstream:** CP77 complete; A2 Harness gateway-backed workspace proof follows
**ADR-010:** NOT READY; owner ratification required

## Objectives and order

| Order | Workstream | State | Dependency / exit evidence |
|---|---|---|---|
| 1 | Baseline, component inventory, reuse-first technology assessment | Research synthesis complete; A2/DBOS integration evidence pending | Frozen requirements mapped to current code and official upstream options; facts separated from hypotheses |
| 2 | CP75 correction diagnosis and safe correction interface | Complete; candidate memory workflow unqualified | CAS contract verified; A/C failures and restart reads preserved in CP75 report/results |
| 3 | Upstream Pydantic AI Harness proof of concept | API fit established; runtime integration pending; separate A2 revision | Pinned isolated integration; every command uses authenticated `workspace_exec` and its HADES effect record |
| 4 | Durable-engine integration spike | DBOS replay contract probe positive; HADES integration pending | Demonstrate resume/retry while HADES remains sole task/effect authority; no external effect replay |
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

## Current next steps

1. Run the bounded DBOS integration against the real HADES gateway and commitment simulator in a separate unique disposable project. The CP77 SQLite probe established only step replay plus target-side idempotency; stop if DBOS requires a second task/effect authority.
2. Compare A2 Shell-only against Shell plus FileSystem using the same synthetic task and independent oracle. Keep it separate from scored Candidate A. Investigate uncertain workspace-command recovery using existing gateway mechanisms before adding custom recovery code.
3. Continue task-linked memory correction/retrieval only after recording the known CP75 outcomes; CP71 remains blocked and no Hypnos generations are authorized.

The CP77 DBOS probe is published and exact-SHA CI passed: run `38508417305` for `88d1017e7a27b87324ead831dcf4dd61f9720c75`. This is still contract evidence only. Do not introduce persistent services or change A/B/C scores. CP71 stays `BLOCKED_EXTERNAL_DEPENDENCY`; no firewall checks or Hypnos inference.

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

## CP77 checkpoint (2026-10-13): DBOS replay contract smoke

- Installed `dbos==3.2.0` only in `/tmp/hades-cp77-dbos-venv`; Python was 3.14.7. The reproducible probe and exact pin are under `experiment/spikes/cp77_durable_execution/` and `experiment/spikes/cp77_durable_execution_probe.py`.
- A subprocess exited after an idempotent synthetic target accepted the fixed effect ID but before DBOS persisted its step result. On restart DBOS recovered the workflow, called the step a second time, and returned the original task/effect identity. The independent synthetic ledger recorded two step attempts and one canonical effect row.
- This is **CONTRACT TEST** only. It did not use HADES gateway, grants, simulator, PostgreSQL, a model, or candidate runtime. It proves DBOS does replay an interrupted step and target idempotency is needed; it does not prove HADES integration or candidate benefit. See `docs/CP77_DBOS_PROCESS_RECOVERY_PROBE.md`.
- A narrowly scoped CI step runs the probe with the exact DBOS pin. Next experiment must use a fresh, unique HADES fixture project and real gateway/simulator before assessing whether DBOS reduces custom recovery plumbing. No active fixture project was modified for this smoke. CP71 remains blocked; no GPU or firewall operation occurred.

## A2 feasibility update (2026-10-14): gateway-backed workspace is the only acceptable composition

- **RESEARCH / pinned-package inspection:** `pydantic-ai-harness==0.56.0` exposes `Shell`, `FileSystem`, `Coder`, and the core `WorkspaceBackend` protocol. The protocol supports a command-only backend; Pydantic derives file operations through that backend's shell. This allows a narrow adapter to route each command through HADES `workspace_exec`, retaining the existing per-task `WORKSPACE_COMMAND` effect record and isolated workspace runner.
- **Security finding:** upstream explicitly documents that Shell allowlists and FileSystem root checks are guardrails, not isolation. `LocalWorkspaceBackend` would execute on the agent host and bypass HADES effect records. `Coder` includes unrestricted shell by default. A2 must use only the HADES-backed workspace, with no local workspace, SSH, host mount, or direct candidate access to other services.
- **Fit and limitation:** a command-only adapter appears sufficient for foreground commands and shell-derived file operations. The existing gateway does not pass per-call env/timeout controls, and its runner has a fixed command timeout; these semantics need explicit tests. Do not claim background/persistent shell compatibility until measured. The adapter is HADES-specific glue, while command and file-agent capabilities remain upstream.
- **Decision:** A2 is feasible enough for one disposable proof, not yet qualified. If `WorkspaceBackend` needs direct filesystem or shell access that evades gateway records, reject the composition. Keep historical Candidate A and all prior scores unchanged.

## CP78 checkpoint (2026-10-14): A2 gateway workspace contract

- A separate A2 proof used pinned Pydantic AI Harness `0.56.0` and Pydantic AI `2.56.0` with the supported command-only `WorkspaceBackend`. Every operation passed through authenticated HADES `workspace_exec`; no local shell, host mount, SSH, or live model was used.
- Three clean deterministic repetitions each used four scripted model calls, 18 candidate workspace commands and one independent oracle command. All 19 effects per run were confirmed; the independent test/source oracle passed. Task state intentionally remained `RUNNING`, so this does not test finalization or score historical Candidate A. See [CP78 report](CP78_A2_HARNESS_WORKSPACE_REPORT.md) and [pinned probe](../experiment/spikes/a2_gateway_workspace/README.md).
- The combined Shell/FileSystem route has high command/effect overhead for this small task. Compare a Shell-only route before accepting extra capability. Fixed gateway environment/timeout and uncertain-command recovery remain limitations; upstream `Coder` is not qualified.
- The previous exact-SHA CI failure at fixture startup remains unexplained. Local equivalent startup and uncached build passed; do not infer the hosted failure's cause. The A2 CI route now uses its own unique project and unconditional cleanup; verify the newly published exact-SHA result.
- All CP78 resources were removed. No HADES v2, Hypnos, firewall, or persistent service changed. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; ADR-010 remains NOT READY.

## CP79 checkpoint: DBOS replay through the HADES gateway

- DBOS Transact 3.2.0 resumed three disposable workflows after the worker died between gateway response and DBOS step persistence. Each replay preserved the original task/effect IDs; HADES recorded one canonical receive and one confirmed effect per task.
- An independent verifier checked task, user/domain, exact approval digest/consumption, effect request/identity, and simulator state before trusted HADES finalization. All three tasks and final responses persisted as completed. This is a **CONTRACT TEST**, not model or candidate qualification, and DBOS metadata was disposable rather than an authority.
- The first Python 3.13/3.14 runner attempts failed before effect dispatch because their bundled SQLite did not support DBOS's `unixepoch('subsec')` schema default. That setup failure is preserved. Python 3.11 runner passed. Full evidence: `docs/CP79_DBOS_GATEWAY_RECOVERY_SPIKE.md`.
- Local CP79/A2 containers, networks, and volumes are absent. Tagged experiment images remain reproducible and are reported to the storage-cleanup lead for disposition; no image or shared build cache was deleted.
- Exact-SHA CI run `38512629038` passed for `cde1ff32a67eb902aefaec42a1cd60730366629b`, including CP79 integration, A2, existing lifecycle/gateway regressions, and the strict three-harness offline suite.
- Next: compare Shell-only A2 against the current gateway-backed Harness composition, then complete held-out compound/recovery work with independent final-state oracles. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; no new GPU or firewall operation is authorized. ADR-010 remains NOT READY.

## CP80 checkpoint: A2 Shell-only reduces workspace effect overhead

- The pinned A2 Pydantic AI Harness proof used the same synthetic repository task, task wording, gateway workspace, 20-second bound, deterministic peer and independent source/test oracle with two capability profiles.
- Four local repetitions per profile passed. Shell + FileSystem used four model turns and 18 candidate gateway effects (plus one oracle); Shell-only used four turns and three candidate effects (plus one oracle). Independent task/effect inspection confirmed unique IDs, amber task/domain binding, confirmed workspace-only effects, and correct final source/tests. Task remained RUNNING by design.
- The result supports using Shell alone for this bounded repository task and avoiding 15 unnecessary HADES gateway effect records per run. It is contract evidence, not a live-model result, task-finalization test, general shell-safety proof, or score for historical Candidate A. See `docs/CP80_A2_SHELL_ONLY_REPORT.md` and `experiment/results/cp80_a2_workspace_profiles.jsonl`.
- The CI workflow now runs three counterbalanced matched pairs with an isolated fixture reset after each run. The local CP80 project is isolated and contains only synthetic fixtures; it remains available for the cleanup lead's review, and Tern removed nothing. Exact-SHA CI is pending. No Hypnos, GPU, firewall, HADES v2, or persistent service was involved.
- Next: verify cleanup/CI, then prioritize task-linked memory correction/fresh-context recall and uncertain workspace command recovery. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; ADR-010 remains NOT READY.
