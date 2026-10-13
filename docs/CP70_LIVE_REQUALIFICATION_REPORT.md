# CP70 — Live GPU requalification result

**Outcome: stopped before inference.** The owner authorized one bounded A/B/C trial. The run did not pass preflight, so no candidate connected, no GPU generation occurred, and no live candidate result was scored.

## Preflight evidence

- Source: public `main` at CP69 `4837b13cfe35cc63e4e464f117cc61d50b0df3ce`; local checkout was clean and matched `origin/main` before this report. Exact-SHA CI run [38355914741](https://github.com/p0rkm4th/hades-v3/actions/runs/38355914741) completed successfully. The CP69 strict offline evidence records three completed trials each for A, B, and C.
- Access: documented Codex key, strict host-key checking, remote `codex` identity, and noninteractive sudo identity all verified.
- GPU: both Quadro P4000 devices reported NVIDIA driver 580.178.04, zero utilization, and 3 MiB of 8,192 MiB used per device. No GPU compute processes were reported.
- Serving endpoint: the Ollama process was present, but the documented service manager reported it inactive. Requests to `/api/version` and `/api/ps` failed to connect. No loaded model or model digest could be verified. Effective context, served settings, and endpoint workload could not be established.
- **Gate decision:** endpoint/model/runtime availability was not verifiable. The protocol requires abort before any inference on this condition. No live adapter or candidate was connected, and no firewall rule, route, or durable trial budget was created. No candidate source or image digests were frozen because candidates never connected.

The SSH identity and driver checks passed; the serving readiness gate failed. The discrepancy between the healthy driver and unavailable Ollama API was not investigated by changing or restarting services. No Hypnos configuration, HADES v2 service, or existing v3 service was changed.

## Source and configuration identity

- Source revision tested for CP69 qualification: `4837b13cfe35cc63e4e464f117cc61d50b0df3ce`. The documentation-only CP70 result is based on that source.
- SHA-256 configuration digests: inference adapter Dockerfile `adee8c49ae16969a1f8ab1b4e9372f6c67946051c2b2ec127cbba83384bf600e`; candidate Dockerfile `d0ed1446c6cf7f9c6cbeee59c454e4ba90143c5bbd9975e6e57910de40f56fb9`; Hermes Dockerfile `e115b785f6e52252951b5a0e5be59310636afb933e996c49fcd4e5b02dcd1927`; GPU Compose profile `6cb62ab6047f1ab62d8b38afd933f6028af9607e40629b3bdd4b5849c837f6bb`; firewall helper `f82cb8c78f92b303164a014ed50b6be6a5603f19880ce26372e7ad4c0d519ede`.
- No live adapter/candidate image digest was frozen: the run stopped before image selection or candidate startup. The hashes above identify source/configuration inputs, not built image digests.

## Candidate result classification

| Dimension | A: Pydantic AI | B: reduced Hermes | C: lean loop |
|---|---|---|---|
| Live protocol/model request | Not run | Not run | Not run |
| Tool selection, gateway observation, final answer | Not scored | Not scored | Not scored |
| Live task/effect integrity | No live task created | No live task created | No live task created |
| Live latency, tokens, GPU throughput | Not measured | Not measured | Not measured |
| Offline strict-peer integration | CP69: 3/3 | CP69: 3/3, actual streaming/MCP | CP69: 3/3 |

This is an infrastructure-readiness blocker, not a candidate failure or a model-capability result. A, B, and C remain viable for the narrow integration scenario based on CP69 offline evidence only. CP67/CP68 negative live evidence remains intact.

## Cleanup and scope

The live route and firewall setup were never invoked, so there were no CP70 host rules to restore. The independent offline CP69 strict-peer recheck passed all nine trials (`all_completed=true`, three per candidate, memory rows unchanged). Its disposable Compose resources were removed; no CP70-prefixed container, network, or volume remains. Existing HADES v2 and v3 services were not targeted. No Ollama request was issued.

## Next step

Do not repeat the live trial under this authorization. The owner may separately authorize a new bounded attempt after Hypnos Ollama availability, approved model digest, residency, and effective context can be verified read-only. Keep the identical A/B/C conditions and preflight gates. Continue offline work with the highest-value comparative family: durable crash recovery and task continuation across restart, followed by memory correction/recall, compound operations with independent after-state checks, and protected actions. Memory writes remain fail-closed. ADR-010 remains **NOT READY**; no harness winner or architecture decision is supported by CP70.
