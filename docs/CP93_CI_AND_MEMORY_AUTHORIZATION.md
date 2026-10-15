# CP93 — CI cleanup regression and memory authorization review

**Status:** Source fix prepared; exact-SHA CI pending publication.
**Baseline:** `1c229352d0929c4afb6090110246698e6e5be9b5`.
**ADR-010:** NOT READY.

## P0 — Gateway marker cleanup

The concurrent exact-retry gateway regression creates a task-specific marker in the persistent Amber workspace. The test read the marker and verified one write but did not remove it. The next `test_workspace_flow.py` test correctly detected the untracked file through its clean-tree assertion. The assertion remains unchanged.

The test now registers an exact, idempotent marker-removal callback with `unittest.TestCase.addCleanup` immediately after task creation. The callback uses a distinct task-derived operation ID, deletes only `.concurrent-operation-<task-id>.txt`, verifies absence, and asserts the gateway confirmed the cleanup. `unittest` invokes registered cleanup even if a later assertion fails. The prior CI failures at `b55a316`, `7818a19`, and `1c22935` remain historical failures; they are not rescored.

`py_compile` and `git diff --check` pass. Local integration execution did not reach either suite: the fresh uniquely named Compose project failed to allocate its first network because Docker's predefined address pools are exhausted. Existing networks belong to active projects and were left unchanged. The attempted project was scoped and its created volumes/networks were removed by the exact-project trap. The repository workflow already runs `test_gateway.py` followed immediately by `test_workspace_flow.py` in one run-specific Compose project; the new exact-SHA Actions run is the required integration verification. No HADES v2 or other agent-owned service was changed.

## P1 — Memory request-to-effect authorization

Source review confirms that task authentication, exact-key/revision CAS, atomic effect recording, and trusted finalization do not authorize the candidate's chosen memory key and replacement value at dispatch. The candidate begins a task with the authenticated user's free-text goal. `trusted_completion_contract` is created by the orchestrator for outcome verification; it cannot serve as a dispatch grant. The only persisted approval implementation in this experiment is `commitment_approvals`, bound to commitment targets and digests. No generic grant/policy record or memory-specific authorization path is present.

The frozen PRD allows an authenticated request to authorize an action only when the user's intent is explicit and material parameters are known. The smallest coherent design is therefore to use the existing trusted policy/grant authority as the source of a task-bound, immutable exact-operation authorization, checked by the gateway before memory mutation. It must bind user, domain, task, `memory_correct`, stable key, expected revision, and canonical replacement (or a collision-resistant digest), and remain distinct from completion criteria. For requests that do not specify a unique key and replacement clearly enough, the policy authority must require clarification or exact user approval. The gateway must reject absence/mismatch before creating an effect or changing canonical memory, then retain the existing CAS, atomic ledger write, exact replay, changed-retry rejection, and independent finalization checks.

This experiment does not currently expose a general grant issuer or a trusted intent-to-operation contract. Adding an orchestrator-only field without establishing who may issue it would merely move the trust gap; treating model interpretation or successful finalization as authorization would violate the boundary. Consequently CP93 records the enforcement design and blocker but does not invent a parallel grant system or enable candidate memory mutation. Required gateway tests remain: missing authorization, mismatched key/value, changed task or scope, cross-domain attempt, exact replay, changed replay, and an exact authorized correction with canonical/effect verification.

## Verification and next action

- Source check: `python -m py_compile experiment/tests/test_gateway.py` passed.
- Diff check: `git diff --check` passed.
- Live model, Hypnos, privileged firewall, HADES v2, and shared model-serving activity: none.
- Next: publish this narrow test correction; require the exact-SHA workflow to show both sequential suites green. Then resolve the trusted memory authorization issuer/contract from the frozen policy authority before adding mutation-path changes or resuming CP81.
