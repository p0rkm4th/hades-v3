# CP77 — DBOS process-recovery probe

**Classification:** CONTRACT TEST; not a HADES integration or candidate qualification
**Dependency:** DBOS Transact 3.2.0, installed in an isolated temporary Python 3.14.7 virtual environment
**Run:** `experiment/spikes/cp77_durable_execution_probe.py`

## Result

The probe completed successfully. It killed the worker with exit code 73 after the synthetic target had accepted the operation but before DBOS stored the step result. On restart, DBOS recovered the same workflow and reran the interrupted step. The step ran twice; the synthetic canonical ledger contained one accepted row, and the output preserved the same task and effect IDs.

The no-duplicate result came from the target's unique `effect_id` behavior. DBOS correctly replayed the interrupted step; DBOS alone did not make an external operation exactly-once.

## Limits

This probe used SQLite for DBOS metadata and a local synthetic canonical-effect table. It did not call the HADES gateway or commitment simulator, verify grants/approvals, use the HADES effect ledger, test PostgreSQL, run a model, or involve A/B/C. It establishes that DBOS recovery is viable enough to justify the next integration test. It does **not** establish that DBOS reduces HADES recovery code or composes safely with HADES authority.

Next test: use a uniquely scoped disposable HADES fixture project, call the existing gateway for one approved synthetic commitment, terminate the DBOS worker after gateway dispatch but before step persistence, then resume the same workflow. Independently check the original HADES task/effect IDs, simulator receive count, approval binding, and reconciled task state. Do not reuse existing CP75/lab projects, and do not install persistent services.

No HADES service, active Docker project, HADES v2 resource, Hypnos route, or firewall was changed for this probe. All probe databases were created in a temporary directory and removed on exit.
