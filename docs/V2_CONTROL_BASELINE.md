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
