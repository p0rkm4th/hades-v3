# Current state

- Experiment: setup only; no prototype trial has run.
- Candidate decision: ADR-010 NOT READY; no comparative evidence.
- HADES v2 source snapshot: `fe222446c83a4034bfa37ac5a493d6a30b9abe74` on public `main`; see [baseline evidence and limits](V2_CONTROL_BASELINE.md).
- Public repository target: `https://github.com/p0rkm4th/hades-v3`.
- Publication: not yet initialized remotely. Anonymous API lookup returned HTTP 404; this does not distinguish an absent repository from a private repository, so ownership and availability are unverified.
- Local repository: initialized on `main`; initial commit `2d0488caddde45210a704a332329783176f45476`. The public-safe initial commit has passed a local Gitleaks scan and contains no prior exposed history.
- Local tooling: Docker Engine `29.8.2` responds to `docker info`; Python `3.14.7`, Node.js `v26.11.1`, and npm `12.2.0` are available.
- Public repository: not yet published. `gh` is unavailable, and no authenticated GitHub write method is configured in this environment. The anonymous API returned 404; this does not distinguish an absent repository from an existing private repository, so the target must be checked while authenticated before creation.
- Publication review: the local frozen specifications, kickoff brief, addendum, and memorial path are excluded from the public commit. The proposed public files were manually checked for private workspace paths, memorial references, personal identifiers, and private network addresses; Gitleaks reported no findings.
- Owner action required for publication: install GitHub CLI if needed and run `gh auth login` locally using the account that owns or administers `p0rkm4th`. Do not paste a token into chat. Then tell Codex when authentication is complete. Check the authenticated account and repository; if the target is absent and available, create it as public, otherwise use only the correct owner-controlled repository. Push the audited branch and verify anonymous access and remote SHA. Prototype work can continue locally meanwhile.

No tests or comparison trials have been run at this checkpoint.
