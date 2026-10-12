# Current state

**Campaign status:** in progress; ADR-010 remains NOT READY. The project is a prototype comparison, not a production HADES v3 implementation.

## Current checkpoint

- Shared lab: PostgreSQL/Grocy, scoped gateway, synthetic commitment simulator, isolated Amber/Cobalt shell/Git workspaces, local Qwen inference, and a Playwright-compatible chat UI are present in the Compose experiment.
- A and C each completed the repeated family 1 screen (9 calls per candidate), plus two repeated family 2 trajectories. Trajectory 1 succeeded 3/3 each on Qwen3-8B. For trajectory 2, both candidates failed safely 3/3 before canonical-name guidance; after the shared guidance update, both made the same partial change in 3/3 8B attempts, omitting Pasta while returning a completion-style update. SQL and operator list reads verified the omission. On Qwen3-14B, both candidates completed that trajectory 3/3 with exact task/effect linkage and independently checked state. Exact IDs, tokens, durations, model conditions and limits are in [COMPARISON_REPORT.md](COMPARISON_REPORT.md). This is evidence from portions of families 1 and 2, not full qualification or a ranking.
- A homelab discovery verified healthy NVIDIA drivers on the laptop and three reachable inference hosts. A Qwen3.6 35B Q4_K_M Ollama endpoint reported a loaded effective context of 65,536, and four bounded generations produced 27.65–37.60 tokens/s with GPU utilization observed during generation. That context meets Hermes's 64,000-token floor. The A/C/B Compose operator network is intentionally internal and cannot reach the endpoint, so candidate comparisons remain on the identical local Qwen3-8B CPU profile. No host service, driver, or configuration was changed; four direct diagnostic generations briefly used the existing inference endpoint, outside the HADES v2 chat/agent path. Full profile and limits: [MODEL_PROFILE.md](MODEL_PROFILE.md).
- Candidate B (reduced Hermes) starts its pinned Hermes gateway, and authenticated `/health` and `/v1/models` requests return HTTP 200. Its candidate request fails before tool execution on the prepared 40,960-token CPU profiles. The discovered 65,536-token GPU endpoint has not yet been tested through Candidate B because it is unreachable from the isolated experiment network; no context metadata was overridden.
- One private wording attempt per candidate on Qwen3-8B stalled before any tool call. Candidate C returned HTTP 502 after five minutes; Candidate A was operator-cancelled after six minutes. The shopping list stayed at its seed in both runs. The API left both tasks `RUNNING`; an operator marked them `FAILED` after confirming there was no effect. This is an incomplete one-attempt matched diagnostic, not comparative evidence.
- The Playwright UI smoke test passed after confirming the three candidate options, visible metrics, and hidden task identity. This uses a mocked `/api/turn`; it is not owner acceptance or an end-to-end candidate UI evaluation.
- Initial family 1 attempts before the wrapper fix left tasks `RUNNING` and were excluded. Candidate API commit `1335470a79fb54f4f4ebcef36011270489f6f993` preserves explicit task checkpoints and completes successful turns that remain `RUNNING`; the subsequent 18 trials verified this lifecycle. Earlier kitchen smoke probes had no pre-probe memory count, so their memory non-mutation is not independently claimed.
- Further family 2 variations, a safe isolated route to reuse the GPU endpoint, families 3–8, deliberate restart-kill recovery, maintenance exercises, independent owner judgment, and the full 20-family historical qualification remain incomplete.

## Living v2 control

- Latest public HADES v2 `main` tip is `63b62a594b1a57e66dd9f59f9efe50c4ef9a4538`. Its current campaign state identifies code-bearing `main` as `99d8b706eb5263250400f55dc257ba43f191905d` and reports that exact-code CI passed.
- The local HADES workspace remains at `6a46e18657b17c261a5725de3b0d09b24e7d3f60`, 1,229 commits ahead and 235 behind upstream, with local changes. It was inspected read-only and is not treated as an eligible current control.
- The latest public campaign record reports an owner-reported read-routing failure, including a read-style question reaching memory mutation; reproduction and repair are explicitly not claimed there. No matched v2 chat/agent trial was performed; the direct model-endpoint probes recorded above were outside that application path. The final endpoint check showed an active client of unknown ownership, so no additional inference requests were sent. This remains source-only evidence and not a matched comparison or owner acceptance result. Details are in [V2_CONTROL_BASELINE.md](V2_CONTROL_BASELINE.md).

## Public checkpoint

- Repository: [`https://github.com/p0rkm4th/hades-v3`](https://github.com/p0rkm4th/hades-v3), branch `main`.
- Latest published evidence checkpoint: `8e4b60f880208c6e92704fe83609486b5e581398` on `main`, including sanitized GPU discovery and the matched one-attempt timeout diagnostic; it builds on source commit `4f9d6c4cab0816d4172870ba2f44b852ca783bae`. This checkpoint was pushed over SSH.
- Post-push verification returned the same SHA from `git ls-remote`; an unauthenticated GitHub API request reported `private=false`, visibility `public`, and default branch `main`. Anonymous raw access returned the new `MODEL_PROFILE.md`. Staged and full-history Gitleaks scans found no leaks; the history scan covered 20 commits.
- Changes include candidate A/C adapters, an early B Hermes runtime integration, the synthetic chat UI and one Playwright UI smoke test. Candidate B remains blocked on the configured CPU profiles' verified 40,960-versus-64,000 mismatch; the 65,536 GPU profile is not reachable from candidate containers yet. ADR-010 remains NOT READY.
- The repository is public and SSH authentication is available. Reverify visibility, anonymous access, and exact remote SHA after each later checkpoint.
- Frozen authority documents and local instruction files remain excluded from the public repository by `.gitignore`; they were not changed. No memorial content is in the public worktree.

## Next engineering actions

1. Keep A/C/B comparisons on identical endpoint settings. Preserve the verified 65,536 GPU context value; do not raise or rewrite metadata. Design a bounded, isolated route for candidate containers to the existing endpoint before using it. Until that route is reviewed, keep CPU comparisons as the fallback.
2. Complete repeated family 2 work with fresh private wordings and per-attempt resets; include the new timeout and task error-path finding. Then exercise stale and unavailable infrastructure in family 3. Keep exact task/effect postcondition verification, including omissions.
3. Recheck the living v2 source and available acceptance evidence at the next comparison checkpoint; collect no production runtime data or owner data.
4. Run Gitleaks on the proposed checkout and full history, perform manual publication review, commit the evidence update, push both sanitized commits, and verify anonymous access and the exact remote SHA.

No owner action is currently required for GitHub access or repository visibility. Full production implementation remains out of scope.
