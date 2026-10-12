# Current state

**Campaign status:** in progress; ADR-010 remains NOT READY. The project is a prototype comparison, not a production HADES v3 implementation.

## Current checkpoint

- Shared lab: PostgreSQL/Grocy, scoped gateway, synthetic commitment simulator, isolated Amber/Cobalt shell/Git workspaces, local Qwen inference, and a Playwright-compatible chat UI are present in the Compose experiment.
- Candidate C (lean) and A (Pydantic AI) each completed one live read-only kitchen integration smoke probe under the same CPU Qwen3-8B endpoint. Both returned the seeded values and called only `inventory_read`. Their task IDs, token counts, timings, and verification limits are recorded in [COMPARISON_REPORT.md](COMPARISON_REPORT.md). These are not controlled trials.
- Candidate B (reduced Hermes) starts its pinned Hermes gateway, and authenticated `/health` and `/v1/models` requests return HTTP 200. Its kitchen request fails before tool execution because the verified shared model context is 40,960 tokens and Hermes enforces a 64,000-token floor. Qwen3-8B reports both `n_ctx` and `n_ctx_train` as 40,960; do not advertise or configure it as a 64K model. The selected local model and runtime profile are documented in [MODEL_PROFILE.md](MODEL_PROFILE.md).
- The Playwright UI smoke test passed after confirming the three candidate options, visible metrics, and hidden task identity. This uses a mocked `/api/turn`; it is not owner acceptance or an end-to-end candidate UI evaluation.
- SQL read-back confirmed the A/C task owners, goals, `RUNNING` states, and zero effect rows. Their states were not advanced to `COMPLETED`. A pre-probe memory count was not recorded, so memory non-mutation is not claimed as independently verified.
- No three-trial scenario, full eight-family screen, restart-kill test, stronger-model comparison, maintenance exercise, independent owner judgment, or 20-family historical qualification has been completed.

## Living v2 control

- Latest eligible public HADES v2 `main` source remains `fe222446c83a4034bfa37ac5a493d6a30b9abe74`; a direct upstream `git ls-remote` check on 2026-10-11 returned the same SHA as the recorded baseline.
- The local HADES workspace remains at `6a46e18657b17c261a5725de3b0d09b24e7d3f60`, 1,229 commits ahead and 235 behind upstream, with local changes. It was inspected read-only and is not treated as an eligible current control.
- No current v2 runtime was exercised. This remains a source-only observation, not a controlled comparison or owner acceptance result. See [V2_CONTROL_BASELINE.md](V2_CONTROL_BASELINE.md).

## Public checkpoint

- Repository: [`https://github.com/p0rkm4th/hades-v3`](https://github.com/p0rkm4th/hades-v3), branch `main`.
- Last remotely verified SHA before this candidate checkpoint: `c87cb0a5b571864614ea591ff47ed354b0918175`.
- Candidate adapters/UI/runtime changes are committed locally as `d2bb5b0` but not pushed yet. The findings document has a follow-up edit with exact post-commit A/C probe IDs and measurements; that documentation edit is not committed.
- SSH authentication succeeds as `p0rkm4th`; no owner action is needed. After the final documentation update, rescan the working tree and full history, review the staged paths, push without force, then verify `git ls-remote` and anonymous GitHub API/raw access. Record the resulting published code SHA here.
- Frozen authority documents and local instruction files remain excluded from the public repository by `.gitignore`; they were not changed. No memorial content is in the public worktree.

## Next engineering actions

1. Preserve the honest Hermes/Qwen compatibility result. Do not bypass the 64K check or misreport the endpoint's actual context. Decide within the existing campaign scope whether an eligible, locally runnable model with a measured context of at least 64K can be added as a common profile; otherwise record Hermes as ineligible for the selected model configuration and continue the eight-family screen with A/C.
2. Complete independently verified A/C trials for all eight scenario families with consistent resets, held-out wording, exact model/runtime identity, and latency/tool/token capture. Fix or investigate task lifecycle state before interpreting completion outcomes.
3. Recheck the living v2 source and available acceptance evidence at the next comparison checkpoint; collect no production runtime data or owner data.
4. Run Gitleaks on the proposed checkout and full history, perform manual publication review, commit the evidence update, push both sanitized commits, and verify anonymous access and the exact remote SHA.

No owner action is currently required for GitHub access or repository visibility. Full production implementation remains out of scope.
