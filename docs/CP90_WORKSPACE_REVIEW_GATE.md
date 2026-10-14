# CP90 — Gateway enforcement for parked workspace tasks

**Date:** 2026-10-14  
**Source base:** `ecad1fcec13e4641f926948c22b3fc6445951a26`  
**Evidence class:** isolated integration contract test  
**GPU/model generations:** none

## Finding and change

CP88 parks a stateless candidate task in `WAITING` with the trusted checkpoint marker `operator_review_required` after a confirmed workspace effect. The candidate API checks that state before resuming, but the gateway's `/v1/workspace/exec` accepted `WAITING` tasks and did not inspect the marker. A caller reaching the authenticated gateway directly could therefore submit a new operation identity while the task was parked.

The gateway now reads the checkpoint under its existing task-row lock and rejects workspace execution with HTTP 409 when the task is `WAITING` and the trusted checkpoint requires operator review. This reuses the current task/effect ledger and does not add an operation store or retry path.

## Verification

A fresh project, `hades-v3-cp90-probe-20261014`, used synthetic data and internal-only Compose networks. After one harmless `pwd` command was independently recorded `CONFIRMED`, the test moved the task to `WAITING` with `operator_review_required`, then attempted a distinct operation identity. The gateway returned 409 and a direct database query confirmed exactly one workspace effect remained, the original confirmed effect. No provider/model request was made.

Results:

- `test_gateway.py`: 9/9 passed, including the new gateway-level review-gate regression.
- `test_task_lifecycle.py`: 16/16 passed.
- `test_candidate_finalization.py`: 24/24 passed.
- Python compilation for the changed gateway and test passed.

Only the uniquely named CP90 project was started. Its containers are stopped after the test. Its volumes, internal networks, and project-tagged images are retained for Tallowmere's cleanup review; no shared resource was removed. CP75/CP80 remained untouched. A protected cleanup handoff identifies the exact CP90 project.

## Limits

This closes direct gateway bypass of the existing sequential CP88 review park. It does not serialize concurrent candidate turns, restore a lost final response, or make arbitrary shell commands exactly-once. The gateway still supports multiple intentional commands in a running task; the current design cannot distinguish a legitimate next command from a concurrent fresh identity after an earlier effect becomes confirmed unless the invocation itself is durably identified. Unknown command outcomes remain quarantined. No claim of general shell reconciliation is made.

CP89's memory generation timeouts and CP81's historical results are unchanged. ADR-010 remains **NOT READY**.
