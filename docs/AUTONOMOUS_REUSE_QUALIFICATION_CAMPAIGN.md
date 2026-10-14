# Autonomous reuse and qualification campaign

**Authority:** frozen HADES v3 PRD and Bounded Operator architecture
**Starting revision:** CP75, `18a4af6738a5e0f4dce079a8302726a766eae49a`
**Current workstream:** CP90 now enforces at the gateway that a task parked `WAITING` with `operator_review_required` cannot accept a distinct workspace operation. The isolated gateway regression passed and its own test project is stopped; resources are retained for Tallowmere's cleanup review. CP89's A/C model attempts timed out before tool selection at matched 4/8 CPU profiles; no mutation occurred and CP81/CP85 evidence remains unchanged. CP71 is blocked and no Hypnos traffic is authorized. Next: finish the bounded A2/DBOS recovery-versus-complexity assessment and run decision-relevant offline authorization or compound-operation checks. Preserve the unresolved concurrent-turn boundary; do not claim arbitrary shell exactly-once behavior.
**ADR-010:** NOT READY; owner ratification required

## Objectives and order

| Order | Workstream | State | Dependency / exit evidence |
|---|---|---|---|
| 1 | Baseline, component inventory, reuse-first technology assessment | Research synthesis complete; A2/DBOS integration evidence pending | Frozen requirements mapped to current code and official upstream options; facts separated from hypotheses |
| 2 | CP75/CP81 correction diagnosis, safe CAS interface, and trusted bounded completion | Contract complete; A/C campaign completed with mixed results | Scalar passed 3/3 per candidate; structured no-tool 0/3; list mutations 3/3 with answer 2/3; fresh list recall 0/3. See report and JSONL. |
| 3 | Upstream Pydantic AI Harness proof of concept | Shell-only exact-call recovery passes; CP83 DBOS/Harness confirmed-result recovery 3/3; CP84 shared-tool/finalizer composition 3/3 | Candidate HTTP Handler and Harness Shell are not combined with DBOS in one run; no live-model score |
| 4 | Durable-engine integration spike | CP84 crossed process death after confirmed effect and before finalization, then completed through HADES finalizer 3/3 | Unknown outcomes, container/host restart, history privacy, cancellation/retry, and net maintenance burden remain |
| 5 | Compound work, general-purpose agency, recovery, protected actions | Planned | Held-out matched trials and independent final-state/security verification |
| 6 | Deletion-oriented simplification and ADR-010 evidence review | Planned | Replacement parity, reduced maintenance surface, decision-readiness table |
| 7 | CP90 parked workspace review-gate enforcement | Passed gateway contract; source-level concurrent-turn risk remains | New distinct workspace operation blocked with 409 while review marker is set; no second effect. See CP90 report. |

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

CP75 resolved CP74's 404 root cause as a mismatched JSON value shape and implemented stable-key/revision CAS with task-linked evidence. CP81 adds a gateway-verified completion contract for exactly one orchestrator-specified `memory_correct` operation; the model cannot author the contract, and arbitrary memory writes remain fail-closed. A/C scalar correction and recall passed 3/3 each; structured task selection and list recall failed safely, and list answer accuracy was 2/3. See the CP81 report and per-trial records.

Research and bounded disposable integrations continue without live GPU access. Stop only the affected operation when it requires new privileged access, production changes, HADES v2 interference, modification of frozen authority, or another Hypnos generation. Publish sanitized, complete checkpoints with normal fast-forward updates and exact-SHA CI.

## Current next steps

1. Preserve CP81's mixed A/C outcomes and CP85/CP89 pre-tool timeouts. CP89 used an independently named project and matched A/C profiles up to eight CPUs; further attempts on the same memory wording/profile are not decision-useful. Memory qualification remains incomplete; a future held-out model comparison needs a separately qualified latency/resource profile.
2. Keep CP83/84 guarantees bounded: same confirmed effect is replayed, unknown outcomes quarantine and block; neither DBOS nor a stable command ID proves exactly-once arbitrary shell effects. CP84 reuses HADES `gateway_call` and `finalize_turn` but does not run the candidate HTTP Handler or Harness Shell.
3. Compare the minimum CP84 DBOS integration against A2 StepPersistence for uncertain outcomes, delivery recovery, history privacy, cancellation/retry bounds, and operations burden before adoption.
4. Advance deterministic CAS, stale-revision, cross-domain, replay, compound-operation, and protected-action contracts with independent postconditions; refresh Cinder's v2 evidence only from an agreed read-only snapshot.
5. Review the newly identified concurrent `/api/turn` resume boundary: CP88 protects sequential resumes after a confirmed workspace effect but does not serialize concurrent turns. Investigate durable turn identity/history within existing task authority before claiming automatic recovery.
6. Keep CP71 `BLOCKED_EXTERNAL_DEPENDENCY`; no Hypnos, privileged firewall, HADES v2, frozen-document, or production work. CP75/CP80 remain untouched.

## CP81 checkpoint — bounded memory completion contract

CP81 implemented the narrow authenticated-orchestrator CAS completion contract and completed matched A/C CPU trials in a new project. Scalar correction plus restart/fresh-context recall passed 3/3 per candidate; structured correction invoked no tool in 0/3; list mutation was correct 3/3 but answer accuracy was 2/3, and list recall failed safely 0/3. A separate synthetic restart probe confirmed duplicate workspace dispatch because the gateway ignored an extra operation ID. The pinned Harness Shell wrapper identity-forwarding test passed with network disabled, proving a supported caller-side identity path but not durable replay. Full details are in [`CP81_MEMORY_COMPLETION_REPORT.md`](CP81_MEMORY_COMPLETION_REPORT.md) and the JSONL evidence. CP75/CP80 were untouched; the CP81 project and its owned resources were removed.

The CP77 DBOS probe is published and exact-SHA CI passed: run `38508417305` for `88d1017e7a27b87324ead831dcf4dd61f9720c75`. It remains contract evidence only. CP81's 2026-10-14 A/C model run and gateway replay reproduction are recorded in `CP81_MEMORY_COMPLETION_REPORT.md` and `experiment/results/cp81-autonomous-20261014.jsonl`. The fresh project had separate internal networks, volumes, and candidate/gateway services; CP75/CP80 remain untouched. CP71 stays `BLOCKED_EXTERNAL_DEPENDENCY`; no Hypnos inference or firewall modification occurred.

## CP82 checkpoint — identity-bound A2 workspace command replay

The pinned A2 wrapper derives each operation identity from the task ID, persisted Harness `tool_call_id`, and a dispatch ordinal so multiple Shell/FileSystem backend commands remain distinct; the gateway binds that identity and command digest to its existing effect record. Exact confirmed replay returns the original result; changed arguments reject; unresolved operations block new dispatch. A deterministic worker-crash test passed after killing the worker between gateway confirmation and Shell acknowledgment, then resuming the original tool call without a duplicate marker. Gateway restart replay and seeded unresolved-state cases also passed. The strict A2 repository probe passed under a deterministic peer. See [`CP82_WORKSPACE_COMMAND_REPLAY_REPORT.md`](CP82_WORKSPACE_COMMAND_REPLAY_REPORT.md).

Limits remain: HADES task stayed `RUNNING`; the old `StepPersistence` row remains `started`; a test-only coordinator rechecks it against the HADES ledger before each continuation but is not integrated in a general runtime; unknown shell outcomes have no canonical resolution path; A/C now inject provider call IDs but restart persistence is unqualified; Hermes still fails closed without an MCP call identity. All three disposable CP82 projects were removed after evidence capture; post-cleanup inventory found no CP82 resources, while the 14 CP75/80 containers remained up and disk free space was 44 GB. No Hypnos, privileged firewall, v2 runtime, or production change occurred.

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
- The CI workflow now runs three counterbalanced matched pairs with an isolated fixture reset after each run. The local CP80 project is isolated and contains only synthetic fixtures; it remains available for the cleanup lead's review, and Tern removed nothing. No Hypnos, GPU, firewall, HADES v2, or persistent service was involved.
- Exact-SHA CI run `38514751305` passed for `347839d0facfdabd7477397df4db98d70b6c1d1f`, including all six matched A2 profile runs, CP79 recovery verification, and the strict offline A/B/C suite. CI removed its own scoped resources; the local CP80 project remains for cleanup-lead review.
- Next: verify cleanup/CI, then prioritize task-linked memory correction/fresh-context recall and uncertain workspace command recovery. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; ADR-010 remains NOT READY.
