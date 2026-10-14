# CP86 — Pydantic provider retry accounting

**Date:** 2026-10-14  
**Scope:** Offline runtime inspection and candidate configuration correction; no model inference  
**Classification:** Pinned-runtime contract evidence, not candidate performance evidence

## Finding

CP85's matched A/C structured-memory screen stopped before either candidate selected a tool. The upstream model server recorded three canceled requests for A and one for C. CP85 did not capture per-request IDs, so it cannot establish request-by-request causality.

Inspection of the exact CP85 candidate image (`sha256:1052d8d2bd8f762460566a798f6026e2125771dddc516b605b2b5ebaf841bcc7`) found `pydantic-ai-slim==2.55.0` and `openai==3.29.0`. The OpenAI client's default `max_retries` is 2. A no-network, deterministic mock transport returned HTTP 500 on each attempt; the pinned SDK issued exactly three requests with the default and one request with `max_retries=0`. The Pydantic AI `Agent(retries=1)` option concerns tool/output validation and does not control these HTTP retries.

This reproduces the hidden retry behavior and strongly supports it as the explanation for CP85's 3:1 server cancellation count. The missing CP85 attempt IDs mean the historical mapping remains an inference, not direct trace proof. CP85 remains unchanged and unscored; no model request was repeated.

## Correction for future candidate revisions

Candidate A now constructs its OpenAI `AsyncOpenAI` client with `max_retries=0` and the configured request timeout, then passes that client to `OpenAIProvider`. This makes each Pydantic AI model request correspond to at most one provider transport attempt; any retry must be an explicit new model request and is subject to the candidate request limit. The change does not alter historical trial configuration or scores.

An offline regression in `experiment/candidates/test_workspace_identity.py` verifies that the configured Pydantic provider has zero hidden HTTP retries. It runs against the exact cached CP85 dependency image with current source mounted read-only, no network, no capabilities, and no fixture services. Result: PASS. This source change is a new candidate revision for future trials; it does not rescore CP85 or establish A/C task performance.

## Limits and next step

The regression checks the provider configuration property, while the separate mock-transport experiment established the pinned SDK's default three-attempt behavior. No live provider or model was contacted. Future A/C comparisons should retain explicit attempt-level telemetry and apply the same per-generation budget semantics to each harness.
