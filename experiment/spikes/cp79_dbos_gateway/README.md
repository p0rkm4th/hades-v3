# CP79 — DBOS with the HADES gateway and commitment simulator

This disposable contract integration asks whether DBOS recovery can resume a
workflow while leaving HADES as the only grant/effect authority. DBOS stores
workflow metadata in a project-scoped SQLite volume. The workflow runner has
only the `operator` network and a fixture user token; it has no database
credentials, grant authority, host access, or model connection. A separate
fixture setup/verifier service creates the synthetic exact approvals and
independently reads canonical PostgreSQL state.

Each case kills the worker after `/v1/commitments` returns, but before the DBOS
step returns to DBOS's history. On restart DBOS replays that step. The HADES
gateway must return the original effect identity without dispatching again;
the same gateway then reconciles canonical target state and the independent
verifier asks HADES to finalize from its persisted completion contract.

Run only in a uniquely named disposable Compose project. Start the ordinary
fixtures and gateway, run setup, the DBOS crash/restart probe, then independent
verification, and remove that project and its volumes. The CI workflow uses
the same order. No live model, Hypnos, GPU, host firewall, or HADES v2 resource
is involved.

This is a service-contract experiment, not candidate or model qualification.
It does not make DBOS an authorization layer or an effect ledger. If a future
integration requires DBOS state to authorize or independently prove a HADES
effect, reject that design.
