# CP70 — Bounded live GPU requalification protocol

**Status: owner-authorized single trial attempted; stopped before inference at the runtime-readiness gate.** The owner explicitly authorized this bounded CP70 attempt. The Hypnos Ollama API and approved model could not be verified as available, so no route was created and no model request was sent. This authorization is now exhausted; another live trial requires new owner authorization.

## Objective

Determine whether Pydantic AI (A), reduced Hermes with its actual MCP tool flow (B), and the lean loop (C) can each finish the same synthetic read-only infrastructure observation through the same pinned GPU model after the CP69 native Ollama history correction. This is one matched integration requalification, not a harness ranking or production qualification.

## Entry gates

All gates must pass before connecting candidates:

1. The CP69 exact commit is public, reachable, privacy-audited, and has passing exact-SHA CI. Offline strict-peer tests pass at least three times per candidate with the pinned candidate/runtime dependencies.
2. Freshly verify Hypnos host identity with the documented break-glass runbook and strict host-key checking. Verify NVIDIA driver health, current workload, model residency and digest, served model identity, effective context of at least 65,536, and endpoint availability. Stop if anything differs from the approved profile or could disturb existing workloads.
3. Recreate only the dedicated HADES v3 adapter path. Candidates can reach only the adapter; the adapter can reach only the verified Hypnos inference IP and port. Confirm host firewall enforcement, Docker network isolation, adapter route/method/model allowlists, and negative egress probes to other homelab hosts, ports, and services. No SSH key or privileged socket enters a container.
4. Record the exact firewall and Compose configuration digests, expected host-key fingerprint (without secret material), model digest, adapter settings, durable budget state, and rollback commands before starting.

Any failed identity, health, residency, isolation, authorization, or configuration check aborts the run before inference.

## Matched run limits and configuration

- One synthetic read-only observation task per candidate, sequentially, with identical user wording, fixture values, tool contracts, task limits, and independent scoring rubric.
- Identical approved `gemma4:12b` Q4_K_M model digest, 65,536 effective context, temperature 0, and maximum output 1,024 tokens.
- At most three upstream generation attempts per candidate, nine total. The adapter enforces a durable deadline and budget across process restarts. The wall-clock window is 20 minutes from the first candidate connection; no extension, rerun, or replacement trial.
- No extra model calls for retries, evaluation, or repairing malformed output beyond those counted attempts. Record every reservation, dispatch start, upstream result or uncertain dispatch, and rejection. Preserve a charge for uncertain dispatched requests.
- Run A, then B, then C. Stop on workload interference, unexpected network access, isolation drift, configuration change, or the durable budget/deadline.

## Per-candidate acceptance gates

A candidate passes the smoke only if all of these independently hold within its allowance:

1. Adapter logs show the approved endpoint/model/settings and only authorized requests; native request histories pass the strict protocol validator.
2. The harness selects and invokes exactly the authorized `infrastructure_read` operation using the authenticated gateway. Hermes must complete its normal `tool_search` and MCP `tool_call` sequence.
3. The final generation received the genuine gateway observation. The final answer matches the fixture oracle, reports unavailable/unknown values honestly, and contains no provider diagnostic or unsupported claim.
4. The task ledger reaches `COMPLETED` through trusted read verification; independent task/effect queries confirm zero effects, no unauthorized tool or memory mutation, and no lingering RUNNING task.
5. The trace explains every generation; no unexplained retry, auxiliary generation, or silent budget expansion occurred.

Report protocol validity, tool selection, end-to-end completion, semantic correctness, lifecycle integrity, runtime failure, and model/provider failure separately. A single successful task does not qualify a harness or establish a winner.

## Evidence and rollback

Capture sanitized per-generation dispatch state, status, tool names and IDs, prompt/completion tokens, Ollama prompt/evaluation timing, latency, task transitions, and GPU/workload observations. Independently inspect the task/effect database and verify fixture state. Do not publish private IPs, credentials, host paths, or raw sensitive logs.

At completion or abort, stop only CP70 processes; remove only temporary CP70 containers, networks, volumes, and firewall rules. Verify the exact pre-run firewall baseline is restored, no CP70 network or rule remains, fixture values are unchanged, and HADES v2/Ollama services and workloads were not modified. Record rollback checksums/status.

## Decision use

If all three pass, select the next comparison family from crash recovery, memory continuity (with memory writes still fail-closed), compound operations with exact independent after-state checks, and protected actions/prompt injection. If any candidate fails, preserve the failure and isolate runtime, protocol, provider/model, lifecycle, and semantic causes before proposing further work. Do not declare an ADR-010 recommendation from this smoke. ADR-010 remains NOT READY until broader repeated, matched evidence supports a decision.
