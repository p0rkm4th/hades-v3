# Reuse-first technology assessment

**Assessment date:** 2026-10-14
**Source baseline:** HADES v3 CP77, `88d1017e7a27b87324ead831dcf4dd61f9720c75`
**Authority:** frozen PRD and Bounded Operator architecture
**Status:** research synthesis; recommendations are hypotheses until integrated and independently tested

## Executive assessment

The current prototype does not need to own a general agent capability framework, model protocol stack, shell/file toolkit, durable workflow engine, or telemetry format. Mature packages now cover much of that ground. HADES still owns the parts that determine authority and truth: authenticated identity/domain, grants and approval, the task/effect ledger, effect reconciliation, trusted completion criteria, domain boundaries, and user-visible task state. These responsibilities must not move into a framework's parallel authority store.

The strongest reuse direction is a separately pinned Pydantic AI Harness candidate plus one durable-execution integration spike, while preserving current A/B/C scores. DBOS is the smallest initial durable-engine spike; Temporal is the strongest comparison candidate but brings a separately operated service and stricter workflow determinism. Do not install both as permanent services. Hindsight is already present in the broader HADES environment; evaluate it as an existing memory capability rather than building a second memory engine, but retain the v3 scoped relational memory contract until its record identity, versioning, domain isolation, and task-linked mutation guarantees are proven.

## Evidence labels and limits

- **RESEARCH:** official upstream documentation/release metadata reviewed on the assessment date.
- **HADES evidence:** behavior in this repository's tests or recorded trials.
- **Hypothesis:** a proposed bounded integration; not a qualification result.
- “Supported” means the upstream project documents an interface. It does not establish HADES isolation, correctness, performance, or safety.

## Component inventory and disposition

| Function / current source | Owner and dependencies | Security significance | Disposition | Rationale / next proof |
|---|---|---|---|---|
| Agent/model loop: `experiment/candidates/api.py` | HADES; Pydantic AI, OpenAI-compatible provider | Receives scoped task and tools; must not grant authority | **SIMPLIFY / REPLACE CANDIDATE** | Keep as historical A. Evaluate Harness composition as distinct A2; gateway remains the grant boundary. |
| Provider protocol: `inference_adapter.py`, `ollama_protocol.py` | HADES adapter; OpenAI-compatible candidates and Ollama | Destination, method, payload, generation ceilings | **KEEP**, narrow | HADES-specific fixed upstream and allowlist are necessary. Protocol conversion should remain standards-compatible and covered by strict-peer tests. |
| Hermes startup/proxy: `hermes_start.py`, `mcp_proxy.py` | HADES integration around upstream Hermes | Maps capabilities into gateway; restricts tools/destinations | **SIMPLIFY** | Reassess reduced profile against supported upstream MCP/tool/session features; avoid Hermes source forks. |
| Candidate C lean loop: `api.py` candidate `lean` branch | HADES experimental reference | Tool validation and retries can affect behavior | **KEEP as baseline; DELETE candidate later** | Valuable minimal comparator only. No presumption it should become a second general runtime. Measure its code and maintenance burden after A2. |
| Tool contracts / MCP: `experiment/contracts/tools.json`, gateway routes, proxy | HADES contracts; MCP SDK and gateway | Capability exposure and argument validation | **KEEP contract; REUSE SDK transport** | One HADES tool/grant boundary; standard MCP SDK should replace only protocol plumbing, never authority. Existing Hermes path has CP69 strict protocol evidence. |
| Task/effect lifecycle: `task_lifecycle.py`, `gateway.py`, PostgreSQL tables | HADES trusted control plane | Core authority, identity binding, durable outcome | **KEEP** | Frozen architecture requires one authoritative task/effect state. Workflow engines may drive execution but cannot shadow this ledger. |
| Durable resume/checkpoints: candidate and CP72/73/74 orchestration | HADES experiment; PostgreSQL and framework options | Prevent replay, preserve approvals and uncertainty | **REPLACE CANDIDATE** | Evaluate Pydantic StepPersistence and DBOS/Temporal while keeping effect IDs/reconciliation in HADES. Framework replay is not exactly-once for external calls. |
| Commitment simulator and reconciliation: `commitment_simulator.py`, gateway | HADES synthetic target | Tests approval, dispatch, unknown outcome and canonical evidence | **KEEP test-only** | HADES-specific independent oracle; use standard fault proxying to reduce custom network fault scripts. |
| Scoped memory/search/correction: gateway `scoped_memory` | HADES experiment; PostgreSQL JSONB/FTS | User/domain isolation and authorized mutation | **KEEP contract; simplify search** | CP75 replaced the legacy fuzzy mutation with keyed/revision CAS. Preserve its atomic task-linked effect. Consider `websearch_to_tsquery` or `plainto_tsquery` for discovery; fuzzy match never authorizes mutation. |
| Existing Hindsight service / MCP | Infrastructure-owned; Hindsight and PostgreSQL | Persistent cross-session memory; privacy/domain scope | **REUSE candidate** | HADES-infra records an existing Hindsight-backed v2 capability. No evidence yet that it supplies stable keyed CAS or task-linked durable effects. Do not touch deployed service. |
| Shell/workspace runner: `workspace_runner.py`, workspace service | HADES isolated runner; containers, Git, shell | Actual process/file/network isolation | **REPLACE CANDIDATE** | Compare Pydantic Harness `Coder`/`Shell` over an existing sandbox. Tool allowlists/root checks are not a sandbox; preserve OS/container boundary. |
| Fixture and fault test scripts | HADES tests; Compose, pytest | Reproducibility and isolation | **SIMPLIFY** | Consolidate only repeated patterns into pytest fixtures. Testcontainers/Toxiproxy are candidates where they reduce setup; no broad test platform. |
| Observability | HADES JSONL and logs; Pydantic/OpenTelemetry | Correlation; raw content can leak | **SIMPLIFY / REUSE** | Adopt GenAI span conventions and correlation IDs with content capture disabled by default. Existing sanitized JSONL remains evidence source until parity is proven. |
| Scheduling/background work | Not a production v3 subsystem | Could create a second scheduler/control plane | **UNKNOWN / DEFER** | Framework/Hermes scheduling is not needed for current harness decision. Do not add a scheduler before requirements demand one. |
| GPU trial firewall, preflight scripts | HADES experiment and host-owned policy | Host-level network enforcement | **KEEP test-specific** | No further live GPU trial authorized here. Use only documented, separately approved host mechanisms. |

## Technology comparison

| Technology | Relevant upstream capability (research) | HADES fit / risk | Evidence and disposition |
|---|---|---|---|
| Pydantic AI core | Typed tools, provider abstraction, MCP, streaming, retries, OTel and durable execution integrations | Good current A foundation; current v3 lock is behind current Harness-linked core. Core run state is not the HADES effect authority. | A has substantial CP67–74 behavior evidence. **Keep baseline**, update only in separately pinned candidate. |
| Pydantic AI Harness | Coder, Shell, FileSystem, RepoContext, tool search, planning/subagents, context support, StepPersistence, stores, OTel; durable execution via multiple engines | Potentially replaces much of custom shell/file/tool orchestration. Shell is unrestricted by default and not a sandbox; FileSystem path checks also are not OS isolation. 0.x API has minor-version change risk. | **High-value A2 hypothesis.** Pin `pydantic-ai-harness==0.56.0` with its required `pydantic-ai-slim==2.56.0`; test inside existing disposable workspace boundary. Not a replacement of scored A until fresh qualification. |
| Hermes Agent | Upstream agent runtime with shell/computer tools, MCP, session state, memory, background tasks, scheduling and subagents | Broad capability set; reduced profile may omit strengths. Hermes session state is not automatically the HADES task/effect ledger. Provider/context needs remain material. | HADES B is pinned to a historical upstream commit. Inspect exact upstream extension support and compare against current release separately. Do not call its 40,960-token CPU result equivalent to A/C. |
| Lean loop (C) | Minimal custom model/tool loop | Small moving parts and direct control; HADES currently carries provider protocol, tool history, retry, context, persistence, recovery, workspace, and test code around it. | Retain as experimental control. **Delete candidate** if A2 plus trusted HADES boundary offers equal/better outcomes with lower maintenance burden. |
| DBOS | PostgreSQL-backed durable workflows; workflow IDs, completed-step replay, transactions, configurable retries | Natural fit with existing relational model and Pydantic AI integration. Steps can retry at least once; arbitrary external effects still need idempotency/reconciliation. Separate DBOS metadata must not become task/effect truth. | **Spike 1 hypothesis.** Use disposable schema/database and explicit mapping from HADES task ID; wrap only safe/reconcilable activities. No production service. |
| Temporal | Durable workflow history, deterministic replay, activities, signals/queries/timers | Mature recovery semantics, but a separate service and worker operations add complexity. Activities retry; non-idempotent external work must remain HADES-mediated. Workflow code must be deterministic. | Contingency only if DBOS leaves a decision-relevant gap. Avoid multiple engine deployments. |
| Restate | Durable services/objects and workflow execution; Pydantic integration exists | Promising option but would add another engine and operational model. | Research alternative; not selected for current two-spike cap. Reconsider only if a specific DBOS/Temporal deficiency appears. |
| Prefect | Pydantic AI durable execution integration and workflow/task model | Broad orchestration; likely more operational features than current local prototype requires. | Documented alternative; not a current spike. |
| PostgreSQL FTS + `pg_trgm` | Built-in normalized full-text query APIs, ranking, trigram similarity/indexing | Suitable for candidate discovery, not authorization. CP74 used hand-built OR tokens plus exact JSONB equality and had no stable key in the agent request; CP75 replaced this mutation contract. | **Reuse existing PostgreSQL.** Evaluate query parsers for discovery; stable scoped key plus revision/current-value CAS remains mutation authority. |
| Hindsight | Existing HADES-infra memory service and MCP capability | May provide persistent contextual recall; not known to provide HADES effect identity, compare-and-swap, or authoritative task completion. | **Reuse candidate**, read-only evaluation first. Keep one canonical HADES mutation contract and domain boundary. |
| MCP Python SDK | Standard client/server transport, tools/resources/prompts, local in-memory testing | Replaces hand-written MCP transport, not HADES gateway policy. SDK v2 has protocol/API migration differences from v1. | Pin current SDK only in separate integration; retain v1 where current Hermes compatibility requires it until explicitly migrated. |
| Testcontainers | Disposable service containers and integration-test fixtures | Could reduce hand-managed Compose/test setup, but current Compose already provides isolated fixtures. Docker-host resource ownership remains critical. | Adopt only for a measured simplification in one bounded test family. |
| Toxiproxy | TCP fault injection without host firewall changes | Suitable for reconciliation/acknowledgment failure windows when isolated on a test-only network. Proxy API must not be exposed. | **Candidate reuse** for future fault cases; compare against existing injections before adding. |
| OpenTelemetry GenAI semantic conventions | Common model/tool spans and usage attributes | Can improve cross-runtime diagnosis; prompt/tool argument/result attributes can contain sensitive content. | Reuse API conventions; default to no content capture, add only safe task/effect correlation and aggregates. |

## CP74 diagnosis and CP75 outcome

CP74's HTTP 404 mutation failures were initially ambiguous because the request arguments were not retained. CP75's isolated investigation determined the cause: both candidates found the intended row but represented its existing structured JSON value in a different shape, so exact canonical JSON equality failed. No canonical memory mutation occurred. This supports a contract correction, not prompt tuning or weaker matching.

CP75 replaced mutation-by-natural-language-query with search/read returning a stable `memory_key` and revision, followed by scoped compare-and-swap. Gateway regressions verified existing-schema migration, fresh fixtures, stale revision rejection, cross-user isolation, exact retry, changed retry, active-task requirement, and atomic memory/effect rollback. The durable effect is checked independently against canonical state and task/user/domain identity.

The interface repair did not qualify end-to-end candidate memory work. A and C each performed the scalar and list corrections correctly in one observation per case, but stayed `WAITING` because they omitted the task checkpoint. Both made no tool call on the structured-value correction and falsely claimed success; canonical state stayed unchanged. Fresh-context scalar recall after restarting gateway/API passed for each, while C's list recall failed to select a tool. CP74's original failures remain historical failures; CP75's trials are also not repeated qualification. See `docs/CP75_MEMORY_CAS_REPORT.md` and its sanitized JSONL records.

The remaining question is agent behavior and lifecycle interaction under the CAS contract, not a need for another memory authority. PostgreSQL full-text search and `pg_trgm` remain suitable discovery/ranking options only; a stable key plus current revision/value must authorize mutation. Fuzzy similarity never authorizes a write.

## Build-versus-reuse justification

| Problem | Existing solution evaluated | HADES-specific remainder | New custom subsystem? |
|---|---|---|---|
| Agent tools, shell, files, planning, context | Pydantic AI Harness; Hermes | Select allowed capabilities, supply a real isolated workspace, bind task identity and tools | No. Compose an upstream runtime. |
| Durable run continuation | Pydantic integrations, DBOS, Temporal, Restate, Prefect | Map workflow/run identity to one HADES task and route effects through HADES gateway; reconcile non-idempotent targets | No workflow engine. Spike max two. |
| Authority and effects | HADES gateway/ledger | Identity/domain/grants, effect identity, approval, independent target verification, completion criteria | Yes, this is frozen HADES-specific authority. Keep one. |
| Memory discovery/mutation | PostgreSQL FTS/pg_trgm; existing Hindsight | Domain-scoped candidate discovery plus durable task-linked CAS mutation and provenance | No second memory database. Narrow existing gateway contract after CP74 diagnosis. |
| MCP integration | Official MCP SDK and upstream Hermes/Pydantic integrations | Tool allowlist and gateway-authenticated identity | No bespoke protocol implementation beyond fixed authorization adapter. |
| Fault injection | Toxiproxy, pytest, Compose/Testcontainers | Test scenario and independent oracle | Reuse standard fault tools; do not build a test orchestration platform. |
| Trace/metrics | OpenTelemetry GenAI conventions and framework instrumentation | Safe correlation IDs, retention and privacy policy | No bespoke generic observability stack. |

## Candidate component reduction plan

1. Preserve A/B/C source and all existing scored evidence.
2. Create a separately labeled A2 proof of concept using the pinned current Pydantic AI Harness dependency; evaluate shell/repo work only inside existing disposable workspace controls.
3. Use official MCP SDK test/server utilities for any new MCP contract tests; avoid replacing a working protocol path without parity tests.
4. After CP75 diagnosis, compare current correction tool with keyed/versioned CAS using the same task fixtures and oracle. Remove the old mutation entry point only if parity and safety regressions pass.
5. Run at most two durable engine spikes (DBOS first; Temporal only if its contrast can change the decision). HADES PostgreSQL task/effect rows remain the source of truth; engine history is execution machinery only.
6. Measure custom code/dependency reduction before deleting Candidate C or test runners. Keep it only as a minimal comparator if it no longer offers a decision-relevant advantage.
7. Adopt OpenTelemetry only with privacy-safe spans and demonstrated correlation parity with the existing sanitized records.

## Decision-readiness table

| Decision evidence | Status | What remains / decision relevance |
|---|---|---|
| Shared model/tool protocol and offline lifecycle | Partial positive; CP69 strict offline passed; CP68/67 GPU negative evidence preserved | Real-model/provider qualification after separate authorization only; not in this campaign |
| Candidate memory correction + restart + fresh recall | Not qualified; CP74 correction failed for A/C, one observation each | CP75 exact diagnosis, then at least three held-out successful/negative cases with restart and fresh context |
| Durable interrupted effect/recovery | Strong narrow A/C evidence CP73; important windows remain | Add engine spike only if it reduces custom recovery while retaining HADES effect authority |
| Compound operations and exact outcomes | Mixed, prompt/profile-sensitive evidence | Held-out tasks, partial effects, after-state oracle, retries and restart |
| General-purpose shell/Git agency | Narrow prior family evidence | A2 comparison, restart, independent test/commit/worktree verification |
| Authorization/adversarial resistance | Partial family 7/8 synthetic evidence | Fresh held-out prompt injection, expired/forged approvals, cross-domain and replay cases |
| Hermes equivalent model comparison | Not available on CPU context | Keep contract/runtime results separate; GPU requires new owner authorization and is out of scope |
| Current HADES v2 living control | Source and public CI evidence only; runtime/acceptance freshness uncertain | Obtain current read-only snapshot through existing handoff; no interference |
| Owner usability | Missing | Owner acceptance after representative workflows, with no production deployment assumed |

The smallest decision-changing set is: (1) repeated, safe memory correction and fresh retrieval; (2) held-out compound/recovery plus protected-action cases for A/C, and strict-peer contract evidence for B; (3) one A2 Harness integration and one durable-engine spike that materially reduces code without splitting authority; (4) current independent v2 runtime evidence and owner usability. No current evidence supports ratifying ADR-010.

## CP76 verified upstream snapshot

This section records the source state checked for CP76. Release numbers are a snapshot, not a recommendation to upgrade an already scored candidate. The current experiment remains pinned to its historical dependency/runtime revisions; new versions require a separately labeled candidate and fresh qualification.

| Component | Verified snapshot / license | Documented capability and boundary | CP76 disposition |
|---|---|---|---|
| Pydantic AI Harness | `pydantic-ai-harness==0.56.0`, MIT; package metadata requires matching `pydantic-ai-slim==2.56.0` (current scored A is `pydantic-ai-slim==2.55.0`) | Current Harness docs cover Coder, Shell, FileSystem, RepoContext, planning/subagents, context management, MCP, persistence and durable-engine integrations. Shell executes commands and is not a sandbox; filesystem-root checks constrain that tool only. Harness is a capability library, not an independent HADES grant/effect authority. The 0.x API and package surface can change. | A2 is warranted as a distinct bounded candidate. Test inside an already isolated workspace; do not give it host privileges or replace historical A scores. |
| Hermes Agent | v0.22.0 release dated 2026-10-13, MIT; HADES B remains pinned to upstream commit `e4d86423856350825a3a0dc4f52aed89759e11bd` | Current release describes MCP/connectors, local model support, persistent sessions, memory-provider plugins, shell/browser computer use, sandbox backends, background subagents and stable SemVer channels. These are upstream release claims, not HADES runtime evidence. Current Hermes behavior cannot be imputed to the older reduced B. Its session/task data is not the HADES effect ledger. | Keep historical B evidence separate. Inspect supported current extensions/configuration as a new candidate only if the shared-context and architecture gates can be met. |
| DBOS Transact | `dbos==3.2.0`, MIT, Python >=3.10; PostgreSQL-backed system database | Workflows resume from last completed step; completed steps are not replayed, while an interrupted step may run again. DB transactions are exactly-once in DBOS's stated model; external activities remain at-least-once and require idempotency/reconciliation. Pydantic integration requires explicit DBOS workflow context; custom tools are not automatically wrapped. Workflow inputs/results are persisted, so data minimization and serialization matter. | Best first durable spike because HADES already uses PostgreSQL. Use only disposable DBOS metadata and preserve HADES task/effect authority. No external effect should be dispatched from a retryable activity without HADES idempotency/reconciliation. |
| Temporal Python SDK | `temporalio==1.34.0`, MIT; server/worker operation is a separate deployment concern | Durable event history, replay, activities, signals, timers and retries are mature. Workflow code must be deterministic; external operations belong in activities and still need idempotency. The extra Temporal service and operational model are material for this local prototype. | Research comparison only for now. Run a Temporal spike only if DBOS reveals a decision-relevant limit that Temporal could resolve; avoid operating two engines. |
| Prefect | `prefect==3.8.8` observed; Apache-2.0; Pydantic AI documents integration | General workflow orchestration with durable task/flow state, but a broader orchestration/control plane than the current agent-resume experiment needs. It does not replace HADES's grant/effect evidence. | Defer; no identified advantage over first DBOS spike for this narrow question. |
| Restate | Official Python SDK and Pydantic AI integration documented; exact release not pinned in this assessment | Durable service/workflow model is a viable alternative; adds another runtime/operational model. | Keep as a documented alternative, not a selected spike absent a concrete DBOS gap. |
| Hindsight | v1.0.0, MIT for core project; API package documents Apache-2.0; existing HADES-infra deployment is separate | Retain/recall/reflect and temporal/semantic/keyword/entity retrieval are supported. Banks/tags provide scoping mechanisms. Documentation reviewed does not establish the HADES requirements for stable-key revision CAS, task-linked effect identity, atomic commit with HADES task state, or independent completion proof. | Reuse for contextual recall evaluation; retain the CP75 canonical write/effect path. Do not migrate or alter the existing service. |
| MCP Python SDK | `mcp==2.3.0`, MIT; official Python SDK | Standard client/server transports and test utilities; protocol SDK does not supply HADES authorization. v2 is a major-version/API boundary relative to prior v1 integrations. | Use for an isolated contract test only if it reduces bespoke transport; preserve the current candidate-specific gateway boundary. |
| Testcontainers Python | v4.15.0, Apache-2.0 | Creates disposable test containers through Docker API. It still uses the host Docker daemon and does not itself guarantee isolation from shared Compose resources. | Do not replace current Compose fixtures wholesale. Evaluate one pytest fixture only when it can run with uniquely owned resources and reduce repeated setup. |
| Toxiproxy | Official Shopify project, MIT | TCP fault injection using a proxy and control API; can inject connection loss/latency without changing host firewall rules. It cannot model application-level commit semantics by itself. | Good candidate for isolated reconciliation-window testing; use only an isolated test network and never expose its control API to candidate containers. |
| OpenTelemetry GenAI conventions | Current OTel semantic-conventions specification; Apache-2.0 project | Common spans/attributes for model and tool calls. Prompt, completion, tool arguments and results can contain sensitive data; conventions do not make those attributes safe to export. | Reuse trace structure with content capture disabled; prove correlation parity before replacing sanitized JSONL evidence. |
| PostgreSQL FTS / `pg_trgm` | Existing PostgreSQL capabilities; PostgreSQL license | FTS query parsers and trigram similarity can improve candidate discovery. Similarity is ranking, not record identity or mutation authority. | Reuse for search only. CP75's exact-key/revision CAS remains mutation authority. |

### Evidence strength and compatibility notes

- Current scored A, B, and C results remain attached to their exact source revisions and settings. Package/release features listed above are **RESEARCH**, not a score for those revisions.
- Pydantic Harness's own Shell and filesystem tools do not provide the isolation required by the Bounded Operator design. Upstream says Shell allowlists are guardrails, not security boundaries; `LocalWorkspaceBackend` runs commands on the agent machine. The `WorkspaceBackend` protocol permits a command-only adapter, with filesystem operations derived through that backend's shell. A2 can therefore plausibly reuse the Harness while routing all commands through HADES `workspace_exec`; this adapter must preserve gateway authentication, task binding, and one durable `WORKSPACE_COMMAND` effect per command.
- The current workspace runner has a fixed timeout and does not accept command-specific environment settings. The Harness adapter must reject or deliberately map those options; no unsupported setting may be silently presented as enforced. Background/persistent shell compatibility remains untested.
- DBOS stores durable workflow history separately from application state. Mapping `workflow_id` to HADES `task_id` is execution correlation only; the gateway remains the only source of task, grant, effect, reconciliation, and completion truth.
- DBOS's workflow ID deduplication does not make an unrecorded external operation exactly-once. A HADES effect ID and target-side idempotency/reconciliation remain necessary around every consequential operation.
- Hermes's latest release materially expands the available product capability set, but it is not the pinned CP69–CP75 runtime. A fresh B profile would require a new immutable revision, dependency/environment capture, and new matched qualification; no 40,960-context CPU run is equivalent to its 64,000 minimum.
- License entries are repository/package metadata for the named component, not a complete transitive dependency or model-weight license review. Any distribution decision needs a lockfile/SBOM and model-specific license check.

## Selected reuse hypotheses (not yet qualified)

1. **A2: Pydantic AI Harness capability composition.** Pin the current Harness/core pair in a separate experiment image. Use one isolated shell/repository task through the existing HADES gateway and existing sandbox. Compare custom code surface, tool correctness, recovery behavior, isolation, runtime footprint, and independently verified repo postconditions against historical A and C. Reject if the Harness requires duplicating authority or its shell cannot be confined by the existing workspace boundary.
2. **DBOS: durable execution adapter.** Use a disposable PostgreSQL system database and a toy workflow with read-only/model steps plus a simulator effect routed through the existing task/effect gateway. Inject worker restart around dispatch/acknowledgment; assert same task/effect IDs, one canonical receive, no repeated authorization bypass, and correct gateway state. Measure retained custom resume code and DBOS deployment/configuration burden. Do not adopt it if it needs a second task/effect authority or cannot make retries safe through HADES.

### CP77 follow-up evidence

The CP77 DBOS subprocess probe passed exact-SHA CI, but it remains a SQLite contract test: DBOS retried a step after restart and a synthetic target's idempotency key kept one canonical effect. It provides no HADES integration evidence. The separately pinned A2 package inspection confirms the upstream workspace extension point is sufficient in shape for an adapter that calls HADES `workspace_exec`; package API fit is **RESEARCH**, not a working integration. Reject direct `LocalWorkspaceBackend` or a Harness shell attached to the agent host because either would bypass the existing workspace/effect boundary. Next proof must run in a unique disposable fixture project and verify real HADES task/effect rows and repository postconditions independently.

These are the only selected spikes for this assessment. Temporal, Restate, Prefect, Testcontainers, and OTel remain alternatives or targeted utilities, not parallel deployments. DBOS should be tested first; the A2 spike can proceed independently and must not alter scored A/B/C.

### CP78 A2 integration evidence

The separate A2 proof now exercises the pinned Harness `Shell` and `FileSystem` with a command-only `WorkspaceBackend` routed through HADES `workspace_exec`. Three deterministic repetitions completed a synthetic read/edit/test task, and an independent oracle verified source, tests, and all task-linked workspace effects. This validates the supported extension point and HADES composition, not model capability or historical Candidate A. The task was deliberately left `RUNNING` to exclude finalization from the experiment.

The combined Shell/FileSystem configuration generated 18 candidate-side workspace commands per small task. This is a concrete efficiency cost and argues for a controlled Shell-only comparison before adopting both capabilities. The adapter also must preserve the gateway's fixed environment and 20-second timeout and has no retry for uncertain command outcomes. `Coder` remains untested. Retain the narrow adapter as a viable composition hypothesis; do not add direct filesystem authority or score A2 as a harness win. See [CP78 report](CP78_A2_HARNESS_WORKSPACE_REPORT.md) and [reproducible probe](../experiment/spikes/a2_gateway_workspace/README.md).

## Updated decision path

CP75 materially improved the trusted memory mutation boundary but did not qualify candidate correction: successful scalar/list mutations still stayed `WAITING`, structured corrections got no tool call, and fresh-context recall was inconsistent. This is a candidate/model interaction gap, not evidence to build another memory engine. Next decision-changing evidence is (a) the two bounded reuse spikes above, (b) repeated held-out memory correction/resume with the established CAS contract and task-finalization behavior, and (c) held-out compound/protected-action tasks. No further live Hypnos generation is authorized. CP71 remains `BLOCKED_EXTERNAL_DEPENDENCY`.

## Primary sources reviewed

Most release/package snapshots were checked 2026-10-13; Pydantic Harness Shell and WorkspaceBackend documentation was rechecked 2026-10-14. Official docs and release/package metadata describe upstream capability; they do not establish HADES qualification. Version metadata should be revalidated before any future pin.

- Pydantic AI Harness overview: https://pydantic.dev/docs/ai/harness/
- Harness Coder: https://pydantic.dev/docs/ai/harness/coder/
- Harness Shell: https://pydantic.dev/docs/ai/harness/shell/
- Harness FileSystem: https://pydantic.dev/docs/ai/harness/filesystem/
- Harness Step Persistence: https://pydantic.dev/docs/ai/harness/step-persistence/
- Pydantic AI durable execution: https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/
- PADES DBOS integration: https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/
- Pydantic AI package metadata: https://pypi.org/project/pydantic-ai-harness/ and https://pypi.org/project/pydantic-ai-slim/
- DBOS workflow guarantees and retry semantics: https://docs.dbos.dev/python/tutorials/workflow-tutorial and https://docs.dbos.dev/python/tutorials/step-tutorial
- DBOS package and source metadata: https://pypi.org/project/dbos/ and https://github.com/dbos-inc/dbos-transact-py
- Temporal workflow definition and activity semantics: https://docs.temporal.io/workflow-definition and https://docs.temporal.io/tasks
- Temporal Python SDK releases: https://github.com/temporalio/sdk-python/releases
- Prefect releases: https://github.com/PrefectHQ/prefect/releases
- Hermes upstream repository and releases: https://github.com/NousResearch/hermes-agent and https://github.com/NousResearch/hermes-agent/releases
- Hermes v0.22.0 release: https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0
- Hindsight upstream/release: https://github.com/vectorize-io/hindsight and https://github.com/vectorize-io/hindsight/releases/tag/v1.0.0
- PostgreSQL text search query controls: https://www.postgresql.org/docs/current/textsearch-controls.html
- PostgreSQL `pg_trgm`: https://www.postgresql.org/docs/current/pgtrgm.html
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP Python SDK package metadata: https://pypi.org/project/mcp/
- Toxiproxy: https://github.com/Shopify/toxiproxy
- Testcontainers Python: https://github.com/testcontainers/testcontainers-python
- Testcontainers Python v4.15.0 release: https://github.com/testcontainers/testcontainers-python/releases/tag/testcontainers-v4.15.0
- OpenTelemetry GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
