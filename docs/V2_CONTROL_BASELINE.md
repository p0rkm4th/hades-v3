# HADES v2 control baseline

## Recorded source observation

- Repository: `https://github.com/p0rkm4th/hades`
- Visibility: public, confirmed from the anonymous GitHub API.
- Default branch: `main`.
- Observed commit: `fe222446c83a4034bfa37ac5a493d6a30b9abe74`.
- Commit timestamp: `2026-10-11T18:57:44Z` (GitHub API committer timestamp).
- Observation timestamp: `2026-10-11`.
- Observation type: read-only source-control observation; not a reproduced deployment or controlled benchmark.
- The tree at this exact commit contains [`acceptance/owner-workflows.md`](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/acceptance/owner-workflows.md), [`CAMPAIGN_STATE.md`](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/CAMPAIGN_STATE.md), [`docs/daily-driver-failures.md`](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/docs/daily-driver-failures.md), [`docs/current-blockers.md`](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/docs/current-blockers.md), and [`docs/decision-plane-alpha.md`](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/docs/decision-plane-alpha.md). Their presence is confirmed from the commit tree; details must be reviewed at this pinned revision before drawing checkpoint conclusions.

## Evidence limitations

This records the exact source revision observed during setup. The local workspace does not contain a HADES v2 checkout. The public tree exposes the evidence documents listed above, but their presence alone does not establish deployed artifact identity, runtime/model versions, non-secret configuration profile, complete acceptance results, unresolved failure state, or comparable performance measurements. Those fields remain unknown until read-only review of their pinned contents or an authorized, non-disruptive observation supplies evidence.

The v2 development lane remains independent and active. Recheck its latest source and acceptance evidence at each meaningful comparison checkpoint; do not treat this moving revision as the fixed historical baseline or infer that historical defects remain unresolved.

## Living-control source recheck — 2026-10-11

- Anonymous GitHub API recheck still reports public `main` at `fe222446c83a4034bfa37ac5a493d6a30b9abe74`, the same source snapshot as the recorded setup baseline. No v2 source change was observed at this checkpoint.
- The pinned tree still contains the owner-workflow scoreboard, campaign state, daily-driver failure log, blocker log, and Decision Plane alpha evidence listed above. The historical risk review's October 11 owner-dogfood notes remain historical evidence; they do not establish that those failures persist at this exact checkpoint.
- No authorized current v2 runtime observation or matched runtime/model/configuration evidence was collected. Consequently this is a source-only living-control check, not a new acceptance result or a controlled comparison.
- Latest eligible v2 source SHA for this project checkpoint remains `fe222446c83a4034bfa37ac5a493d6a30b9abe74`.

### Workspace and upstream verification — 2026-10-11

- A read-only check of the local HADES workspace found `main` at `6a46e18657b17c261a5725de3b0d09b24e7d3f60` (commit time `2026-09-30T03:42:37-05:00`). That checkout is 1,229 commits ahead and 235 behind its recorded `origin/main`, with local modifications to multiple documentation files. It is therefore not treated as the latest eligible v2 source or a clean controlled instance.
- A direct `git ls-remote origin refs/heads/main` check still returned `fe222446c83a4034bfa37ac5a493d6a30b9abe74`, matching the anonymous GitHub observation above. No files or state in the v2 workspace were changed.
- No v2 runtime, model, configuration, or matched task was exercised. This remains source-only evidence; neither the local diverged checkout nor the upstream source observation establishes current owner-facing behavior.

## Living-control source recheck — 2026-10-11, family 1 checkpoint

- A fresh read-only `git ls-remote` and anonymous pinned-file fetch again identified upstream `main` at `fe222446c83a4034bfa37ac5a493d6a30b9abe74`; no newer public source revision was observed.
- The current `CAMPAIGN_STATE.md` calls for a Core Usability Reset after a newly reported household routing failure, including a read-style prompt reaching memory mutation. It explicitly says reproduction and repair are not claimed. This is a public source-record observation of an owner-reported issue, not an independent reproduction or proof that it remains in current runtime behavior.
- The pinned owner-workflow scoreboard contains current workflow statuses and synthetic/canonical verification notes, while the pinned blocker record says fresh authenticated owner acceptance and exact production source/runtime parity remain unverified for the homelab slice. These files do not provide a matched model/hardware/configuration comparison with the v3 fixtures.
- No current v2 runtime, production service, user data, credentials, branch, or working-tree content was changed or exercised. HADES v2 remains an independently active living control. No owner-acceptance ranking is available.

Primary source snapshots: [campaign state at the observed SHA](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/CAMPAIGN_STATE.md), [workflow scoreboard](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/acceptance/owner-workflows.md), and [blocker record](https://github.com/p0rkm4th/hades/blob/fe222446c83a4034bfa37ac5a493d6a30b9abe74/docs/current-blockers.md).

## Living-control source recheck — 2026-10-11, GPU discovery checkpoint

- A fresh `git ls-remote` read returned public `main` tip `63b62a594b1a57e66dd9f59f9efe50c4ef9a4538`. At that pinned tip, [`CAMPAIGN_STATE.md`](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/CAMPAIGN_STATE.md) and [`docs/current-blockers.md`](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/docs/current-blockers.md) identify code-bearing `main` as `99d8b706eb5263250400f55dc257ba43f191905d`, with exact-source Public CI reported as passed.
- The current campaign record says the Core Usability Reset is investigating an owner-reported routing failure: read-style household inventory or infrastructure questions were routed incorrectly, and one inventory phrasing reached a memory mutation path. The record explicitly says this is not independently reproduced and no repair is claimed. Its immediate next step is a focused owner-routing branch and reproduction across production behavior, canonical source, and historical evidence.
- The public owner-workflow scoreboard reports PASS + PERSISTENCE for several integrated slices. That broad status does not establish resolution of the newly reported routing failure or exact production/source parity.
- No HADES v2 chat/agent request, checkout, credentials, or user data was accessed. The GPU probes described in [COMPARISON_REPORT.md](COMPARISON_REPORT.md) were direct inference requests to an existing model-serving service used by the homelab; they were outside the HADES chat/agent application path and briefly consumed that service. No service restart or configuration change occurred. A later read-only check found an active client connection of unknown ownership, so no additional inference requests were made.
- This is a moving source-only living-control observation, not a matched outcome, current runtime acceptance, or owner evaluation. The earlier `fe222446…` checkpoint above remains a historical observation and is not the current tip.

Pinned current source snapshots: [campaign state](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/CAMPAIGN_STATE.md), [owner-workflow scoreboard](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/acceptance/owner-workflows.md), and [current blockers](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/docs/current-blockers.md).

## Living-control source recheck — 2026-10-11, family 3 checkpoint

- An anonymous GitHub API request and a fresh `git ls-remote` both returned public v2 `main` tip `63b62a594b1a57e66dd9f59f9efe50c4ef9a4538`. The pinned campaign state identifies code-bearing `main` as `99d8b706eb5263250400f55dc257ba43f191905d` and reports exact-SHA Public CI run `38162158388` passed.
- The current campaign record marks Open WebUI P0 closed and summarizes exact-artifact DOCX cross-user acceptance, owner-data preservation, fresh backup/recovery, restart persistence, revocation contracts, canonical convergence, and post-promotion CI as passed. It separately keeps the Core Usability Reset open for an owner-reported kitchen/ingredient-typo/network routing failure, including read-style inventory or infrastructure questions reaching the wrong route and a reported memory-mutation path. The public campaign explicitly does not claim reproduction or repair.
- Current public blocker records describe homelab read reliability as partial and exact deployed byte parity as unverified. Public source and acceptance summaries provide useful evidence of continuing v2 work, but no matched v2 runtime/model/configuration comparison was performed for this v3 checkpoint. The historical owner report is not proof the issue remains in current runtime behavior.
- No HADES v2 service, user data, credentials, workspace, source branch, or runtime workload was accessed or modified. HADES v2 remains an independent, actively developing control.

Pinned latest source snapshots: [campaign state](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/CAMPAIGN_STATE.md), [owner-workflow scoreboard](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/acceptance/owner-workflows.md), and [current blockers](https://github.com/p0rkm4th/hades/blob/63b62a594b1a57e66dd9f59f9efe50c4ef9a4538/docs/current-blockers.md).


## Living-control source recheck — 2026-10-12, HADES v3 checkpoint 28

- An unauthenticated GitHub API request and HTTPS `git ls-remote` both returned public v2 `main` at `8b45404575c3efc1aeb1e9a9f9245b9b029e53ee` (commit time `2026-10-12T05:00:27Z`). This is newer than the prior observed `63b62a594b1a57e66dd9f59f9efe50c4ef9a4538` source snapshot.
- The exact commit changes `hermes/sitecustomize.py` and `scripts/test-coding-worker-hermes-runtime.sh`. Its source wraps `asyncio` executor submission to copy request `ContextVars` for chat-bound work; the test exercises concurrent chat IDs through `run_in_executor`. This is source-level evidence of a request-context propagation fix, not evidence of deployed behavior or owner acceptance.
- Public Actions lists two runs for the exact SHA: run [`38206117325`](https://github.com/p0rkm4th/hades/actions/runs/38206117325) concluded success; later run [`38206254049`](https://github.com/p0rkm4th/hades/actions/runs/38206254049) concluded failure at `Check public history`. No conclusion is drawn about the runtime patch from these differing CI outcomes; the latest run's failed repository-history gate is recorded as such.
- The current public `CAMPAIGN_STATE.md` and `docs/current-blockers.md` still describe the Core Usability Reset as open for owner-reported read-routing and memory-mutation failures, with reproduction and repair not claimed. The current source update does not establish that this issue was addressed. No v2 runtime, production service, user data, or branch was accessed or changed; no matched task was run.

Pinned current source snapshots: [request-context implementation](https://github.com/p0rkm4th/hades/blob/8b45404575c3efc1aeb1e9a9f9245b9b029e53ee/hermes/sitecustomize.py), [runtime test](https://github.com/p0rkm4th/hades/blob/8b45404575c3efc1aeb1e9a9f9245b9b029e53ee/scripts/test-coding-worker-hermes-runtime.sh), [campaign state](https://github.com/p0rkm4th/hades/blob/8b45404575c3efc1aeb1e9a9f9245b9b029e53ee/CAMPAIGN_STATE.md), and [current blockers](https://github.com/p0rkm4th/hades/blob/8b45404575c3efc1aeb1e9a9f9245b9b029e53ee/docs/current-blockers.md).

## Living-control source recheck — 2026-10-12, HADES v3 checkpoint 30

- Anonymous GitHub API and HTTPS `git ls-remote` both returned public v2 `main` at `0cca0c8bbfa770b02adcd8c75f48a8ab88a8b3e9` (commit time `2026-10-12T05:48:20Z`), advancing beyond the prior `8b45404575c3efc1aeb1e9a9f9245b9b029e53ee` recheck.
- The commit adds `hermes/coding_evidence_store.py`, its contract tests, and worker integration. It stores a bounded, permission-restricted receipt outside the worker-writable repository, bound to the authenticated subject/session and recent timestamp. On a later task within that session, the worker can reuse passing test evidence only if the same branch, pre-commit HEAD, exact changed paths, and source fingerprint still match; a commit or subsequent test attempt clears the receipt. This addresses test-evidence continuity across Hermes task IDs at the source-contract level.
- Exact-SHA Public CI run [`38209585326`](https://github.com/p0rkm4th/hades/actions/runs/38209585326) passed. Its public job log shows the new cross-turn evidence-store check and the existing workspace, routing, relay, adapter, and UI checks completed successfully. The run has no uploaded artifacts. A targeted log scan found no credential patterns, private IPv4, or local-account markers.
- The current public `CAMPAIGN_STATE.md` and `docs/current-blockers.md` still carry the October 11 mission checkpoint: the Core Usability Reset remains open for owner-reported read-routing and memory-mutation failures, with reproduction and repair not claimed. The new coding-evidence receipt is a separate source-level improvement; it does not establish current owner-facing correctness or deployed behavior. No v2 runtime, production service, user data, or branch was accessed or changed.

Pinned current source snapshots: [evidence store](https://github.com/p0rkm4th/hades/blob/0cca0c8bbfa770b02adcd8c75f48a8ab88a8b3e9/hermes/coding_evidence_store.py), [coding worker integration](https://github.com/p0rkm4th/hades/blob/0cca0c8bbfa770b02adcd8c75f48a8ab88a8b3e9/hermes/coding_worker.py), [workspace contract](https://github.com/p0rkm4th/hades/blob/0cca0c8bbfa770b02adcd8c75f48a8ab88a8b3e9/hermes/workspace_contract.py), and [evidence-store tests](https://github.com/p0rkm4th/hades/blob/0cca0c8bbfa770b02adcd8c75f48a8ab88a8b3e9/scripts/test-coding-evidence-store.py).

## Living-control source recheck — 2026-10-12, family 6 pilot

- Anonymous GitHub API and HTTPS `git ls-remote` both returned public v2 `main` at `3df7bfb886bfcb891aab7d770be09139329b6ccd` (committer time `2026-10-12T06:45:12Z`). Exact-SHA Public CI run [`38214947338`](https://github.com/p0rkm4th/hades/actions/runs/38214947338) completed successfully.
- The current code-bearing `main` includes a change accepting HADES-bound Hermes worker results when an optional turn ID is absent. This is source and CI evidence of adapter compatibility progress, not an end-to-end v2 restart-recovery result.
- The current campaign and blocker documents still carry an October 11 checkpoint. They continue to describe read-style household inventory/infrastructure routing, including a reported inventory-to-memory-mutation route, as owner-reported and not independently reproduced. The homelab read slice remains partial. The acceptance scoreboard has no newer owner judgment for this routing issue. No v2 runtime, workload, production data, branch, or deployment was accessed.
- This is source-only living-control evidence. It is not a matched comparison to the v3 family 6 pilot and does not establish owner usability, current deployment parity, or resolution of the reported routing issue.

Pinned current source snapshots: [Hermes coding-worker integration](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/hermes/coding_worker.py), [focused routing tests](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/scripts/test-coding-worker-routing.py), [campaign state](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/CAMPAIGN_STATE.md), [current blockers](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/docs/current-blockers.md), and [owner-workflow scoreboard](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/acceptance/owner-workflows.md).

## Living-control source recheck — 2026-10-12, HADES v3 checkpoint 45

- Anonymous GitHub API and HTTPS `git ls-remote` again returned public v2 `main` at `3df7bfb886bfcb891aab7d770be09139329b6ccd` (committer time `2026-10-12T06:45:12Z`), unchanged from the previous living-control check. Exact-SHA Public CI run [`38214947338`](https://github.com/p0rkm4th/hades/actions/runs/38214947338) remains successful.
- Read the pinned `CAMPAIGN_STATE.md`, `docs/current-blockers.md`, and `acceptance/owner-workflows.md`. The Core Usability Reset is still open for the owner-reported read-routing and memory-mutation path; reproduction and repair are not claimed. The current next step is a truth-only P0 change passing hosted CI, followed by a focused owner-routing branch. The scoreboard records passes for other staging slices, not new owner acceptance for this routing issue.
- No v2 runtime, production service, branch, user data, credentials, or deployment was accessed or changed. This is a source and acceptance-record observation and not a matched result for the v3 family 2 task.

Pinned current source records: [campaign state](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/CAMPAIGN_STATE.md), [current blockers](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/docs/current-blockers.md), and [owner-workflow scoreboard](https://github.com/p0rkm4th/hades/blob/3df7bfb886bfcb891aab7d770be09139329b6ccd/acceptance/owner-workflows.md).

## Living-control source recheck — 2026-10-12, HADES v3 checkpoints 48–49

- Anonymous GitHub `git ls-remote` still returns public v2 `main` at `3df7bfb886bfcb891aab7d770be09139329b6ccd`. The exact-SHA Public CI runs 38214947338 and 38214081660 both report success.
- Read the campaign state, current blockers, and owner-workflow scoreboard pinned to that source tip. The Open WebUI P0 acceptance remains closed; the separate owner-reported read-routing/memory-mutation mission remains open and unreproduced in the public record. No new owner acceptance for this routing case is recorded.
- No v2 runtime, production service, workload, branch, user data, credential, or deployment was accessed or changed. This is source/acceptance-record observation only and is not a matched v2 task comparison.

## Living-control source recheck — 2026-10-12, HADES v3 checkpoints 50–51

- Anonymous `git ls-remote` again returned public v2 `main` at `3df7bfb886bfcb891aab7d770be09139329b6ccd`; exact-SHA Public CI runs 38214947338 and 38214081660 remain successful.
- The pinned campaign state and current blockers continue to describe the owner-reported read-routing/memory-mutation failure as open and not independently reproduced; the public owner-workflow scoreboard has no new acceptance result for that route. The Open WebUI P0 remains separately recorded as closed.
- The family 6 v3 runs are synthetic and local; they are not matched against v2. No v2 runtime, service, workload, user data, branch, deployment, or credentials were accessed or modified.

## Living-control source recheck — 2026-10-12, HADES v3 checkpoint 46

- Anonymous `git ls-remote` returned public v2 `main` at `3df7bfb886bfcb891aab7d770be09139329b6ccd`; the pinned campaign state, current-blocker record, and owner-workflow scoreboard were read at that exact revision.
- The owner-reported read-routing/memory-mutation mission remains open; source records do not claim reproduction or repair. No new owner acceptance for that route was recorded. The next recorded action remains a truth-only P0 change with hosted CI, followed by the focused owner-routing branch.
- This is source/acceptance-record observation only. No v2 runtime, workload, user data, branch, deployment, or service was accessed or modified, and no matched v2 family 2 task was run.

## Living-control source recheck — 2026-10-12, HADES v3 checkpoints 52–55

- Anonymous public GitHub API now reports v2 `main` at `9edf77b79f1054a0c779abdca3510790db2729ed`. Its parent `2c7715ce6632ea45baf4e0756d0368645c523589` is “Prove coding failure recovery and ambiguous commit state.” The 2c changes cover Hermes coding-worker commit-intent detection and canonical workspace verification after lost or ambiguous commit responses. Added tests cover negated commit language, unchanged HEAD, changed source during an ambiguous operation, and exact commit-path verification. The latest 9edf commit adjusts one tested-source mismatch assertion.
- Exact-SHA Public CI runs [38256761322](https://github.com/p0rkm4th/hades/actions/runs/38256761322) passed on 2c; runs [38258273019](https://github.com/p0rkm4th/hades/actions/runs/38258273019) and [38257920711](https://github.com/p0rkm4th/hades/actions/runs/38257920711) passed on 9edf. These results show public source/contract-test evidence. They do not show that the change is deployed, accepted by the owner, or successful in a matched v3 interruption trial.
- The latest campaign and blocker documents at the current branch still contain an October 11 checkpoint naming `99d8b706...` as `main`; they have not yet incorporated the October 12 code-only commits. Their owner-tracking state remains: Open WebUI P0 is closed; the separate owner-reported read-style inventory/infrastructure routing and memory-mutation issue is open, not independently reproduced, and not claimed fixed. The owner-workflow scoreboard documents passing slices in other domains but no new acceptance for that routing case.
- v3 CP50–54 work remains local synthetic evidence and is not a matched runtime comparison against v2. The only owner-facing acceptance evidence available in this comparison is recorded for v2; v3 owner usability has not been evaluated. Therefore there is no controlled basis to say v3 handles ordinary owner work better. Continue v2 as the living control and do not interrupt its active lane. No v2 runtime, service, workload, user data, branch, deployment, or credentials were accessed or modified.

## Living-control source recheck — 2026-10-12, HADES v3 checkpoint 58

- Anonymous GitHub API confirmed public v2 `main`; HTTPS `git ls-remote` independently returned `8be6ccba0c1d5009581e0e4ad5b1fc180fd2ebf1` (commit message: “Recognize conditional commit requests and trace isolated turns”). This advances beyond the prior checkpoint's `9edf77b79f1054a0c779abdca3510790db2729ed` observation.
- The new source change expands coding-worker commit-intent recognition for conditional “commit only … once/after/when/if” language, passes the opt-in diagnostics flag through private task configuration, and records aggregate model-request count/durations/failures without logging request bodies. The regression test adds positive and interrogative-negative examples. This is source and test-contract evidence; it does not establish owner-facing acceptance or deployed behavior.
- Exact-SHA Public CI runs [38269741284](https://github.com/p0rkm4th/hades/actions/runs/38269741284) and [38269114341](https://github.com/p0rkm4th/hades/actions/runs/38269114341) both concluded success. These are public automated checks, not a matched HADES v3 task result.
- Current public `CAMPAIGN_STATE.md` and `docs/current-blockers.md` still show an October 11 mission checkpoint: the owner-reported read-routing/memory-mutation issue remains open and is not claimed fixed. The owner-workflow scoreboard contains other passing slices, but no new acceptance entry for the read-routing case. These status documents name an older main SHA than the current code tip, so the new code commit should not be read as resolving that open mission.
- No v2 runtime, production service, workload, branch, user data, deployment, or credential was accessed or changed. This is a read-only source/acceptance-record observation. Checkpoint 58's family 3 CPU diagnostic timed out before a tool call on both profiles and is not a matched v2 comparison.

Pinned public records: [current source commit](https://github.com/p0rkm4th/hades/commit/8be6ccba0c1d5009581e0e4ad5b1fc180fd2ebf1), [campaign state](https://github.com/p0rkm4th/hades/blob/8be6ccba0c1d5009581e0e4ad5b1fc180fd2ebf1/CAMPAIGN_STATE.md), [current blockers](https://github.com/p0rkm4th/hades/blob/8be6ccba0c1d5009581e0e4ad5b1fc180fd2ebf1/docs/current-blockers.md), and [owner-workflow scoreboard](https://github.com/p0rkm4th/hades/blob/8be6ccba0c1d5009581e0e4ad5b1fc180fd2ebf1/acceptance/owner-workflows.md).

## Living-control source recheck — 2026-10-12, HADES v3 checkpoint 62

- HTTPS `git ls-remote` still reports public v2 `main` at `8be6ccba0c1d5009581e0e4ad5b1fc180fd2ebf1`; no newer public source or acceptance evidence was observed in this read-only check.
- The prior pinned campaign, blocker, and owner-workflow records still leave the owner-reported read-routing/memory-mutation issue open and unreproduced. This source-only recheck is not matched to CP62's synthetic family 2 task and establishes no v2 runtime behavior or ordinary-work ranking.
- No v2 runtime, service, workload, production data, branch, deployment, or credential was accessed or changed.

## Living-control source recheck — 2026-10-12, HADES v3 checkpoint 61

- A new HTTPS `git ls-remote` read still returns public v2 `main` at `8be6ccba0c1d5009581e0e4ad5b1fc180fd2ebf1`. I fetched `CAMPAIGN_STATE.md`, `docs/current-blockers.md`, and `acceptance/owner-workflows.md` pinned to that exact revision.
- The campaign and blocker records remain dated October 11 and identify code-bearing `main` as `99d8b706eb5263250400f55dc257ba43f191905d`, an older source SHA. They keep the owner-reported read-style inventory/infrastructure routing and memory-mutation issue open; reproduction and repair are not claimed. The owner-workflow scoreboard records PASS + PERSISTENCE for several workflows, including conversation, memory, operator, and household slices, but no acceptance specifically resolves that routing issue.
- This source and published-acceptance review does not prove current deployed behavior, source/runtime parity, or current owner acceptance. There is no controlled v2 result matched to CP61's Qwen3-8B endpoint, fixture, prompt, and configuration; no ordinary-work superiority claim is warranted. No v2 runtime, service, production data, branch, deployment, or credential was accessed or changed.
