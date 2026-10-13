# CP72 durable recovery and reconciliation

**Status: partial recovery qualification; no harness qualifies for ADR-010.**

The v3 source base was `6c86cfc894c40fe9bfd19097cdb4f4e12796d4ee`; the recovery fixes and regression suite in this checkpoint are the changes under review. The model artifact SHA-256 and candidate dependency pins are recorded below. This is CPU/offline evidence only.

CP72 used only isolated HADES v3 disposable services and the approved local CPU
profile. No Hypnos generation, privileged host-network helper, firewall change,
HADES v2 operation, or production service change occurred. CP67–CP71 evidence
remains unchanged.

## Matched CPU trials

Pydantic AI (A) and the lean loop (C) ran the same synthetic appointment task
three times each against the same Qwen3-8B Q4_K_M model, 40,960 context,
llama.cpp image, temperature 0, 1,024-token output limit, 16 CPU threads, and
50-second per-request timeout. The local GGUF SHA-256 matched
`d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
Dependencies were pinned by `requirements.lock.txt` (Pydantic AI 2.55.0,
OpenAI client 3.29.0). The model profile does **not** meet Hermes's 64,000
minimum context.

| Candidate | Authorized tool and simulator result | Final answer | Durable task outcome |
|---|---|---|---|
| Pydantic AI (A) | 3/3 called `commitment_submit`, then `commitment_reconcile`; each independent simulator receive count was exactly 1 and each ledger effect reached `CONFIRMED`. | Useful and consistent with the synthetic canonical target state in all 3. | 0/3 completed. All remained non-complete because the model did not persist the required explicit effectful completion checkpoint; the operator closed them `FAILED` for review. |
| Lean loop (C) | 2/3 called both tools; both effects reached `CONFIRMED` with receive count 1. The remaining attempt timed out before tool selection; it had zero effects and receive count 0. | Useful and consistent in the 2 dispatched attempts; no answer in the timeout. | 0/3 completed. The two dispatched tasks lacked the explicit completion checkpoint; the timeout task failed before any effect. |
| Reduced Hermes (B) | Not run against this CPU model. | Not scored. | Not scored. |

These are matched tool-use trials, not a harness winner comparison. The baseline
records are in `experiment/results/cp72_uncertain_effect_recovery.jsonl`.

## Process interruption and recovery

The restart runner delayed only the synthetic acknowledgement after committing
the simulator's canonical state. It then killed both the candidate API process
and tool gateway in the unique CP72 project after observing `receive_count=1`.
The recovered service read the original task/effect IDs, reconciled canonical
state, and resumed the same task. Each restart trial produced exactly one
persisted effect and one simulator receive; no unauthorized operation occurred.

| Trial | After restart and reconciliation | Resumed result | Final task |
|---|---|---|---|
| A, before the shared fix | The effect was `DISPATCHED`; operator reconciliation changed it to `CONFIRMED`. | A retried the same submit with the consumed approval, received an approval error despite the existing confirmed effect, then a repeated resume was rejected because the task was stuck in `WAITING`. | `WAITING`, with stale uncertainty metadata. This negative record is retained. |
| A, after the shared fix | The original effect was reconciled to `CONFIRMED`. | A repeated submit returned the same confirmed effect ID without dispatch. It reported the confirmed operation accurately. | `FAILED` because A did not record the required explicit completion claim. |
| C, after the shared fix | The original effect was reconciled to `CONFIRMED`. | C repeated the exact submit; the gateway returned the existing confirmed effect and did not dispatch. C reported the result accurately. | `FAILED` because C did not record the required explicit completion claim. |

The actual restart records, including the first failed-resume attempt, are in
`experiment/results/cp72_restart_recovery.jsonl`. Their result does not hide the
initial model failure or count the second source revision as a successful task.

## Shared defects corrected

1. **Confirmed reconciliation did not update a `DISPATCHED` row.** If the
   simulator committed but the gateway stopped before persisting the lost
   acknowledgement, the reconciliation endpoint could report `CONFIRMED`
   while its SQL update excluded the durable `DISPATCHED` state. The update now
   accepts `DISPATCHED`, `QUARANTINED`, or `UNRESOLVED`. The regression recreates
   the crash window and independently checks task ID, effect ID, canonical
   simulator state, and one receive.
2. **An exact retry could not reuse its durable effect record.** After restart,
   a candidate retrying the same task/target/details saw the consumed approval
   and got an approval error even when that operation was already confirmed.
   The gateway now returns the existing persisted result for the exact same
   task, target, and details. It does not create a new effect or contact the
   simulator. A differing request for the same task/target is rejected; pending
   effects remain pending for reconciliation.
3. **Settled effects could leave a task permanently blocked in `WAITING`.** A
   resumed task now clears the stale uncertainty marker only after a fresh
   trusted task read shows every persisted effect is terminal. An unresolved
   effect keeps the marker, and approval-pending remains blocked. `approval_required`
   is now recorded as an approval flag rather than mislabeled as uncertain
   effect state.

The full existing unit/integration suite passed locally in the disposable CP72
project: **63 tests, 2 skipped**. The first two suite attempts exposed setup
issues (uninitialized disposable Grocy, then a workspace fixture that had been
changed by the earlier suite run); the fixture was initialized/reset within the
unique CP72 project and the final run passed. No existing project was targeted.
After the run, all CP72 project containers, networks, and volumes were removed
using the unique project name. The model-server container initially remained
because it belongs to the separate `model-8b` Compose profile; it was then
removed by the same project-scoped cleanup. No non-CP72 resource was selected.

## Interruption coverage and remaining gaps

- **Before dispatch:** deterministic ledger coverage confirms a `DISPATCHED`
  record with no canonical acceptance remains quarantined when reconciliation
  reads `NOT_RECEIVED`; repeat reconciliation does not dispatch it. This is a
  service-contract case, not a model-run interruption.
- **After dispatch / before acknowledgement:** directly exercised by killing
  the candidate API and gateway after the simulator committed and before its
  delayed acknowledgement returned.
- **After acknowledgement / before durable gateway confirmation:** the same
  interruption leaves the row `DISPATCHED`; recovery uses the original effect
  ID and canonical simulator state.
- **During reconciliation:** the accepted and not-received canonical states
  are tested, but a process/network outage during the reconciliation request
  has not yet been fault-injected.
- **After reconciliation / before final response:** the runner reconciles
  before resuming. A kill precisely between a successful reconciliation and
  final-answer persistence has not yet been exercised.
- **After restart / repeated resume:** A and C resumed the original task after
  both API processes restarted. The pre-fix A record shows repeated resume
  rejection; post-fix A/C preserve the same effect and receive count. A second
  post-fix resume after the task became terminal was correctly not attempted.

Accordingly, CP72 establishes the no-duplicate and canonical-reconciliation
properties for the exercised crash window, but it does not claim full recovery
qualification across all six interruption points.

## Firewall, infrastructure, and control handoff

The firewall implementation exists in
`experiment/scripts/gpu_trial_firewall.py`. CP67/CP68 records show the temporary
rule policy, counters, negative probes, and rollback. The available CP68 records
do not identify the exact helper image digest, invocation, or an approved
reusable privileged execution path. A private procedure draft is at
`acceptance/hades-v3-ephemeral-firewall-helper-procedure-draft-2026-10-13.md`
in the local HADES-infra checkout. It is explicitly not approved for use. A
future execution requires owner approval of the exact immutable helper image,
command, affected host namespace, and its `NET_ADMIN` privilege.

The private HADES-infra checkout has no configured remote and contains extensive
uncommitted owner work. The access matrix and Cinder handoff remain untouched;
the firewall procedure is a separate local draft. Address and ownership details
in the matrix remain partly provisional, with evidence freshness recorded
there. No documentation commit was made.

Read-only public v2 inspection still shows `p0rkm4th/hades` at
`35c33ed9630296d8f7b581306d254a770ab439c5`. This is source status only; the
current deployed revision, owner acceptance, and exact-SHA CI for that public
revision are not independently established here. The local v2 worktree is
substantially dirty and remains untouched. The existing Cinder handoff requests
a current snapshot; no reply is recorded in the shared handoff.

## Next experiment

Finish fault injection during reconciliation and between reconciliation and
final-answer persistence. Then evaluate Hermes only with a strict deterministic
peer configured at at least 65,536 context; report it as contract/runtime
evidence, not a model-equivalent comparison. Follow with fresh memory correction
and retrieval cases. ADR-010 remains **NOT READY**: A and C can safely reconcile
the exercised uncertain operation but neither completed the durable task, C
timed out before tool use once, Hermes has not been tested on this recovery
family, and two interruption windows remain open.
