# Current state

- Experiment: setup only; no prototype trial has run.
- Candidate decision: ADR-010 NOT READY; no comparative evidence.
- HADES v2 source snapshot: `fe222446c83a4034bfa37ac5a493d6a30b9abe74` on public `main`; see [baseline evidence and limits](V2_CONTROL_BASELINE.md).
- Public repository target: `https://github.com/p0rkm4th/hades-v3`.
- Publication: not yet initialized remotely. Anonymous API lookup returned HTTP 404; the name is available at this observation but ownership/creation is not established.
- Local repository: initialized on `main`; initial commit `2d0488caddde45210a704a332329783176f45476`. The public-safe initial commit has passed a local Gitleaks scan and contains no prior exposed history.
- Public repository: not yet created. `gh` is unavailable, and no authenticated GitHub write method is configured in this environment. The API returned 404 for the target at the latest check.
- Publication review: the local frozen specifications, kickoff brief, addendum, and memorial path are excluded from the public commit. The proposed public files were manually checked for private workspace paths, memorial references, personal identifiers, and private network addresses; Gitleaks reported no findings.
- Next actions: owner authenticates through `gh auth login` (without sharing a token) or provides another authenticated GitHub transport; create `p0rkm4th/hades-v3` as public; push the audited branch; verify unauthenticated access and the remote SHA; then build the shared disposable environment and three smallest viable adapters.

No tests or comparison trials have been run at this checkpoint.
