# HADES v3 autonomous engineering day — progress handoff

**Date:** 2026-10-14, in progress (10:29 AM CDT)
**Authority:** frozen PRD and Bounded Operator architecture
**ADR-010:** NOT READY
**Next update:** before 6:00 PM CDT

## Starting state and publication

- Started from local and public `main` at CP82 `625c08e4bf6cad953c03745868f4c24dc010d343`, with unpublished CP83 DBOS/Harness changes and a dirty worktree.
- Published CP83 and follow-ups by normal fast-forward. Current local and remote `main` at report entry: `6f94dd74baf582eba3a8f15e8c3a3a4a707d5894`; worktree was clean before this report update.
- Exact-SHA CI passed on CP83 `252f21917d065cdf74de3d4c87f3bdacd0be3165`, run [38586048285](https://github.com/p0rkm4th/hades-v3/actions/runs/38586048285), quarantine follow-up `6b71fbe78a6650e0b4d421815a622044d1a9f1cb`, run [38586964117](https://github.com/p0rkm4th/hades-v3/actions/runs/38586964117), repeated-result check `6526f6cc71825bbc6079958678477b8314990888`, run [38587824181](https://github.com/p0rkm4th/hades-v3/actions/runs/38587824181), and v2-control-doc update `c6ddf4de04d45959dbf20a478d713381fe12d9d6`, run [38588165471](https://github.com/p0rkm4th/hades-v3/actions/runs/38588165471). At 10:29 CDT, `e329cde` run `38588504783` and current `6f94dd7` run `38588664035` were still in progress, checked through the public GitHub API.
- Public privacy checks passed for each publishable change; Gitleaks reported no findings. No private network values or credentials were added.

## CP83 DBOS and A2 evidence

- Pinned Pydantic AI Harness `0.56.0`, Pydantic AI `2.56.0`, DBOS `3.2.0`; deterministic `FunctionModel`, no live inference. DBOS metadata used SQLite in runner tmpfs. The candidate runner had no host shell, Docker socket, database credential, or provider network.
- A worker killed after HADES persisted a confirmed workspace command but before Harness received it recovered the same effect across three repetitions. Each had two model generations, one marker, and no duplicate effect. Repeated completed-result retrieval added no model call or effect.
- A separate timeout case wrote one marker, timed out, and left one effect `QUARANTINED`. After restart, gateway replay was refused. Repeated resume added no effect/generation; an independent task found one marker. The Pydantic run raised `WorkspaceUnavailableError` with no final response. The direct spike task remained `RUNNING` because it deliberately bypassed the candidate API orchestrator.
- The candidate API's existing exception classifier maps quarantine to `WAITING` for reconciliation and confirmed effects with lost response to `WAITING` for response recovery. It was extracted without changing outcomes and has new unit regressions. The finalization suite passes 24 tests; task lifecycle suite passes 16. These are unit/contract checks, not an integrated A2+DBOS+candidate-API run.
- Additional local verification: the 24 candidate-finalization and 16 lifecycle tests passed. The adapter identity test passed in a one-shot, `--network none`, read-only container using the cached A2 Harness image and read-only source mount; it confirmed Pydantic and lean adapters bind workspace dispatch to the same persisted model tool-call ID. Host pytest/Pydantic packages were absent, so no dependency was installed. No shared services were used.
- All fresh CP83 Compose projects were cleaned by exact project scope. Verification found zero CP83 containers, networks, or volumes; the 14 existing CP75/CP80 containers remained running. Free disk remained 39 GB. No Hypnos, privileged host, HADES v2, or shared-resource changes occurred.
- DBOS is not adopted: CP83 supports a credible confirmed-result recovery composition and safe quarantine, but does not prove end-to-end completion or a net maintenance reduction. A2/DBOS integration remains a separate experimental candidate; no A/B/C historical score changed.
- Reuse review counted the current shared candidate API at 705 LOC, trusted lifecycle contract at 367 LOC, and gateway at 1,097 LOC; those HADES-specific authority/protocol layers remain needed under DBOS. A2 workspace adapter/identity wrapper are 97/69 LOC. The 53-line CP82 resume gate is test-only and CP83's 363-line driver is test code. This is a code-surface observation, not a full complexity metric: CP83 does not demonstrate net production LOC reduction because candidate API/finalizer integration is absent and DBOS adds a dependency plus durable-history configuration. The official Harness docs confirm Shell is not an isolation boundary and the 0.x package may change across minor versions; the HADES gateway workspace remains necessary.
- Current Pydantic DBOS guidance says workflow history records workspace command arguments/file contents, recommends PostgreSQL for production, and advises a payload codec; it also documents retry multiplication, buffered event delivery, and cancellation caveats. CP83's tmpfs SQLite/synthetic-data run tested none of those operational properties. They are required gates before DBOS could be recommended.

## CP81 memory and comparison status

- CP81's existing matched CPU evidence remains mixed and unchanged: A/C scalar correction plus restart/fresh-context recall passed 3/3; structured corrections selected no tool 0/3; list mutations were canonically correct 3/3, but answers were correct 2/3 and fresh-context list recall was 0/3. Hermes remains ineligible on the 40,960-token CPU context.
- No new A/C memory-model trial was run. The active local model server is inside the existing CP75 project; no independent model endpoint was available in the new isolated project. I did not connect to, restart, or reconfigure shared CP75/CP80 resources. Further candidate memory trials require an independently approved/available model route or release of an appropriate fixture.
- CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`. No Hypnos inference or firewall helper was used.

## Cross-restart workspace-command safety review

- Source review confirms the gateway requires a task-bound `operation_id`, stores a canonical digest with the existing `WORKSPACE_COMMAND` effect, returns the saved result for an identical `CONFIRMED` replay, rejects changed arguments for that identity, and quarantines `DISPATCHED`/unknown outcomes without redispatch. Candidate A/C adapters derive IDs from the original provider tool-call identity; A2's wrapper derives stable IDs from task, persisted Harness call ID, and dispatch ordinal.
- The A2 identity-forwarding contract passed in a fresh read-only, network-disabled container. CP82/CP83 restart probes already provide stronger deterministic integration evidence for reuse of the same effect after confirmed response loss. A quarantined timeout remains blocked and requires independent review; arbitrary shell commands do not have general canonical reconciliation and are not exactly-once.
- No new gateway code or experiment project was needed. This closes the specific “a repeated command gets a new effect” source gap for the tested adapters, while leaving A/C persistent runtime recovery and unknown-result resolution unqualified.

## Living HADES v2 control

- Read-only public API recheck found v2 `main` at `eccaf8a4eec9802341cc31261496b98fe50856be`; exact-SHA Public CI runs `38522183010` and `38522042760` passed.
- Current public blocker/acceptance records describe an owner-authorized Open WebUI 0.12.0 promotion and PASS + PERSISTENCE slices for conversation, memory, bounded delegation, and household. Direct owner dogfood remains active. `CAMPAIGN_STATE.md` is stale relative to the newer blocker record. These are public owner-acceptance records, not Tern-observed v2 runtime evidence or a matched v2/v3 comparison.
- No v2 service, runtime, data, or checkout was touched. See [pinned v2 control review](V2_CONTROL_BASELINE.md).

## Coordination and shared resources

- A direct Codex thread listing was attempted at this milestone, but the local TUI MCP transport returned a connection error. No Tallowmere or Cinder reply was received in this session; no message receipt is claimed.
- The shared CP75/CP80 fixture containers remain active and untouched. No new Docker project, volume, image, or host rule was created today; the identity regression ran as a one-shot network-disabled container from an already cached image, with auto-removal. Current free disk was 44 GB.
- Documentation-only follow-up updates the campaign next-step pointer, current state, CP83 complexity assessment, and matrix without changing historical test results. `git diff --check` passed; Gitleaks scanned `docs/` and found no leaks; private-address/account-path scan of the touched public docs found no matches.

## Decision status and next actions

ADR-010 remains **NOT READY**. A2/DBOS now has stronger recovery evidence than CP82, while its unresolved-effect continuation and task/API integration remain open. Candidate C remains a useful minimal comparison baseline; current evidence does not justify selecting it or a winner. Existing A/B/C scores and negative outcomes remain unchanged.

1. Exact-SHA CI recheck: `6526f6c` passed; `c6ddf4d`, `e329cde`, and `6f94dd7` were still in progress at 10:23 CDT. Recheck at the next checkpoint.
2. Keep CP83 as bounded contract evidence. Next engineering question: can DBOS integrate with the candidate API's trusted finalizer while preserving one HADES task/effect authority? Do not add a second ledger or persistent service just to test it.
3. Do not retry CP81 model trials until an eligible isolated model endpoint and independently owned fixture are available. Preserve CP81 scores and Hermes context limits.
4. At end of day, update this report with completed work, exact CI, resource cleanup, and the next actionable handoff. Stop initiating new engineering at 6:00 PM CDT.
