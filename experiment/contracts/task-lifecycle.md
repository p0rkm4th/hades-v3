# Candidate task lifecycle contract

The candidate API reports a model turn separately from the canonical task state. An HTTP 200 or nonempty model answer alone never completes a task.

## Completion

The candidate's `task_checkpoint(COMPLETED, ...)` is a completion claim, held until the model turn returns a nonempty final response. The orchestrator then submits the canonical completion to the gateway with evidence captured from actual tool calls. The gateway accepts `COMPLETED` only when:

- the final response is nonempty;
- the completion claim has at least one completed step and an empty pending list;
- a read-only task has successful read-tool evidence, or an effect task has explicit completion and current verification evidence; and
- every recorded task effect is `CONFIRMED` (write evidence must include read-back where that tool supports it).

The gateway rejects candidate-originated completion requests unless the request carries the separate internal orchestrator credential; a user-scoped fixture token and a fabricated body marker alone are insufficient. Candidate tools cannot supply that credential. Set a unique `ORCHESTRATOR_SECRET` in the ignored `experiment/.env` before starting Compose; do not commit it. A verified tool write no longer completes its task on its own; the model turn must finish and the orchestrator must finalize it.

## Other outcomes

- An explicit checkpoint with pending work remains `RUNNING` so it can be resumed. A later resume keeps the existing checkpoint and requires fresh evidence before completion.
- Approval-pending and unresolved/uncertain effects become `WAITING`. Candidate turns cannot move a waiting task to another state. An uncertain effect is never retried as part of finalization.
- A caught model/provider/tool error without an uncertain effect becomes `FAILED`. If an effect may have occurred, it remains `WAITING` for reconciliation. Existing `WAITING` and terminal states are preserved.
- A caller may resume a nonterminal task explicitly. `WAITING` can return to `RUNNING` only through the orchestrator and only when the checkpoint does not record pending approval or an uncertain effect. Terminal tasks cannot be resumed.
- A completed response is not semantic correctness proof. Candidate answer correctness, task outcome, and verified tool effects remain separate evaluation signals.

The gateway and candidate API share the pure rules in `task_lifecycle.py`. The regression suite covers read completion, confirmed writes, partial work, tool errors, interrupted turns, approval and uncertain outcomes, resumed tasks, state preservation, and gateway rejection of completion without orchestrator evidence.
