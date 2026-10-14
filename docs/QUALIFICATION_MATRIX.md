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
| Memory correction / fresh-context recall | Scalar 3/3; list mutation 3/3, answer 2/3; structured 0/3; list recall 0/3 | Not model-equivalently tested below 64,000 context | Scalar 3/3; list mutation 3/3, answer 2/3; structured 0/3; list recall 0/3 | Matched CPU Qwen3-8B, 40,960 context; scalar correction included restart/fresh-context recall 3/3 per A/C. Mixed outcomes, no winner. Arbitrary writes remain fail-closed; CP75 scores unchanged. See CP81 report and trial JSONL. |
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

## CP72 uncertain-effect recovery

| Dimension | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Common evidence / remaining gap |
|---|---|---|---|---|
| Matched CPU model tool selection | 3/3 commitment submit + reconcile | Not run; Qwen context is below Hermes minimum | 2/3 submit + reconcile; 1/3 timeout before tools | Same synthetic task, model, inference profile, approval contract and simulator. |
| Independent effect integrity | 3/3 one receive, one effect, `CONFIRMED` | Not scored | 2/3 one receive, one effect, `CONFIRMED`; timeout 0 effects | No unauthorized operation, duplicate dispatch, or memory mutation observed. |
| Semantic answer | 3/3 accurately reported canonical synthetic reservation | Not scored | 2/3 accurate; timeout had no answer | Strict deterministic recovery peer still needed for B at context >=65,536. |
| Durable task completion | 0/3 `COMPLETED`; explicit completion checkpoint absent | Not scored | 0/3 `COMPLETED`; explicit completion checkpoint absent | Tasks were closed `FAILED` for review after preserving candidate state. Useful answers and confirmed effects do not substitute for lifecycle proof. |
| Process restart after committed effect / before acknowledgment | 1 interrupted trial; after correction recovered same effect ID, no duplicate, accurate answer, task `FAILED` | Not run | 1 interrupted trial; recovered same effect ID, no duplicate, accurate answer, task `FAILED` | Pre-fix A interruption is retained as evidence: repeated resume was blocked in `WAITING` after a retry hit consumed approval. |
| Reconciliation and retry contract | Shared regression passes for accepted and not-received canonical states | Shared contract only | Shared regression passes | `DISPATCHED` can now reconcile to `CONFIRMED`; exact same-task replays return the persisted effect and never redispatch. Network/process loss during reconciliation and kill between reconciliation and final response remain open. |
| Implementation/runtime failure | No task-level runtime failure in matched baseline; omitted lifecycle claim | Not scored | One model-request timeout before tool use | Root causes and shared fixes are documented in [CP72 report](CP72_DURABLE_RECOVERY_REPORT.md). |

CP72 corrects two durable recovery defects and stale uncertainty handling, but it does not qualify A or C: both failed to durably complete the task after a confirmed operation. C also timed out before tool selection once. B has no model-equivalent CPU result because the verified 40,960 CPU context does not meet its 64,000 minimum. The next experiment must fault-inject reconciliation outages and final-answer interruption, then run B through the same strict recovery contract at >=65,536 context. ADR-010 remains **NOT READY**.

## CP73 evidence-driven completion and recovery

| Dimension | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Common evidence / remaining gap |
|---|---|---|---|---|
| Matched interrupted-effect recovery | 3/3 after two API restarts | Not run; CPU profile is below Hermes's minimum | 3/3 after two API restarts | Same bounded task, one-effect contract, approval, Qwen3-8B Q4_K_M CPU settings, simulator, and procedure. |
| Canonical operation integrity | Original effect confirmed; receive_count=1 each | Not scored | Original effect confirmed; receive_count=1 each | No duplicate/unauthorized operation, extra effect, or memory mutation. Exact task/effect/approval identity and canonical target independently checked. |
| Durable completion without model checkpoint | 3/3 `COMPLETED` | Not scored | 3/3 `COMPLETED` | Immutable authenticated task criteria plus persisted effects, consumed approval, canonical state, and persisted final response. Delivery remains `PERSISTED_PENDING_DELIVERY`. |
| Semantic final answer | 3/3 accurate | Not scored | 3/3 accurate | Independently checked against the synthetic appointment oracle; forced termination lost initial-turn token counters, so total generation/token counts remain unknown. |
| Reconciliation fault injection | Shared regression passes: transient canonical GET failure quarantines, repeated reconcile confirms same effect | Shared regression only | Shared regression passes | `NOT_RECEIVED` remains quarantined without redispatch. These are contract tests, not matched candidate repetitions. |
| Provider/memory/partial safeguards | Regression suites reject completion | Shared contract; no recovery run | Regression suites reject completion | Provider failure after effect remains pending; partial, mismatched, uncertain, and memory effects cannot complete. |

CP73 fixes a narrow orchestrator lifecycle defect: exact trusted criteria let the gateway complete a bounded task from independently verified persisted evidence without model bookkeeping. It does not infer arbitrary free-text task success. Reconciled-before-response restart was repeated 3/3 for A and C; transient reconciliation network failure and `NOT_RECEIVED` are regression-tested, not three-repetition semantic comparisons. Hermes remains unassessed on recovery due its context floor. See [CP73 report](CP73_EVIDENCE_DRIVEN_RECOVERY_REPORT.md) and [sanitized trial records](../experiment/results/cp73_completion_recovery.jsonl). CP72's original failures remain unchanged. ADR-010 remains NOT READY.

## CP74 — task-linked memory durability and fresh-context retrieval

| Dimension | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Common evidence / remaining gap |
|---|---|---|---|---|
| Initial preference recall | 1/1 correct | Not run; CPU context below minimum | 1/1 correct | Same synthetic key/value, Qwen3-8B Q4_K_M, 40,960 context, temperature 0, 1,024 output cap. Single observation only. |
| Candidate memory correction | 0/1; `memory_correct` rejected HTTP 404 | Not run | 0/1; `memory_correct` rejected HTTP 404 | Both left the canonical row unchanged and tasks `FAILED`; no effect row. The captured request lacks enough detail to identify whether query or expected value mismatched. |
| Fresh-context retrieval | 1/1 correct after independent fixture setup | Not run; CPU context below minimum | 1/1 correct after independent fixture setup | Candidate had no prior conversation context; each used `memory_search`, task `COMPLETED`, zero effects, answer matched oracle. The corrected value was seeded by test setup, not by a candidate. |
| Task-linked mutation durability | Integration contract passed | Shared gateway contract; no Hermes model run | Integration contract passed | Existing effect ledger links mutation to task/user/domain/key/value; canonical mutation and `MEMORY_MUTATION` effect commit atomically; exact retry returns same effect, changed retry rejects. Integration regression also checks fresh read and cross-domain denial. |
| Lifecycle and integrity | Known no-effect rejection `FAILED` | Shared contract only | Known no-effect rejection `FAILED` | Regression suites reject unlinked writes and require persisted identity-linked evidence plus current canonical value for completion. No unauthorized mutation observed. |
| Repetition and recovery | One scored correction/retrieval observation | No eligible model-equivalent profile | One scored correction/retrieval observation | Not qualified: require at least three matched repetitions, restart between mutation and recall, and stronger persisted diagnostics for correction request matching. |

CP74 shows a shared durability contract improvement and a candidate/model correction failure, while both A and C demonstrated initial and fresh-context reads once. It does not qualify memory continuity: the candidates failed the actual correction request and the sample is one pair. Hermes is not scored on the 40,960 context profile because it is below its 64,000 minimum. See [CP74 report](CP74_MEMORY_DURABILITY_REPORT.md) and [trial records](../experiment/results/cp74_memory_continuity.jsonl). ADR-010 remains NOT READY.

## CP75 — stable-key memory CAS

| Dimension | Pydantic AI (A) | Reduced Hermes (B) | Lean loop (C) | Common evidence / remaining gap |
|---|---|---|---|---|
| CAS contract | Passed gateway regressions | Offline contract only | Passed gateway regressions | Exact key+revision update, stale rejection, cross-domain rejection, exact-retry identity, changed-retry rejection, atomic mutation/effect, old-schema migration. |
| Held-out scalar/list correction | Both mutations reached canonical state with one confirmed task-linked effect; both tasks remained `WAITING` | Not run; deterministic peer remains planned | Same as A | Both generated accurate answers but omitted completion checkpoint. Three correction prompts per candidate included structured JSON; see trial JSONL. |
| Structured correction | No tool call; unsupported success answer; task `FAILED`, no mutation | Not run | Same as A | Gateway preserved canonical value and rejected completion. |
| Same-task recovery | Resume read original confirmed effect; no duplicate; task still `WAITING` | Not run | Not run | Model described a checkpoint without invoking it. |
| Fresh-context read after restart | Scalar correct and `COMPLETED` | Not run | Scalar correct and `COMPLETED`; list recall later made no tool call and failed | Retrieval is inconsistent; successful corrections do not establish the full workflow. |

CP75 establishes that stable-key CAS fixes the brittle old-value serialization boundary and that the existing effect ledger can prove atomic, scoped memory changes. It does not qualify candidate memory continuity: A and C each had two safe persisted mutations and one failed no-tool structured attempt, while completion and recall remained inconsistent. CP74's 404 failures remain unchanged. Hermes is unassessed; 40,960 context is below its 64,000 minimum. See [CP75 report](CP75_MEMORY_CAS_REPORT.md) and [sanitized records](../experiment/results/cp75_memory_cas.jsonl). ADR-010 remains NOT READY.

## CP78 — separate Pydantic AI Harness A2 workspace integration

| Dimension | Historical A | A2 Harness proof | B | C | Evidence / limit |
|---|---|---|---|---|---|
| Scope and model | Unchanged | Separate pinned integration candidate; deterministic `FunctionModel` | Not run | Not part of this comparison | A2 does not replace or rescore A. No live inference or model-quality evidence. |
| Gateway-backed workspace task | Historical evidence unchanged | 3/3 clean repetitions | Not run | Not run | `Shell` + `FileSystem` used a command-only supported backend routed through authenticated `workspace_exec`. |
| Independent outcome | — | 3/3 source and tests passed | — | — | Independent oracle reran tests, checked source, and inspected task/effect records. Task intentionally remained `RUNNING`. |
| Effects and overhead | — | 18 candidate commands + 1 oracle command per run; 19 confirmed workspace effects | — | — | No memory or other effects. High overhead for the small synthetic task; compare Shell-only. |
| Isolation / recovery | — | Bounded operator-only internal network check; no workspace/database DNS resolution | — | — | Not a complete adversarial egress test. Uncertain command recovery, background execution, task finalization, and live model behavior remain unqualified. |

CP78 establishes that upstream Harness workspace tools can compose with the existing HADES gateway and effect ledger in a deterministic synthetic repository task. It does not qualify A2 as an agent or compare A/B/C. See [CP78 report](CP78_A2_HARNESS_WORKSPACE_REPORT.md). Historical CP67–CP74 scores and failures remain unchanged. CP71 remains blocked on host firewall privilege; no GPU was used. ADR-010 remains NOT READY.

## Reuse spike update — CP79

| Candidate/area | Protocol and recovery | Independent outcome | Classification | Remaining gap |
|---|---|---|---|---|
| DBOS 3.2.0 + HADES gateway | Three worker-death/restart cases replayed the same task/effect request; two DBOS step attempts per case | HADES ledger retained one confirmed effect and simulator one canonical receive; independent verifier checked approval/effect identity and trusted finalization completed task | **CONTRACT TEST**, not A/B/C score | Compare recovery complexity against current candidates; SQLite spike is not production durability evidence |
| Pydantic AI Harness A2 | CP78 three deterministic workspace runs, 18 candidate commands each | Source/tests and 19 effects independently verified; task remained RUNNING by design | **CONTRACT TEST**, not historical A score | Shell-only comparison and task-finalization/recovery behavior remain open |

CP79's Python 3.13/3.14 SQLite setup failures occurred before any gateway effect and remain recorded in the CP79 report. They do not count as workflow failures.

## CP80 — A2 Shell-only composition comparison

| Profile | Repetitions | Model/tool trace | Independent outcome | Classification | Limit |
|---|---:|---|---|---|---|
| Pydantic AI Harness Shell + FileSystem | 4 local; 3 matched pairs in CI | 4 deterministic model turns; 18 candidate workspace effects per task | Exact source and tests passed; 19 total confirmed effects including oracle | **CONTRACT TEST**, separate A2 candidate | No live model, finalization or recovery evidence |
| Pydantic AI Harness Shell only | 4 local; 3 matched pairs in CI | 4 deterministic model turns; 3 candidate workspace effects per task | Exact source and tests passed; 4 total confirmed effects including oracle | **CONTRACT TEST**, separate A2 candidate | Same limitations; no historical A score change |

Shell-only reduced candidate gateway effects by 15/18 (83.3%) for this specific repository task while preserving the strict oracle result. This supports omitting FileSystem for tasks naturally served by the bounded workspace shell. It does not establish general-model reliability or justify reducing HADES computer agency. The task intentionally remained `RUNNING`. Per-task synthetic IDs and outcomes: [`cp80_a2_workspace_profiles.jsonl`](../experiment/results/cp80_a2_workspace_profiles.jsonl). See [CP80 report](CP80_A2_SHELL_ONLY_REPORT.md).

## CP81 — trusted memory completion and A2 uncertain-command guard

| Area | Evidence | Classification | Remaining gap |
|---|---|---|---|
| Trusted memory completion | The gateway rejects a false claim without mutation, validates one exact CAS effect and canonical revision, returns the same effect on exact retry, rejects a changed retry, and persists the final response. Exact-SHA CI passed at `4cead3a` (`38521858461`). | Database-backed contract regression | Candidate-mediated results are mixed; see the CP81 A/C row and report. |
| A/C memory workflow | On identical CPU Qwen3-8B Q4_K_M (`n_ctx=n_ctx_train=40,960`, temp 0, output cap 1,024), A and C each passed scalar correction and restart/fresh-context recall 3/3. Structured correction passed 0/3 for both: no tool call, no effects, `WAITING`. List mutation was independently correct 3/3 for each with one confirmed effect and durable `COMPLETED`; answer oracle passed 2/3 each. Fresh-context list recall passed 0/3 each, failed safely without tool/effect. 30 phase records: [`cp81-autonomous-20261014.jsonl`](../experiment/results/cp81-autonomous-20261014.jsonl). | **LIVE EXPERIMENT**, matched CPU model, synthetic fixture | Scalar memory path is positive but narrow. Shared structured-task interpretation failure and repeated list-recall failure remain; one inaccurate final answer per candidate despite confirmed mutation. No winner inference. Hermes excluded below its 64,000-context floor. CP75 results unchanged. |
| Memory CAS/completion contract | Database tests cover exact/changed retry, stale revision, cross-user and same-user/mismatched-domain rejection, atomicity, false-claim rejection, and canonical value/revision checks. The cross-domain regression passed exact-SHA CI run [38600538341](https://github.com/p0rkm4th/hades-v3/actions/runs/38600538341) on `389ebb038cdd0aa087b17c7365553f79fee306bd`. | **CONTRACT TEST** | Trusted completion proves the specified exact correction, not arbitrary intent or semantic answer correctness. Memory and task/effect state remain one authoritative gateway/ledger. |
| A2 Shell-only uncertain command | The pinned Harness aborts after one quarantined result without same-turn retry (CI `649bfce`, run `38523264803`). The cross-restart synthetic probe then showed two confirmed effects and marker count 2 because the gateway ignored `operation_id` (`9886f7e`, CI `38528653321`). New isolated tests prove the actual Shell wrapper carries run/tool IDs through workspace I/O and that a process crash leaves a `started` unresolved `StepPersistence` effect. The interrupted snapshot includes the pending call; the default continuation can instead select an earlier complete checkpoint without it. | **CONTRACT TEST** plus **LIVE EXPERIMENT** on synthetic workspace | The A2 adapter/gateway does not yet enforce the identity. The orchestrator must inspect unresolved effects before any continuation; Harness persistence alone is not replay safety. Next: bind task/run/tool identity and request digest in the existing effect ledger; exact confirmed replay returns the original result, changed requests reject, unknown outcomes quarantine. Do not claim exactly-once arbitrary shell. |

The follow-up documentation run at `37589f2` (`38525623070`) failed before fixture startup due to Docker Hub rate limiting. Review of its public log found generated run-scoped test credentials in subsequent environment summaries; they were unused because no fixture service started. The workflow now masks generated values before export, verified in public logs. Exact-SHA CI passed on masking correction `d590da3` (`38525869943`); this infrastructure failure does not change CP81 candidate scores.

CP81 does not change CP75 scores. Hermes remains excluded from CPU model-equivalent memory trials because 40,960 context is below its documented 64,000-token minimum. ADR-010 remains **NOT READY**.

## CP82 — A2 command replay and worker recovery

| Area | Evidence | Classification | Remaining gap |
|---|---|---|---|
| Stable invocation identity | The pinned A2 Shell wrapper forwards `tool_call_id`; task ID, call ID, and backend-dispatch ordinal are hashed and inserted by the adapter, not selected by the model. Network-disabled runtime test passed. | **CONTRACT TEST** | Verify the production-intended orchestrator preserves the original call identity across restart and reconciles old StepPersistence entries. |
| Gateway replay protection | Exact confirmed replay returned the original effect/result after gateway restart; changed request rejected; one marker remained. A seeded `DISPATCHED` effect blocked both same-ID and new-ID attempts without adding an effect. Eight gateway integration tests passed. | **CONTRACT TEST** and isolated synthetic gateway test | Unknown command outcomes remain quarantined with no general canonical reconciliation. The operation ID must be preserved; regenerated new IDs are new operations. |
| Harness worker recovery | A2 worker died after gateway confirmation but before Shell received the response. A test-only gate matched the interrupted `StepPersistence` call to the authenticated canonical effect snapshot; original-call resume and repeated resume both returned the persisted result and independently verified one marker. | **CONTRACT TEST**, strict deterministic peer | HADES task remains `RUNNING`; upstream journal row stays `started`. The test-only coordinator is not integrated in a general runtime. No live-model score. |
| A/C/Hermes workspace adapter compatibility | A and C pass an isolated identity-injection contract using provider tool-call IDs; the shared gateway rejects missing operation IDs. Hermes's MCP proxy does not supply one. | **CONTRACT TEST** for A/C injection; **UNKNOWN** for B | No A/C persisted-history/resume integration has been tested; Hermes workspace execution fails closed until its MCP adapter supplies a stable identity. No live model score. |

CP82 narrows the A2 Shell replay risk for exact persisted calls. It does not establish exactly-once arbitrary shell execution, task lifecycle completion, live-model performance, or a winner. See [CP82 report](CP82_WORKSPACE_COMMAND_REPLAY_REPORT.md).

## CP83 — Pydantic AI Harness + DBOSDurability

| Area | Evidence | Classification | Remaining gap |
|---|---|---|---|
| A2 Shell + DBOS composition | Pinned Harness 0.56.0 / Pydantic AI 2.56.0 / DBOS 3.2.0 used the documented workspace capability hook and HADES authenticated workspace gateway. No host shell, database credential, persistent DBOS service, or model network was available to the runner. | **CONTRACT TEST** | Separate candidate revision; not a live-model comparison or scored A/B/C result. |
| Confirmed-result process recovery | Across 3/3 deterministic trials, a worker died after HADES persisted a confirmed command but before Shell received its response. Restart replay returned the original effect; repeated result retrieval added no model call or effect; one marker remained, two model calls occurred, and independent reads passed. | **CONTRACT TEST** | Only the confirmed boundary is covered. Quarantined/unknown continuation, approvals, cancellation, and finalization remain gaps. |
| Authority and completion | HADES task/effect ledger remained canonical; workflow ID derived from task ID. | **CONTRACT TEST** | Tasks remained `RUNNING`; no task finalization or delivery. DBOS is not adopted as task/effect authority. |
| Complexity impact | DBOS avoids the CP82 test-only resume gate on this confirmed replay path; HADES API, lifecycle, gateway, and A2 adapter remain. | **RESEARCH + CONTRACT TEST** | No net maintained-runtime reduction demonstrated. CP82 gate is experimental test code, not an existing production subsystem. |
| Operational data/retries | Current Pydantic DBOS guidance records workspace command arguments and file contents in workflow history, recommends PostgreSQL for production, and documents retry multiplication and cancellation/streaming caveats. | **RESEARCH** | CP83 used synthetic content with SQLite in tmpfs; no payload codec, retention, deletion, retry-budget, or cancellation test. These are adoption gates. |
| Quarantined timeout recovery | A command wrote one synthetic marker and timed out. After worker death/restart, the same operation remained `QUARANTINED`; gateway refused a second dispatch, repeated resume added no generation/effect, and independent read found one marker. The agent runtime raised `WorkspaceUnavailableError`; no final answer was persisted and task stayed `RUNNING`. | **CONTRACT TEST**, one distinct failure case | No reconciliation/finalization path for this arbitrary shell outcome. Safe quarantine is proven; task continuation is not. |
| Candidate API exception lifecycle | The existing orchestrator maps uncertain effects to `WAITING` for reconciliation and confirmed effects with failed response delivery to `WAITING` for recovery; classifier and terminal-state regressions pass in the 24-test finalization suite. | **UNIT CONTRACT TEST** | Not integrated with the A2/DBOS runner; CP83 direct runner intentionally leaves its task RUNNING. |

CP83 supports one A2/DBOS composition hypothesis, not a harness ranking. It proves safe no-duplicate behavior for the tested quarantine/restart path while also documenting failed continuation. Current source counts show the HADES authority and API code remains required, while the only identified removed gate is a test-only 53-line helper; no net maintained-code reduction is established. Historical CP81 memory scores and CP82 failures are unchanged. See [CP83 report](CP83_PYDANTIC_DBOS_WORKSPACE_RECOVERY.md), [machine-readable result](../experiment/results/cp83-pydantic-dbos-workspace-20261014.json), and [reuse-first assessment](REUSE_FIRST_TECHNOLOGY_ASSESSMENT.md).

## CP84 — Pydantic AI + DBOS through trusted HADES finalization

| Area | Evidence | Classification | Remaining gap |
|---|---|---|---|
| Candidate tool path | Pydantic AI `Agent` used the shared candidate tool schemas and `gateway_call`; deterministic peer invoked one `workspace_exec` and one explicit completion checkpoint. | **CONTRACT TEST** | Does not run the public candidate HTTP Handler or Harness `Shell`; no live model comparison. |
| Recovery windows | Across 3/3 clean repetitions, worker died after gateway confirmation and again after DBOS workflow completion but before HADES finalization. Repeated process resume retrieved the original workflow result and completed via `finalize_turn`. | **CONTRACT TEST** | SQLite DBOS history was in runner tmpfs; full container/host restart and persistent-store recovery are untested. |
| HADES task/effect integrity | Each task reached trusted `COMPLETED`; same original effect ID remained `CONFIRMED`; independent read saw exactly one marker; repeated retrieval added zero generations/effects; no memory mutation. | **CONTRACT TEST** | Semantic correctness came from a deterministic peer. Arbitrary-shell outcome reconciliation remains unavailable. |
| Preserved driver failures | One run stopped on a `RunUsage` property/method error before finalization; one run completed the task but the test driver lost its output to a parser bug. Both effects and marker states were independently checked and cleaned. | **TEST-DRIVER FAILURES**, not candidate scores | Kept separate from the 3 clean passes in the JSONL. |
| Reuse impact | DBOS recovery composes with HADES task/effect authority and trusted finalizer; no second ledger was introduced. | **CONTRACT TEST** | No net runtime code reduction shown; DBOS history privacy, payload codec, persistent DB, retry/cancellation and lifecycle integration need qualification. |

CP84 is a separate deterministic Pydantic AI + DBOS integration candidate, not an A/B/C score. It improves the evidence that a confirmed effect and final response can survive process interruption while HADES independently decides task completion. See [CP84 report](CP84_DBOS_CANDIDATE_FINALIZATION.md) and [sanitized trial records](../experiment/results/cp84-dbos-candidate-finalization-20261014.jsonl). ADR-010 remains NOT READY.

## CP85 — resource-limited held-out memory screen

| Area | Evidence | Classification | Remaining gap |
|---|---|---|---|
| Isolation | New unique project, internal-only networks, no host ports or privileged services; candidate resolved only gateway/model aliases. Shared CP75/CP80 services were not contacted or restarted. | **OPERATIONAL EVIDENCE** | Inference still consumed shared host CPU/RAM; stopped when load approached capacity. |
| A/C held-out structured correction | One identical lab-report JSON correction each. Both timed out before tool selection; A had three canceled upstream requests and C one. Offline inspection of the exact A image found `openai==3.29.0` with client `max_retries=2`, strongly consistent with three A HTTP attempts; per-attempt IDs were absent, so causality is not proven. | **LIVE CPU SCREEN, RESOURCE-LIMITED** plus **PINNED-RUNTIME INSPECTION** | One trial per candidate; no CAS operation or fresh-context recall occurred. This reveals a likely transport retry-budget asymmetry, not a memory-selection result or candidate ranking. Future matched revisions should disable provider retries or durably count each attempt. |
| Canonical state and lifecycle | Independent reads showed original revision-1 JSON unchanged, zero effects, and both tasks `FAILED`. | **INDEPENDENT FIXTURE VERIFICATION** | No correction success to restart/retrieve; prior CP81 observations remain the controlling memory evidence. |
| Resource/cleanup | Four-CPU cap led to 50-second provider timeout; host load reached 19.64/20. CP85 containers, networks, and volumes were removed; 14 CP75/CP80 containers remained. | **OPERATIONAL EVIDENCE** | Five project-tagged images remain for cleanup-lead review; no pruning. No higher-cap rerun during this session. |

CP85 does not alter CP81's A/C outcomes. See [CP85 report](CP85_MEMORY_RETEST_REPORT.md) and [sanitized per-trial records](../experiment/results/cp85-memory-retest-20261014.jsonl).

## CP86 — provider transport retry accounting

Offline inspection and a strict mock transport using CP85's pinned candidate image reproduced the OpenAI SDK default of two retries (three HTTP attempts). The candidate's `Agent(retries=1)` setting is separate from provider transport retries. Candidate A now configures `max_retries=0`; an offline regression confirms the provider setting, and the real adapter identity test still passes. This is a new unscored source revision and a budget-accounting correction, not a CP85 rescore or a model-performance result. See [CP86 report](CP86_PROVIDER_RETRY_ACCOUNTING.md).

## CP87 — workspace command restart boundary

| Area | Evidence | Classification | Remaining gap |
|---|---|---|---|
| Gateway replay | Existing task/effect ledger returns the saved result for an exact confirmed task/operation identity, rejects a changed request under that identity, and quarantines unresolved outcomes before any new dispatch. | **SOURCE REVIEW + GATEWAY CONTRACT TESTS** | Same-command requests with distinct call identities are distinct operations; generic shell has no canonical reconciliation. |
| A2 identity persistence | Pinned Harness StepPersistence retains an interrupted Shell call identity; the test-only resume gate permits absent pre-dispatch or confirmed original calls and blocks uncertain effects/WAITING state. Both isolated offline tests passed in the cached A2 image. | **CONTRACT TEST** | Resume gate is not integrated with scored A/C runtime. Default Harness continuation may omit the interrupted call; caller must inspect unresolved effects first. |
| A/C | Both adapters forward provider tool-call IDs to the gateway. | **ADAPTER CONTRACT** | Persistent history/identity and cross-process continuation remain unqualified; a new identity could create a new effect. |
| Hermes | MCP workspace route lacks operation identity and fails closed. | **SOURCE REVIEW** | Identity-bearing MCP integration and recovery remain unqualified. |

No safe generic fix was added. Deduplicating by command text would collapse legitimate repeated commands, while stable IDs alone cannot reconcile arbitrary shell effects. See [CP87 boundary review](CP87_WORKSPACE_REPLAY_BOUNDARY.md).

CP88 adds a fail-closed guard to the stateless shared candidate API: a task with a confirmed workspace command is parked in `WAITING` for operator review instead of being resumed from caller-supplied messages that could generate a new call identity. Missing effect snapshots also park. The offline route regression and database-backed integration passed exact-SHA CI at `33ab8587f43272f8bc482c6ccfa92ab1457ba0f9` ([run 38607008722](https://github.com/p0rkm4th/hades-v3/actions/runs/38607008722)). Independent database checks confirmed one unchanged effect, durable `WAITING`, unchanged memory rows, and zero model requests. This blocks sequential replay in the identified lost-response window but leaves completion/recovery manual. Concurrent `/api/turn` requests are not serialized and remain an unqualified duplicate-risk boundary; no exactly-once shell guarantee is claimed. See [CP88](CP88_STATELESS_WORKSPACE_RESUME_GUARD.md).

## CP89 — matched CPU repeat screen under the current adapter revision

| Candidate | Profile | Scenario | Outcome | Independent state | Classification |
|---|---:|---|---|---|---|
| A / Pydantic AI | 4 CPU | Structured correction | HTTP 502 provider timeout before tool selection | Task `FAILED`; revision 1 unchanged; zero effects | Live CPU experiment; resource-limited |
| C / lean | 4 CPU | Same structured correction | HTTP 502 provider timeout before tool selection | Task `FAILED`; revision 1 unchanged; zero effects | Matched live CPU experiment; resource-limited |
| A / Pydantic AI | 8 CPU | Structured correction | HTTP 502 provider timeout before tool selection | Task `FAILED`; revision 1 unchanged; zero effects | New matched profile; resource-limited |
| C / lean | 8 CPU | Same structured correction | HTTP 502 provider timeout before tool selection | Task `FAILED`; revision 1 unchanged; zero effects | Matched live CPU experiment; resource-limited |
| A / Pydantic AI | 4 CPU | Scalar correction | HTTP 502 provider timeout before tool selection | Task `FAILED`; revision 1 unchanged; zero effects | Single live CPU screen |

The source revision was `33ab8587f43272f8bc482c6ccfa92ab1457ba0f9`; A used Pydantic AI 2.55.0/OpenAI 3.29.0 with transport retries disabled. Both model profiles used Qwen3-8B Q4_K_M, 40,960 context, temperature 0, 1,024 output-token ceiling, and 50-second request timeout. The structured case repeats CP81's existing `weekly_structured` wording; this was not a held-out prompt. Each candidate attempt made one upstream request and returned no successful generation. These results support a provider/runtime timeout classification; they do not score memory selection or CAS behavior. CP81's prior scalar/list outcomes and CP85's held-out lab-report case remain unchanged. No successful CP89 mutation means no CP89 fresh-context recall. See [CP89 report](CP89_MEMORY_SCREEN_REPORT.md) and [sanitized records](../experiment/results/cp89-memory-screen-20261014.jsonl).

The keyed CAS gateway integration passed: same-task exact retry returned the original effect; changed retry, stale revision, wrong user, and wrong domain rejected without canonical mutation. The candidate finalization suite passed 24/24 offline tests, including false completion claims and provider-failure behavior. CP89 does not establish candidate memory qualification because all current model attempts timed out before tools.
