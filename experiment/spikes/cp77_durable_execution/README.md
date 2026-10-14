# CP77 DBOS process-recovery probe

This disposable probe checks one narrow DBOS contract: after a process dies
after an external operation is accepted but before a step result is recorded,
DBOS replays the interrupted step. The synthetic target uses an `effect_id`
unique key to return the same accepted operation on replay.

Run with Python 3.10 or newer:

```sh
python -m venv /tmp/hades-cp77-dbos
/tmp/hades-cp77-dbos/bin/pip install -r experiment/spikes/cp77_durable_execution/requirements.txt
/tmp/hades-cp77-dbos/bin/python experiment/spikes/cp77_durable_execution_probe.py
```

The result should report two step attempts, one canonical synthetic effect row,
and the same task/effect identity. All state is created under a temporary
directory and removed when the probe exits.

This is **contract evidence only**. It uses SQLite for both DBOS metadata and a
synthetic idempotent target. It does not call the HADES gateway, validate a
grant, use the HADES effect ledger, prove PostgreSQL behavior, or qualify a
candidate runtime. The important finding is that DBOS does retry the step;
no-duplicate behavior comes from the external effect-ID idempotency contract,
not from DBOS alone. The next test must use the isolated HADES gateway and
commitment simulator before DBOS can be considered a useful HADES integration.
