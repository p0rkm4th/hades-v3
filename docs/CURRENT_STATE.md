# Current state

- Experiment: setup only; no prototype trial has run.
- Candidate decision: ADR-010 NOT READY; no comparative evidence.
- HADES v2 source snapshot: `fe222446c83a4034bfa37ac5a493d6a30b9abe74` on public `main`; see [baseline evidence and limits](V2_CONTROL_BASELINE.md).
- Public repository: [`https://github.com/p0rkm4th/hades-v3`](https://github.com/p0rkm4th/hades-v3), public, branch `main`.
- Publication verification: anonymous GitHub API returned HTTP 200 with `private=false`; anonymous raw README fetch succeeded. `git ls-remote` and anonymous API both reported `3508ad86857b01ca6cd47423914daaddee08ce44` after the initial push.
- Local initial project commit: `2d0488caddde45210a704a332329783176f45476`. The remote's preexisting one-line initializer commit `11abec1f63d3cd65aa8df3c99a8d227340138457` was preserved by merging unrelated histories; no force-push was used.
- Local repository: `main`; initial project content and complete combined history passed Gitleaks with no findings. The worktree was clean after the initial push.
- Local tooling: Docker Engine `29.8.2` responds to `docker info`; Python `3.14.7`, Node.js `v26.11.1`, and npm `12.2.0` are available.
- Public content review: local frozen specifications, project instructions, and owner-specific addenda remain excluded pending their own detailed content review. The published files were manually checked for private workspace paths, memorial references, personal identifiers, and private network addresses; Gitleaks reported no findings across the full merged history.
- Test status: no tests or comparison trials have run. Only repository publication and history-scanning checks are complete.
- Next actions: implement the shared disposable environment and three minimal candidate adapters, then run the controlled scenario families and continue versioned v2 observations. Recheck remote SHA and Gitleaks at each meaningful push.
