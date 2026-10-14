# Candidate task lifecycle contract

The candidate API reports a model turn separately from the canonical task state. An HTTP 200 or nonempty model answer alone never completes a task.

## Completion

An ordinary task's candidate `task_checkpoint(COMPLETED, ...)` remains a claim, held until the model turn returns a nonempty final response. Semantic answer correctness is evaluated separately. The orchestrator submits completion to the gateway with evidence captured from actual tool calls. The gateway accepts ordinary completion only when:

- the final response is nonempty;
- the completion claim has at least one completed step and an empty pending list;
- a read-only task has successful read-tool evidence, or an effect task has explicit completion and current verification evidence; and
- every recorded task effect is `CONFIRMED` (write evidence must include read-back where that tool supports it).

The gateway rejects candidate-originated completion requests unless the request carries the separate internal orchestrator credential; a user-scoped fixture token and a fabricated body marker alone are insufficient. Candidate tools cannot supply that credential. Set a unique `ORCHESTRATOR_SECRET` in the ignored `experiment/.env` before starting Compose; do not commit it. A verified tool write without independently registered success criteria requires an explicit model claim or remains in a recoverable review state.

### Trusted bounded success criteria

A trusted task ingress may attach an immutable, typed completion contract at task creation. CP73 supports only the narrow `external_commitment_set` contract: a bounded list of exact target IDs and operation details. The gateway computes and stores each canonical effect digest in the existing task checkpoint. The model cannot create or change this field through `task_start` or `task_checkpoint`; registering it requires the orchestrator credential.

For this contract, a final response without a model-generated completion checkpoint may complete the task only after the gateway independently proves that:

- every contract item has exactly one matching persisted effect and there are no extra effects;
- task, user, and domain identity match on the task, effect, and consumed approval;
- target, requested details, and digest exactly match the immutable contract and approval, and approval consumption occurred before its expiry;
- the effect ID is `CONFIRMED` and a fresh canonical target query reports `ACCEPTED` for that exact effect and target; and
- no model/provider error, provider diagnostic response, or candidate-reported pending step exists, and a nonempty final response was generated.

The gateway writes that response into the canonical task checkpoint atomically with `COMPLETED`, marked `PERSISTED_PENDING_DELIVERY`. If the HTTP reply is lost, an authenticated task read returns the persisted response; this is not a claim that notification was delivered. Semantic answer quality is still scored independently. A compound objective must register every required operation; partial effects, missing records, wrong identities, stale/uncertain effects, or unavailable canonical state are rejected.

This does not establish general success criteria for arbitrary free-text tasks. Those keep the explicit claim and evidence path. A missing model claim after confirmed work now becomes `WAITING` for completion review rather than terminal `FAILED`; a confirmed effect followed by provider failure waits for response recovery. Rejected/failed effects remain failures, and uncertain operations remain blocked for reconciliation.

## Other outcomes

- An explicit checkpoint with pending work remains `RUNNING` so it can be resumed. A later resume keeps the existing checkpoint and requires fresh evidence before completion.
- Approval-pending and unresolved/uncertain effects become `WAITING`. Candidate turns cannot move a waiting task to another state. An uncertain effect is never retried as part of finalization.
- Agent-mediated `memory_write` and `memory_correct` calls include the active task ID. The gateway locks that authenticated running task, records a `MEMORY_MUTATION` in the existing effect ledger, applies the canonical row change, and marks the effect `CONFIRMED` in one PostgreSQL transaction. An exact replay returns the same effect; a changed replay for the same task/key is rejected. Finalization requires the persisted effect ID to match the tool evidence and task/user/domain, the effect request/result to match the key/value, and the current canonical memory row to match the recorded result. This makes an HTTP 200 alone insufficient proof. Calls without a task ID remain available for explicit fixture/setup writes but have no task-linked effect and cannot prove completion.
- A successful memory mutation with missing task-linked effect evidence remains `WAITING`. A known rejected mutation (for example, a correction with no matching current value) has no effect and fails the task; it is not left `WAITING` as if an effect might have occurred. Provider failure after a confirmed mutation preserves the effect and waits for final-response recovery.
- A caught model/provider/tool error without an uncertain effect becomes `FAILED`. If an effect may have occurred, it remains `WAITING` for reconciliation. Existing `WAITING` and terminal states are preserved.
- A caller may resume a nonterminal task explicitly. `WAITING` can return to `RUNNING` only through the orchestrator and only when the checkpoint does not record pending approval or an uncertain effect. Terminal tasks cannot be resumed.
- New workspace operations require a `RUNNING` task at the gateway. `WAITING` blocks new dispatch regardless of whether the cause is operator review, pending approval, response recovery, or uncertainty. Exact retries of already confirmed operation identities may return the persisted result without dispatch; unresolved effects remain quarantined. The candidate API's resume guard is not the sole enforcement point.
- A completed response is not semantic correctness proof. Candidate answer correctness, task outcome, and verified tool effects remain separate evaluation signals.

The gateway and candidate API share the pure rules in `task_lifecycle.py`. Ordinary read/write evidence is assembled by the gateway-call proxy from actual gateway HTTP responses; a candidate completion claim without that tool evidence is rejected. Hermes tool records are written by the proxy and consumed by the orchestrator, not asserted by the model response. For a registered bounded contract, restart recovery uses the durable task contract, effect, approval, and canonical target records rather than an in-memory model-turn trace. The regression suite covers read completion, evidence-driven bounded completion, task/effect/approval identity, partial work, provider failure, unledgered memory writes, uncertain outcomes, resumed tasks, terminal-state immutability, and gateway rejection of unauthorized completion.
