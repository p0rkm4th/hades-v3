# CP71 — corrected GPU preflight and safe abort

**Outcome: preflight corrected; live trial safely stopped before inference.** The Hypnos service and endpoint are healthy, but the required host-enforced adapter egress boundary could not be inspected or installed from this workspace. No model generation, context probe, candidate request, inference route, firewall rule, trial network, or trial volume was created. The local regression test used a disposable test image/container, both removed after the pass.

## Corrected preflight

The new [Hypnos preflight](../experiment/scripts/hypnos_gpu_preflight.py) queries the enabled `scotty` user unit `ollama-hades.service` using the documented strict Codex SSH identity. It reads `OLLAMA_HOST` from both the managed unit and the live process, rejects mismatch or configuration drift, bypasses environment HTTP proxies, and sends bounded probes to the configured binding. It distinguishes service health, listener/API health, installed model identity, model residency, and effective context. An installed but unloaded model is accepted as healthy; catalog context metadata is not treated as effective context.

Ten automated regression tests cover the CP70 loopback/system-service false negative, user-unit health, configured listener selection, unloaded model acceptance, model digest and quantization, loaded context status, API/port drift, and managed/live configuration drift. They are included in Prototype CI.

The existing adapter and firewall helper now also support CP71's offline control contract: a separate one-use context-probe credential, durable count and deadline state, a clock that starts with the first reserved generation, and checkpoint-scoped CP71 firewall chain names. Reservations are persisted before dispatch, with file and directory sync. The context probe has a hard one-generation cap; tests exercise three-per-candidate and ten-total settings. A separate regression suite validates firewall rule construction without applying it. All 28 relevant preflight, adapter, budget-seeding, and firewall-construction tests pass in a network-isolated container. These tests do not prove host firewall enforcement or a live model route.

## Read-only Hypnos result

- The correct `scotty` user service is enabled and active; process owner is `scotty`.
- The endpoint discovered from the live `OLLAMA_HOST` responds on its configured binding. Loopback is not the configured listener.
- Ollama API version is 0.31.1. The approved `gemma4:12b` Q4_K_M digest matches the accepted profile and is installed but unloaded.
- Both Quadro P4000 devices are healthy and idle. `/api/ps` is empty, which is a healthy unloaded state.
- Effective context is **unverified** while the model is unloaded. The single authorized context generation was not spent because security gates had not passed.
- No service restart, model load, configuration change, or inference request occurred. The separate Hypnos Code service was not touched.

## Isolation gate and rollback

The existing HADES v3 `operator` network is Docker-internal, and the reviewed design places the adapter on a distinct egress network. However, candidate isolation also requires a host `DOCKER-USER`/`INPUT` rule that permits only the adapter's fixed Hypnos destination and port. This host cannot read the active firewall rules or apply/verify that rule: direct `iptables` access is denied and noninteractive sudo is unavailable. Docker group membership does not demonstrate the firewall policy. Using a Docker host-network `NET_ADMIN` helper would grant broad host-firewall control and would not provide a safe, reviewable substitute for the documented rule procedure.

The route was therefore not created. No CP71 firewall rules, inference adapter, candidate containers, trial networks, or trial volumes exist to roll back. During regression testing, an initial Compose test command unexpectedly began recreating three existing v3 fixture/workspace containers. It was interrupted; the three original containers were restarted and verified healthy using their original container image IDs. Their persistent volumes were retained. Compose rebuilt local image tags, but the running containers remain on their original image IDs. No HADES v2 or Hypnos service/configuration was changed. Candidate-to-Hypnos negative egress tests, adapter bypass tests against a live adapter, and route/configuration digests were not claimed because there was no CP71 route to test.

## Result and next action

CP70's false-negative preflight is corrected and regression-tested. CP71 produced no live candidate outcomes: A, B, and C remain unscored by this attempt. Model identity and GPU readiness were verified, but effective context and live inference compatibility remain open. The minimal blocker is controlled root access on the experiment host to snapshot its firewall and apply/remove the existing narrowly scoped guard. After that access is available, a new owner-authorized bounded trial can repeat the full gates, use at most one context probe, and run A/B/C sequentially. This CP71 attempt is concluded; no further GPU trial is authorized here.

CP67–CP70 evidence is unchanged. ADR-010 remains **NOT READY**; no harness winner or production implementation is authorized.
