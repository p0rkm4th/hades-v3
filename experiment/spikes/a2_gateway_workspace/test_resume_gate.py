"""Synthetic contract tests for the HADES-aware StepPersistence resume gate."""

from __future__ import annotations

from types import SimpleNamespace

from operation_identity import derive_operation_id
from recovery_gate import inspect_resume

TASK = "f30454d9-9346-4d9c-9daa-87b46e5b3f74"
CALL = "persisted-tool-call"


def main() -> None:
    pending = [SimpleNamespace(tool_call_id=CALL)]
    absent = {"task_id": TASK, "state": "RUNNING", "effects": []}
    assert inspect_resume(TASK, pending, absent)["allow"] is True

    confirmed = {
        "task_id": TASK, "state": "RUNNING", "effects": [{
            "effect_id": "synthetic", "effect_kind": "WORKSPACE_COMMAND",
            "state": "CONFIRMED", "operation_id": derive_operation_id(TASK, CALL, 0),
        }],
    }
    assert inspect_resume(TASK, pending, confirmed)["allow"] is True

    unknown = {
        "task_id": TASK, "state": "RUNNING", "effects": [{
            "effect_id": "synthetic", "effect_kind": "WORKSPACE_COMMAND",
            "state": "QUARANTINED", "operation_id": derive_operation_id(TASK, CALL, 0),
        }],
    }
    assert inspect_resume(TASK, pending, unknown)["allow"] is False

    unrelated_unknown = {
        "task_id": TASK, "state": "RUNNING", "effects": [{
            "effect_id": "synthetic", "effect_kind": "COMMITMENT", "state": "DISPATCHED",
        }],
    }
    assert inspect_resume(TASK, pending, unrelated_unknown)["allow"] is False
    assert inspect_resume(TASK, pending, {**absent, "task_id": "other"})["allow"] is False
    assert inspect_resume(TASK, pending, {**absent, "state": "COMPLETED"})["allow"] is False
    assert inspect_resume(TASK, [], absent)["allow"] is False
    assert inspect_resume(TASK, pending, {**absent, "state": "WAITING"})["allow"] is False
    print("PASS resume gate permits only absent or confirmed original calls and blocks uncertain effects")


if __name__ == "__main__":
    main()
