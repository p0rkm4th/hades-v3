# HADES v3 autonomous engineering report — 2026-10-14

**Status:** In progress; final owner handoff due by 18:00 CDT.  
**Authority:** Frozen HADES v3 PRD and Bounded Operator architecture.  
**ADR-010:** NOT READY; owner ratification remains required.

## Baseline and publication

- The goal cited `268e34babfc18e543dee9f93fdd5b7ba9a2243de` as last verified baseline; session preflight found both local and public `main` had already advanced and were synchronized at `eb2b212c090a72c68c0a8efd53043bec18334322`.
- CP92 initial source-review documentation is public at `c6f60a0e28fda6c5efdcf14647b0d74ce00d020f`; exact-SHA CI passed: [run 38616383083](https://github.com/p0rkm4th/hades-v3/actions/runs/38616383083).
- Follow-up documentation is public at `ebbdbacd34db1a67e5787dd29ec3bb320bbe09ce`; exact-SHA CI passed: [run 38617681737](https://github.com/p0rkm4th/hades-v3/actions/runs/38617681737). The strict three-harness offline, A2, DBOS, gateway, and lifecycle checks completed before cleanup.
- The CP92 source-review/reuse-evidence follow-up is public at `1a53ff0c062bc3108d96e2d413d906db4f76079d`; its exact-SHA CI passed: [run 38624076796](https://github.com/p0rkm4th/hades-v3/actions/runs/38624076796), including the strict three-harness offline qualification and scoped fixture cleanup.
- The qualification-matrix, partial-effect regression, and continuation-state follow-up is public at `4a70d56af4299fb35e6b9e6090ac1f3101ec5eed`; exact-SHA CI passed: [run 38626913801](https://github.com/p0rkm4th/hades-v3/actions/runs/38626913801). It includes the explicit one-of-two-effect rejection assertion. A later documentation correction makes clear that only commitment-specific approvals exist in the prototype and that `WAITING` does not prove a memory write never occurred; that wording receives a follow-up CI run.
- CP89 through CP91 evidence remains unchanged. No Hypnos, privileged firewall, HADES v2, or production action occurred.

## CP81 memory qualification and CP89 resource screen

- CP81 remains the historical baseline: scalar correction and fresh-context recall passed 3/3 for A and C; structured correction made no tool call in 3/3; list mutation passed 3/3 but answer correctness was 2/3; fresh-context list recall failed safely 0/3. These are narrow model observations, not broad memory qualification.
- CP89 used a new, unique synthetic project and reused cached images/model weights. Five A/C CPU requests at four/eight CPU allocations timed out before tool selection. All five tasks were independently `FAILED`; no memory effect existed and each seeded row remained at revision 1. These are provider/runtime/model latency failures, not CAS failures. No timeout or prompt tuning and no additional CP89 generation is planned.
- The stable-key/revision CAS gateway checks remain positive contract evidence: exact same-task retry returns the same effect; changed retry and stale revision reject; cross-user/domain attempts reject; effect and canonical update are atomic. The tests do not qualify model-mediated correction or fresh-context recall.
- CP92 source review found that `memory_write` and `memory_correct` require an authenticated active task and create task-linked effects transactionally. However, dispatch does not independently bind a candidate-selected key/value to the authenticated user's request. The candidate task starter sends only the goal; the orchestrator-authored CP81 completion contract verifies outcome at finalization but is not a general dispatch grant. A targeted source search found only commitment-specific approvals, not a general operation-grant record in this experiment. The frozen PRD permits an explicit authenticated request to authorize an action when its material scope is bound. The prototype has not proved that request-to-effect binding. This is an unqualified authorization/intent-validation path, not a demonstrated cross-domain exploit. A responsible fix must integrate the frozen protected grant/policy authority; no parallel grant system was added.
- The existing trusted completion contract still verifies only its exact single correction; generic writes without matching trusted completion criteria remain incomplete/`WAITING`. This task-state safeguard does not itself prevent a write from occurring.

### Candidate comparison (model-equivalent versus contract evidence)

| Candidate | Current memory evidence | CP89 result | Context/comparison limit |
|---|---|---|---|
| A — Pydantic AI | CP81 scalar mutation and fresh-context recall 3/3; list mutation 3/3 with semantic answer 2/3; structured correction selected no tool 0/3 | Three A requests (two structured, one scalar) timed out before tool selection; no mutation | Same Qwen3-8B CPU profile as C when model requests completed; CP89 resource load made no comparative behavior observable |
| C — lean loop | CP81 same narrow scalar/list outcomes as A; structured correction selected no tool 0/3 | Two C structured requests timed out before tool selection; no mutation | No basis to rank A/C from CP89; no further request tuning or retry |
| B — reduced Hermes | Strict-peer Hermes runtime paths provide protocol/contract evidence; no CP81 memory model trial | Not run | Qwen3-8B's 40,960 context is below Hermes's 64,000-token minimum; no model-equivalent memory comparison |
| A2 — Pydantic AI Harness | CP80 Shell-only and CP83/84 DBOS integrations passed deterministic workspace/recovery contracts | Not a memory trial | Separate pinned integration variant, not a replacement score for Candidate A and not live-model qualification |

## Workspace recovery review

- CP87/CP88/CP90 controls were rechecked in source. A workspace operation is bound to task, operation ID, and command digest in the existing effect ledger. Exact confirmed replay returns the prior result; changed commands under that identity reject; unresolved effects quarantine. The gateway writes `DISPATCHED` before runner I/O.
- The shared candidate API parks a sequential stateless resume after a confirmed workspace effect because the provider tool-call ID is not restored. New workspace dispatch requires task state `RUNNING`; pending approval/review tasks cannot dispatch new effects. The workspace runner terminates its process group on its bounded timeout.
- This closes the previously identified **sequential** blind-replay path. It does not restore a missing user answer, establish arbitrary shell exactly-once behavior, reconcile unknown shell outcomes, or qualify concurrent same-task turns. No new workspace experiment or code change was needed for CP92.
- Follow-up, network-disabled checks in the cached pinned A2 runner image (`sha256:90331becfbeb7bd15a10623367b457466963cc147ba9fd4e15b037650d6c3387`) passed `test_resume_gate.py`, `test_operation_identity_context.py`, and `test_step_persistence_interrupted_shell.py`. They confirm that the gate allows only absent pre-dispatch or matching confirmed original-call evidence, stable tool-call identities survive the tested Shell persistence path, and interrupted/default continuation can omit the pending call. They do not contact the gateway, execute a command, or qualify actual post-restart outcome reconciliation. No source change was justified: A2 has bounded same-call journal recovery; A/C park sequential resumes; arbitrary unknown shell effects still require review.

## Reuse-first assessment

- Official PyPI metadata checked 2026-10-14 shows current `pydantic-ai==2.56.0` and `pydantic-ai-harness==0.56.0`, matching CP80/CP83 pins. The Harness remains 0.x, so minor-release API movement requires pinning and deliberate requalification.
- Current Pydantic docs describe 50+ composable capabilities. They also state that local Shell is not an isolation boundary, `FileSystem.root_dir` does not constrain Shell, persistent/background commands can outlive an agent run, and Harness Spend limits are per run rather than durable shared budgets. Keep the HADES gateway/workspace as the enforcement boundary.
- Current DBOS docs describe pickle-backed workflow/step history by default, capability/toolset registration constraints, and retry multiplication risks. CP79/CP83/CP84 show positive bounded replay composition but no reduction in authoritative HADES task/effect/finalization code or total operational burden.
- A read-only check of the exact cached A2 image confirmed `pydantic-ai-harness==0.56.0` exports `step_persistence.recovery.inspect_recovery`. It aggregates the Harness store's latest/interrupted and settled snapshots, unresolved tool-call journal entries, and completed/failed tool names; it does not execute tools or query HADES task/effect state. This can reduce local journal-inspection glue, but cannot replace the cross-authority check or HADES ledger. No code change was needed.
- Added one narrow lifecycle regression placing one confirmed effect against a two-effect trusted commitment contract. The validator rejects the incomplete set explicitly; `python -m unittest experiment.tests.test_task_lifecycle` passed **16/16**. This is contract evidence, not an agent execution result.
- Upstream Harness Memory provides a namespaced notebook with optimistic concurrency/idempotency, but its documented mutation path does not prove HADES task/effect authority or canonical domain-scoped verification. Treat it as an unqualified contextual-memory option only; do not create a second canonical memory store.
- CP80 Shell-only had three candidate gateway effects versus 18 for Shell + FileSystem on one deterministic repository task, with the same independent result. This is narrow contract evidence, not model qualification.
- Current source-size snapshot: candidate API 770 lines (+65 from CP84), lifecycle contract 367 (unchanged), gateway 1,099 (+2), Hermes MCP proxy 117. Size alone is not complexity, and safety corrections remain necessary. No custom code was deleted or dependency changed.

## Verification, infrastructure, and coordination

- Earlier CP92 run: `python -m unittest experiment.tests.test_task_lifecycle experiment.tests.test_candidate_finalization`: **41 passed**. The new focused task-lifecycle suite then passed **16/16** with the added 1-of-2 partial-effect assertion.
- A host attempt to run `experiment/candidates/test_workspace_identity.py` could not import the pinned `pydantic_ai` dependency. It is not counted as a test pass; the network-disabled runner-image checks above and CP91 exact-SHA CI provide the available evidence.
- `git diff --check` and targeted Gitleaks scan passed before the follow-up documentation commit.
- CP89 resources remain stopped and retained: four project containers, four internal networks, and nine uniquely prefixed volumes; no new image was built. CP90 resources remain stopped and retained: six project containers, four internal networks, five project volumes, and five project-tagged images. Tallowmere owns cleanup review; no resource was deleted. CP75/CP80 remain untouched. CP89 observed 44 GB free at its cleanup boundary; no new persistent storage was created today.
- A protected note was sent to Cinder with the CP92 memory-intent finding and a request for relevant high-level v2 evidence. No reply is observed as of the latest check. A protected response was appended to Tallowmere's cleanup request: no upcoming v3 activity depends on the five listed exact image digests; Qwen3-14B remains a historical reproduction asset, not a planned run. No cleanup permission was inferred and no resource was changed.
- Read-only public check found HADES v2 `main` still at `eccaf8a4eec9802341cc31261496b98fe50856be`, with two successful associated safety/regression CI jobs ([38522183010](https://github.com/p0rkm4th/hades/actions/runs/38522183010), [38522042760](https://github.com/p0rkm4th/hades/actions/runs/38522042760)). This establishes fresh v2 source/CI status only; no v2 runtime was inspected and no owner-acceptance result was received.

## Decision readiness and next step

No harness is selected. A and C have narrow scalar/list positives and repeated structured pre-tool timeouts; no current model-equivalent Hermes result is available on the 40,960-token CPU profile. Deterministic A2/DBOS evidence does not rank model quality or provide owner acceptance. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`; no GPU generations were sent.

The smallest decision-changing work is: (1) define how the existing protected grant/policy authority binds an explicit memory request to the exact proposed mutation or requires clarification/approval; (2) obtain a resource-adequate matched A/C memory correction, restart, and fresh-context campaign without tuning CP89; (3) qualify same-task concurrent workspace turns and unknown-effect reconciliation; and (4) measure A2/DBOS maintenance reduction. Current Cinder v2 runtime/owner-acceptance evidence is also needed before a fair architecture decision. Production implementation and ADR ratification remain out of scope.

**Closeout update required:** refresh exact remote SHA and Actions outcome for this report's commit, worktree state, latest protected-note replies, and any change in owned-resource status before 18:00 CDT.
