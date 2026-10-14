# CP91 — Keep model tool arguments outside orchestrator authority

**Date:** 2026-10-14  
**Base:** CP90 `f2728511bc577d0bf5bcab673eb35aeb62b3a64d`  
**Evidence class:** source reproduction and isolated proxy regression  
**Provider/model requests:** none

## Finding

The candidate API's shared `gateway_call` proxy attached `X-Hades-Orchestrator` whenever a `task_checkpoint` argument object contained `_orchestrator_resume` or `_orchestrator_finalization`. Lean tool arguments are JSON-decoded and passed to this proxy without an additional schema-validation gate. Thus a model-shaped tool call could ask the candidate service to attach its private orchestrator credential. `_orchestrator_resume` could reach a trusted state transition; `_orchestrator_finalization` also bypassed the proxy's ordinary candidate completion-claim interception. The gateway still performs its own effect/contract checks, but the candidate must not be able to mint the trusted caller identity.

The issue was reproduced without contacting the gateway: the CP90 source revision's `gateway_call` was loaded from Git, `urlopen` was replaced with a local capture function, and a synthetic reserved field caused that old function to attach a synthetic orchestrator header. No credential, real gateway request, or task mutation was involved.

## Correction

Model-facing calls now use `trusted_internal=False`. The proxy rejects either reserved field before HTTP dispatch unless the trusted Python finalizer/resume path explicitly sets `trusted_internal=True`. Only `transition_task` sets that flag, and only when it adds its own finalization or resume metadata. Candidate calls through the OpenAI, Pydantic AI, and Hermes MCP paths use the default false value.

## Verification

- `test_candidate_finalization.py`: 25/25 passed locally; new regression checks forged `_orchestrator_resume` and forged `_orchestrator_finalization` both raise before `urlopen`.
- `test_workspace_identity.py` passed in a cached candidate container with `--network none`, read-only filesystem/source, all capabilities dropped, and no-new-privileges. It confirms the trusted resume path explicitly marks its internal call.
- Python compilation passed for the changed candidate and tests.
- Full exact-SHA CI passed on `b747762dc0e3789abd577e86c0e716d8df165a65` in run [38612829657](https://github.com/p0rkm4th/hades-v3/actions/runs/38612829657), including the strict three-harness offline lifecycle and recovery suites.

The regression proves the proxy no longer forwards model-supplied reserved fields. It is not a full adversarial live-model test or a claim that arbitrary code execution inside the candidate service could not access that service's configured secret. Keep the candidate service's tool-argument boundary and the gateway's independent evidence validation in place.

No historical scores were changed. CP89 memory timeouts, CP90 fixture-start CI failure, and all CP81 results remain intact. ADR-010 remains **NOT READY**.
