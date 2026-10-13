# HADES v3 comparison and qualification matrix

Historical rows preserve evidence through CP68. CP69 results below add strict offline protocol compatibility; they do not erase or rescore the CP67/CP68 live GPU failures. Offline scripted success establishes integration behavior under a deterministic model peer; it does not qualify a harness or establish a winner.

| Capability | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Evidence / remaining gap |
|---|---|---|---|---|
| Offline scripted tool lifecycle | 3/3 completed; 2 generations/trial | 3/3 completed; 3 generations/trial, actual streaming and MCP | 3/3 completed; 2 generations/trial | Identical prompt/config, genuine authenticated gateway observation; exactly one authorized `infrastructure_read`; correct fresh/stale/unknown answer; all tasks `COMPLETED`; zero effects/memory changes. |
| Live GPU model/config | First generation succeeded on approved `gemma4:12b` Q4_K_M; effective context 65,536; temp 0; max output 1,024 | Same verified model/config | Same verified model/config | Same model digest for all. GPU observed up to 100% on both devices during successful generations. Smoke only, not a benchmark. |
| Live tool selection/invocation | Correct read selected | `tool_call` selected; actual MCP read invoked | Correct read selected | All three received genuine gateway observations. |
| Live follow-up/final answer | Both dispatched follow-ups returned upstream HTTP 400; no answer; runtime hit adapter ceiling | Both dispatched follow-ups returned HTTP 400; retries rejected pre-dispatch; returned provider rate-limit message | Follow-up returned HTTP 400; runtime stopped | Five upstream HTTP 400s, three retries rejected before upstream, eight of nine reservations used. Shared adapter/Ollama tool-history incompatibility is leading hypothesis; precise cause unproven because response bodies were not retained. |
| Durable live task / semantic correctness | `FAILED`, no final answer | `COMPLETED` from trusted read evidence, but answer was not a useful observation summary | `FAILED`, no final answer | All terminal; zero `RUNNING`, zero effects, memory rows unchanged. Durable task completion is not semantic correctness. |
| Live latency / throughput | First generation 23.9 s; 13.57 tok/s | 27.8 s; 12.99 tok/s | 20.9 s; 13.52 tok/s | Per-generation data and GPU samples are in sanitized CP68 results. Three first generations do not support ranking. |
| Multi-step household operation | Prior mixed matched CPU results, including exact successes and partial outcomes | Not qualified at common GPU context | Prior mixed matched CPU results, including exact successes and partial outcomes | Continue repeated trials with exact independent final-state verification. |
| Memory correction / fresh-context recall | Prior limited CPU evidence | Not qualified | Prior limited CPU evidence | Memory writes remain fail-closed as `WAITING` because task-linked durable effect evidence is unproven. |
| Shell/Git work and verified outcomes | Existing isolated CPU evidence includes successes and failures | Not qualified at a common endpoint | Existing isolated CPU evidence includes successes and failures | Continue held-out work, tests, and independent repository verification. |
| Crash recovery / continuation | Prior task-specific mixed profile results | Not qualified | Prior task-specific mixed profile results | Test interruption, restart, durable checkpoint inspection, continuation, exact completion. |
| Authorization / prompt injection | Partial historical coverage | Not qualified | Partial historical coverage | Extend negative tests for unauthorized effects, injected instructions, approvals, and reconciliation. |
| Inference route isolation | CP68 negative egress/API tests passed | Same | Same | Adapter-only fixed upstream; host allowlist permits only Hypnos inference TCP 11434; other adapter forwarding and host-input blocked. Temporary CP68 firewall, containers, networks, and volumes removed. |

## Decision status

CP68 proves all three real harness integrations can complete a trusted tool lifecycle offline. On the live GPU endpoint, each selected the correct tool, but a shared follow-up request incompatibility prevented useful completion. Preserve both outcomes; do not rank A, B, or C. The exact upstream compatibility defect remains unproven. Further GPU traffic requires new owner authorization. ADR-010 remains NOT READY, and production implementation remains unauthorized.

The CP69 strict-peer gate is complete. CP70 was owner-authorized but stopped before inference because the Hypnos Ollama API and approved model were not verifiably available. No candidate live result was collected. See [CP70 live requalification report](CP70_LIVE_REQUALIFICATION_REPORT.md). The CP70 authorization is exhausted; any new live attempt needs new owner authorization.

## CP69 strict offline compatibility and lifecycle matrix

| Dimension | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Common evidence / limit |
|---|---|---|---|---|
| Native Ollama protocol | 3/3 strict-peer histories and tool schemas valid | 3/3 valid through actual streaming/MCP | 3/3 valid | Independent strict peer validates native argument objects, tool names/IDs, sequence, roles, and tool declarations. Reconstructed OpenAI-shaped history is rejected. |
| Tool selection and execution | 3/3 exact `infrastructure_read` | 3/3 exact MCP `infrastructure_read`, via `tool_search` then `tool_call` | 3/3 exact `infrastructure_read` | One fixed synthetic read contract and authenticated gateway. |
| End-to-end completion | 3/3 | 3/3 | 3/3 | Two generations A/C; three B. No unexplained or auxiliary requests. |
| Semantic answer / independent oracle | 3/3 fixture states and uncertainty represented | 3/3 fixture states and uncertainty represented | 3/3 fixture states and uncertainty represented | Deterministic scripted peer answer is not evidence of live model semantic capability. |
| Task/effect integrity | 3/3 durable `COMPLETED`, zero effects | 3/3 durable `COMPLETED`, zero effects | 3/3 durable `COMPLETED`, zero effects | Zero memory changes and no lingering RUNNING tasks. Provider failures and diagnostic final messages fail closed; memory writes remain WAITING absent task-linked durable effect evidence. |
| Runtime/provider failure paths | Shared lifecycle and adapter tests | Provider diagnostic explicitly rejected as final answer | Shared lifecycle and adapter tests | HTTP 400 after read, exhausted budget, timeout, malformed output/history, invalid provider completion, retries, and partial effect state covered by tests. |
| Latency / resource use | Local scripted peer only | Local scripted peer only | Local scripted peer only | Not comparable to GPU throughput; no Hypnos requests were made during CP69. |
| Implementation complexity | One Pydantic profile capability override to avoid unsupported `strict` extension | Existing actual Hermes MCP/streaming integration | Existing small loop | Shared adapter performs protocol mapping. No prompt tuning. |

### CP69 protocol diagnosis and limits

The adapter's previous raw pass-through preserved OpenAI tool-history syntax (`type:function`, stringified arguments, and tool results without native `tool_name`) for Ollama's native `/api/chat`. CP69 reproduces the schema rejection with an independent strict local peer and verifies the common adapter translation fixes it for all actual candidates. CP68 upstream HTTP 400 bodies were not retained and a local Ollama runtime was unavailable; the compatibility fault is strongly supported by reconstructed traces and the strict peer, while the exact historical upstream diagnostic remains unconfirmed. Do not change the historical CP68 classification to a proven exact error.

Protocol compatibility, harness execution, model capability, durable lifecycle correctness, and semantic answer quality remain separate axes. CP69 is a strict offline integration pass only. CP70 was stopped before inference at infrastructure preflight; it produced no live candidate result. ADR-010 remains NOT READY.

## CP70 live preflight outcome

| Dimension | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Common evidence / limit |
|---|---|---|---|---|
| Live inference and end-to-end task | Not run | Not run | Not run | Preflight stopped before inference: Ollama API requests failed and the approved model, digest, residency, and context could not be verified. No live task or generation exists to score. |
| Offline strict-peer integration | CP69 3/3 | CP69 3/3 | CP69 3/3 | Rechecked using the repository runner after CP70 preflight; all nine completed and memory rows were unchanged. Hermes used actual streaming/MCP. |
| Harness viability | Viable for further qualification | Viable for further qualification | Viable for further qualification | Infrastructure-readiness blocker, not a candidate or model failure. This does not qualify live inference or establish a winner. |

The CP70 attempt created no live route, firewall rule, candidate connection, or model request. CP67/CP68 outcomes remain unchanged. Next priority is crash recovery and durable continuation across restart, then memory continuity, exact-state compound operations, and protected-action resistance. ADR-010 remains NOT READY.

## CP71 corrected preflight and live gate

| Dimension | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Common evidence / limit |
|---|---|---|---|---|
| Corrected Hypnos service preflight | Ready for a bounded context probe | Ready for a bounded context probe | Ready for a bounded context probe | The enabled `scotty` user unit and configured binding are healthy; approved model digest/quantization installed but unloaded. Effective context remains unverified. |
| Live inference and end-to-end task | Not run | Not run | Not run | Safely stopped before route setup: host firewall rules could not be inspected or applied from this workspace. No generation or candidate result exists. |
| Offline strict-peer integration | CP69 3/3 | CP69 3/3 | CP69 3/3 | Unchanged. CP67/CP68 live failures and CP70 false-negative record remain intact. |
| Isolation qualification | Not re-tested | Not re-tested | Not re-tested | Internal candidate networks are configured, but the required adapter-only host egress rule and negative tests were not established for CP71. |

CP71 corrects the CP70 preflight implementation and adds regression coverage. It does not qualify live GPU integration. The adapter's separate one-use context bucket and durable deadline, plus CP71 chain construction, pass offline tests; host enforcement remains unproven. The smallest remaining blocker is controlled root access to snapshot, install, verify, and remove the previously reviewed host firewall guard. No CP71 trial resources were created; the isolated preflight regression-test container was removed. ADR-010 remains NOT READY.
