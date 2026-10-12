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
