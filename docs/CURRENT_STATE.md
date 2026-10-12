# Current state

**Campaign status:** in progress; ADR-010 remains NOT READY. The project is a prototype comparison, not a production HADES v3 implementation.

## Current checkpoint

- Shared lab: PostgreSQL/Grocy, scoped gateway, synthetic commitment simulator, isolated Amber/Cobalt shell/Git workspaces, local Qwen inference, and a Playwright-compatible chat UI are present in the Compose experiment.
- Candidate C (lean) and A (Pydantic AI) each completed one live read-only kitchen integration smoke probe, one valid compound shopping-list smoke, and the first repeated family 1 screen: three attempts each for three inventory wordings (9 calls per candidate) under the same CPU Qwen3-8B endpoint. All 18 family 1 responses matched the fixture, used only `inventory_read`, and reached `COMPLETED`; SQL showed zero linked effects, memory count stayed at one, and an operator-side Grocy read matched the expected quantities. Exact outputs, task IDs, tokens, timing and limitations are in [COMPARISON_REPORT.md](COMPARISON_REPORT.md). This is one family, not full qualification or a candidate ranking.
- Candidate B (reduced Hermes) starts its pinned Hermes gateway, and authenticated `/health` and `/v1/models` requests return HTTP 200. Its kitchen request fails before tool execution because the verified shared model context is 40,960 tokens and Hermes enforces a 64,000-token floor. Qwen3-8B reports both `n_ctx` and `n_ctx_train` as 40,960; do not advertise or configure it as a 64K model. The selected local model and runtime profile are documented in [MODEL_PROFILE.md](MODEL_PROFILE.md).
- The Playwright UI smoke test passed after confirming the three candidate options, visible metrics, and hidden task identity. This uses a mocked `/api/turn`; it is not owner acceptance or an end-to-end candidate UI evaluation.
- Initial family 1 attempts before the wrapper fix left tasks `RUNNING` and were excluded. Candidate API commit `1335470a79fb54f4f4ebcef36011270489f6f993` preserves explicit task checkpoints and completes successful turns that remain `RUNNING`; the subsequent 18 trials verified this lifecycle. Earlier kitchen smoke probes had no pre-probe memory count, so their memory non-mutation is not independently claimed.
- Families 2–8, deliberate restart-kill recovery, stronger-model comparison, maintenance exercises, independent owner judgment, and the full 20-family historical qualification remain incomplete.

## Living v2 control

- Latest eligible public HADES v2 `main` source remains `fe222446c83a4034bfa37ac5a493d6a30b9abe74`; a direct upstream `git ls-remote` check on 2026-10-11 returned the same SHA as the recorded baseline.
- The local HADES workspace remains at `6a46e18657b17c261a5725de3b0d09b24e7d3f60`, 1,229 commits ahead and 235 behind upstream, with local changes. It was inspected read-only and is not treated as an eligible current control.
- Upstream `main` was rechecked read-only and remains at `fe222446c83a4034bfa37ac5a493d6a30b9abe74`. Its current public campaign record reports a newly surfaced owner routing failure, including a read-style question reaching memory mutation; reproduction and repair are explicitly not claimed there. No v2 runtime was exercised, so this remains a source-only observation and not a matched comparison or owner acceptance result. Details are in [V2_CONTROL_BASELINE.md](V2_CONTROL_BASELINE.md).

## Public checkpoint

- Repository: [`https://github.com/p0rkm4th/hades-v3`](https://github.com/p0rkm4th/hades-v3), branch `main`.
- Published family 1 code/evidence checkpoint: `6c37bcf0b2e197c912e023353564dc01f631760b` on `main`, including candidate lifecycle source `1335470a79fb54f4f4ebcef36011270489f6f993`. SSH push succeeded; `git ls-remote` returned the exact checkpoint SHA. Unauthenticated GitHub API returned `visibility=public`, `default_branch=main`, and an unauthenticated raw fetch returned the family 1 findings. The full 16-commit history and staged changes passed Gitleaks. This current-state sync follows the evidence commit.
- Anonymous GitHub API verification returned `private=false`, default branch `main`; anonymous raw access to `experiment/candidates/api.py` returned source containing `chat_hermes`. The full 12-commit Git history and new public source/docs passed Gitleaks with no findings.
- Changes include candidate A/C adapters, an early B Hermes runtime integration, the synthetic chat UI and one Playwright UI smoke test. Candidate B remains blocked by the verified 40,960-versus-64,000 context mismatch; ADR-010 remains NOT READY.
- No owner action is required for authentication or visibility. Continue synchronizing meaningful sanitized checkpoints and reverify the remote SHA and anonymous access after later pushes.
- Frozen authority documents and local instruction files remain excluded from the public repository by `.gitignore`; they were not changed. No memorial content is in the public worktree.

## Next engineering actions

1. Preserve the honest Hermes/Qwen compatibility result. Do not bypass the 64K check or misreport the endpoint's actual context. Decide within the existing campaign scope whether an eligible, locally runnable model with a measured context of at least 64K can be added as a common profile; otherwise record Hermes as ineligible for the selected model configuration and continue the eight-family screen with A/C.
2. Continue A/C repeated trials through family 2 (compound grocery changes), with independently restored seeds, retained candidate outputs, exact model/runtime identity, and independent postcondition reads.
3. Recheck the living v2 source and available acceptance evidence at the next comparison checkpoint; collect no production runtime data or owner data.
4. Run Gitleaks on the proposed checkout and full history, perform manual publication review, commit the evidence update, push both sanitized commits, and verify anonymous access and the exact remote SHA.

No owner action is currently required for GitHub access or repository visibility. Full production implementation remains out of scope.
