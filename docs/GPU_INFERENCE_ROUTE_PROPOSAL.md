# GPU inference route

**CP67 status:** the bounded trial route was implemented, host-enforced, tested, used for the six reserved generations, then rolled back. The reusable v3-only adapter, Compose profile, and firewall helper remain in source. No CP67 host rules, adapter containers, trial networks, or trial volumes remain active.

## Route and enforcement

```text
candidate API / reduced Hermes
              |
    dedicated internal model network
              |
       fixed inference adapter
              |
    dedicated adapter egress bridge
              |
       Hypnos Ollama only
```

Candidate containers joined the internal model network and the existing isolated v3 operator network. Only the adapter joined the egress bridge. Docker assigned its egress source at container creation; that address was read locally and supplied to the host-rule helper. The public Compose file contains no private bridge or homelab CIDR. The adapter had a fixed model, a private locally configured upstream URL, no published host port, a read-only root filesystem, all Linux capabilities dropped, and no Docker socket or SSH credential. It did not join the operator, fixture, workspace, or HADES v2 networks.

The temporary host rules used `DOCKER-USER` and `INPUT`:

```text
DOCKER-USER: adapter-egress-source -> HADES3GPUFWD
HADES3GPUFWD: allow TCP to verified-Hypnos-/32 on port 11434
HADES3GPUFWD: drop every other forwarded packet from adapter-egress-source
INPUT: adapter-egress-source -> HADES3GPUIN
HADES3GPUIN: drop packets sourced from adapter-egress-source
```

Private addresses are intentionally omitted. During testing, the forward allow rule counted 50 packets, the forward drop rule counted 4, and the host-input drop rule counted 4. Candidate-shaped containers could not connect directly to Hypnos inference, Hypnos SSH, or Tartarus SSH. From the adapter's egress identity, the approved Ollama TCP port connected; Hypnos SSH, Tartarus SSH, laptop SSH, and the Docker host bridge were blocked. Candidate containers reached the adapter's authenticated model-list route but not native Ollama administrative paths or unsupported OpenAI endpoints. The adapter unit suite rejected caller-supplied upstreams, model overrides, methods, routes, and redirects; it disabled proxy environment use and redirects.

For a future reauthorized run, create only the adapter first, inspect its assigned egress source locally, install the host rule with that source and the verified Hypnos address, then start it before attaching or starting candidates. Candidate traffic must wait until the rules and negative checks pass.

After CP67, only CP67 containers were stopped and removed. The two temporary Docker networks and four CP67-only volumes were removed. The adapter's assigned source was removed from the host rules; both CP67 chains and their jumps are absent. Existing v3 candidate and CPU inference containers remained running. HADES v2 and Hypnos services/configuration were not modified. The model was not explicitly unloaded; Ollama's existing keep-alive policy remains in control.

The rollback order is: stop only `gpu-inference-adapter`, `gpu-candidate-api`, and `gpu-hermes-amber`; run `python experiment/scripts/gpu_trial_firewall.py rollback --adapter-ip <locally-inspected-trial-adapter-ip>` as root; remove only those three CP67 containers; remove `hades-v3-gpu-model-access` and `hades-v3-gpu-egress`; then remove the CP67-only Hermes and budget volumes. Never use `docker compose down` for the shared v3 project as rollback.

## Adapter contract

The adapter accepts only authenticated `GET /v1/models` and `POST /v1/chat/completions`. It rejects every other route and method, a caller-selected model, destination override fields, malformed or oversized bodies, and invalid streaming flags. It never follows redirects or uses proxy environment variables. Chat calls go only to the fixed native Ollama `/api/chat` path, with model `gemma4:12b`, `num_ctx=65536`, temperature `0`, and `num_predict=1024`. It translates tool calls in both directions. For Hermes streaming requests it returns OpenAI event-stream chunks while still issuing one non-streaming Ollama request.

The current adapter source logs Ollama's prompt and completion token counts, prompt-evaluation time, generation time, and generation tokens per second without logging prompts. The deployed CP67 build did not retain Ollama's `eval_duration`; CP67 therefore has request latency and Hermes-reported aggregate token usage, but no comparable per-generation throughput value.

Per-harness and total generation reservations persist across adapter restarts, and the original absolute 15-minute deadline is preserved. CP67 ended at the authorized budget of two reservations each for Pydantic AI, Hermes, and lean, six total. Fresh per-trial API keys are injected at runtime and are not stored in the public repository; they authorize only requests to the fixed adapter. They provide no homelab access. The host firewall and network attachments enforce the boundary.

## Matched configuration and evidence

All three harnesses used the same `gemma4:12b` Q4_K_M model digest, reported effective context 65,536, temperature `0`, and 1,024 output-token limit. `/api/ps` confirmed `context_length=65536` after the first request loaded the previously nonresident model. A and C invoked the real synthetic `infrastructure_read` gateway tool; B made two generations but invoked no tool. No candidate returned a useful final answer. All three durable tasks are `FAILED`; independent task/effect reads show zero effects, and the tool traces show no memory writes or corrections. The CP67 smoke is an integration failure, not a candidate qualification or comparison pass.

One-second host sampling during each run observed GPU utilization peaking at 100% on both Quadro P4000 devices, with approximately 6.6 GiB and 6.8 GiB reported in use. Ollama reported the loaded model's VRAM allocation as 10,690,263,775 bytes. These are bounded smoke observations and do not establish sustained throughput.

The private endpoint and actual firewall source/destination values are excluded from this public record. The deployed CP67 route snapshot digest is `975978b8b8988f2efbad751f3163b7227e91496572e23a9a8f65cad30d47b294`; it covers the active rules, adapter runtime configuration, persistent budget, and source files as deployed. The current sanitized route-source bundle has digest `2566c1886749c3c97054c84291f53d10837ba40ea0c647e5dfc0a7ad100fcf43` (SHA-256 over the listed route, candidate, and lifecycle source files). The public source retains the policy while omitting runtime addresses. See the sanitized [CP67 result records](../experiment/results/cp67_gpu_smoke.jsonl), [adapter tests](../experiment/tests/test_inference_adapter.py), and [firewall helper](../experiment/scripts/gpu_trial_firewall.py).

## Remaining qualification

The live route and fixed upstream passed the isolation checks. The three harnesses did not complete the shared read-only task within their two-generation ceilings: Pydantic AI and lean reached a read tool but exhausted their limits before a final response; Hermes first had one zero-generation compatibility attempt rejected, then reached Ollama with streaming requests and exhausted its two-generation allowance through internal retries without invoking a tool. Fake-upstream tests verify streamed tool-call conversion, but live Hermes tool-call streaming was not exercised. Further inference would exceed CP67's six-generation authorization and is not performed here. A future bounded trial needs harness request loops configured to fit the same two-generation limit, followed by a newly authorized smoke window. ADR-010 remains NOT READY; production implementation remains unauthorized.
