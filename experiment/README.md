# Disposable fixture environment

This Compose project is a synthetic comparison fixture, not a production security boundary.

## Services and reset

- PostgreSQL `17.11-bookworm`, pinned by image digest. It owns the experiment's synthetic users/domains, task and effect ledger, scoped memory, infrastructure observations, and commitment behavior configuration.
- Grocy `4.7.1-ls342`, pinned by image digest. It owns the disposable inventory and shopping list. Its generated API key lives only in a dedicated Docker volume and is not mounted into candidate processes.
- The Python `3.13.16` tool gateway uses Psycopg `3.3.6`; it is the only candidate-adjacent service attached to both the fixture-backend network and the isolated operator network. The test runner (and future candidate workers) attach only to the operator network and receive no PostgreSQL credential or Grocy API-key volume.
- The protected commitment simulator attaches only to the fixture-backend network. The gateway is its only candidate-adjacent caller. A one-shot `fixture-admin` operator command, also confined to the fixture-backend network and disabled behind a Compose profile, issues a short-lived approval bound to a task, user, target, and canonical details digest. Candidate containers receive neither database credentials nor access to the simulator or fixture-admin service.
- Amber and Cobalt have separate shell/Git runner containers, named volumes, and internal networks. The gateway alone connects each runner to its matching identity; the runners cannot resolve each other or reach candidate/test-runner containers. Each runner is unprivileged, has a read-only root filesystem, no added capabilities, no external network route, a 2 GiB memory cap, 64-process cap, 20-second command timeout, 256 MiB per-file limit, and bounded captured output. Git is `2.39.5`; bash is `5.2.15-2+b13`.
- Optional local inference profiles use the pinned CPU `llama.cpp` server image on the operator network. Start one model at a time with `--profile model-8b` or `--profile model-14b`. The model files are downloaded to `experiment/models/`, ignored by Git, and mounted read-only. The 8B profile is Qwen3-8B Q4_K_M; the stronger profile is Qwen3-14B Q4_K_M. The current server configuration requests 40,960 tokens, matching the Qwen3 trained context limit, and uses 16 CPU threads. Model and server identities are recorded in `docs/MODEL_PROFILE.md`. A read-only homelab discovery found an existing Qwen3.6 35B GPU endpoint with a loaded effective context of 65,536, meeting Hermes's 64,000-token minimum. The operator network is deliberately internal and cannot reach that endpoint, so all candidate comparisons remain on the identical local 8B CPU profile; no context value is advertised beyond the serving endpoint's observed limit.
- All Compose networks are internal; no service port is published to the host.

Start from the repository root:

```sh
docker compose -f experiment/compose.yaml up -d
docker compose -f experiment/compose.yaml exec -T grocy sh /opt/hades-v3-scripts/initialize_grocy.sh
docker compose -f experiment/compose.yaml exec -T grocy sh /opt/hades-v3-scripts/seed_grocy_data.sh
sh experiment/tests/smoke_fixtures.sh
docker compose -f experiment/compose.yaml up -d --build tool-gateway commitment-simulator workspace-amber workspace-cobalt
docker compose -f experiment/compose.yaml run --build --rm test-runner
```

The default test run includes a real shell/Git scenario: the seeded discount test fails, the runner edits the implementation, the test passes, the change is committed, and a separate Cobalt workspace remains unchanged. It mutates the Amber workspace. Reset either synthetic workspace before repeating it:

```sh
docker compose -f experiment/compose.yaml exec -T -e WORKSPACE_RESET=1 workspace-amber python /app/workspace_runner.py
docker compose -f experiment/compose.yaml exec -T -e WORKSPACE_RESET=1 workspace-cobalt python /app/workspace_runner.py
```

For an explicitly approved synthetic commitment, create a user-owned task, then have the test operator issue an exact-effect approval from the fixture-admin profile. Pass that returned approval ID to the candidate only after the simulated confirmation step. The approval expires after five minutes by default and is consumed before dispatch. If the simulator loses its acknowledgment, the gateway records `QUARANTINED`; use `commitment_reconcile` to inspect the receiving fixture. The gateway never retries an ambiguous effect.

```sh
docker compose -f experiment/compose.yaml --profile fixture-admin run --build --rm fixture-admin approve \
  --user user-amber --task TASK_UUID --target target-ack-loss \
  --details 'Reserve the synthetic appointment slot for Amber at 16:00'
docker compose -f experiment/compose.yaml run --rm \
  -e COMMITMENT_TASK_ID=TASK_UUID -e COMMITMENT_APPROVAL_ID=APPROVAL_UUID test-runner \
  python /app/tests/test_commitment_flow.py -v
docker compose -f experiment/compose.yaml --profile fixture-admin run --rm fixture-admin inspect \
  --target target-ack-loss
```

The test runner command expects the task to target the seeded ack-loss target and the exact details in `test_commitment_flow.py`. `inspect` independently reads the target's accepted effect and receive count from the fixture database. Run the fixture-admin commands from the operator host during a controlled trial. Never run them inside a candidate container. The simulator and admin service are synthetic test components and do not authorize real external actions. Reset fixture volumes before repeating one-shot target trials.

Start a shared local model endpoint when running candidate adapters (only one profile at a time):

```sh
docker compose -f experiment/compose.yaml --profile model-8b up -d model-server-8b
# Or stop it and choose the stronger profile:
docker compose -f experiment/compose.yaml stop model-server-8b
docker compose -f experiment/compose.yaml --profile model-14b up -d model-server-14b
```

The selected server is reachable from operator-network candidate containers at `http://model-server-8b:8080/v1` or `http://model-server-14b:8080/v1`. It has no published host port. CPU inference is slower than the intended GPU path; measurements must record that hardware condition. The local model files are large and are not committed.

The A/C adapter defaults to a 50-second model-request timeout, six model requests, four tool calls, and 1,024 completion tokens per response. The candidate API client records failed turns as `FAILED`, returns the task ID, and flags operator review and possible effect uncertainty; inspect the task/effect ledger before retrying. Candidate B's outer request timeout does not prove that the Hermes backend cancels work after a disconnect, so B's failure lifecycle is not qualified.

Reproduce the matched family 2 A/C screen, including per-call seed reset, task-trace verification, and final seed restoration:

```sh
docker compose -f experiment/compose.yaml build test-runner
docker compose -f experiment/compose.yaml run --rm test-runner python /app/tests/run_family2_compound_screen.py
```

The screen uses the Qwen3-8B CPU endpoint and mutates only the synthetic Amber list. It stops without resetting after an API failure so an operator can inspect any unresolved effect. For a read-only task-error closure probe, intentionally override the candidate timeout, run each supported probe, then restore the default before further comparisons:

```sh
MODEL_REQUEST_TIMEOUT_SECONDS=0.01 docker compose -f experiment/compose.yaml --profile harness up -d --build --force-recreate candidate-api
docker compose -f experiment/compose.yaml run --rm test-runner python /app/tests/candidate_error_path_probe.py --candidate lean
docker compose -f experiment/compose.yaml run --rm test-runner python /app/tests/candidate_error_path_probe.py --candidate pydantic
docker compose -f experiment/compose.yaml --profile harness up -d --build --force-recreate candidate-api
```

The probe intentionally leaves two synthetic `FAILED` tasks and creates no effects. Confirm the restored default with `docker compose -f experiment/compose.yaml exec -T candidate-api python -c 'import os; print(os.environ["MODEL_REQUEST_TIMEOUT_SECONDS"])'` before resuming comparisons.

To reproduce the limited family 3 source-unavailable screen, ensure the disposable Amber fixture has no row for `synthetic-monitor`, then insert the temporary `ERROR` row, run three matched calls per candidate, and remove that exact row. This database mutation is only for the disposable lab and must never target a household or production database:

```sh
docker compose -f experiment/compose.yaml exec -T postgres psql -U fixture_writer -d hades_lab -v ON_ERROR_STOP=1 -c "INSERT INTO infra_observations (domain_id, subject, observation_state, value, observed_at, source) VALUES ('domain-home-amber', 'synthetic-monitor', 'ERROR', NULL, NULL, 'fixture-unavailable-v1') ON CONFLICT (domain_id, subject) DO NOTHING;"
docker compose -f experiment/compose.yaml build test-runner
docker compose -f experiment/compose.yaml run --rm test-runner python /app/tests/run_family3_unavailable_screen.py
docker compose -f experiment/compose.yaml exec -T postgres psql -U fixture_writer -d hades_lab -v ON_ERROR_STOP=1 -c "DELETE FROM infra_observations WHERE domain_id='domain-home-amber' AND subject='synthetic-monitor' AND observation_state='ERROR' AND source='fixture-unavailable-v1';"
```

Before insertion, inspect the subject and stop if it already exists; do not overwrite or delete a preexisting row. After the screen, verify the original three Amber observations through the gateway. The recorded run used the same Qwen3-8B CPU endpoint and configuration as the preceding family 3 screen. The injected row was deleted after the run and the original seed was verified.

`smoke_fixtures.sh` checks domain separation, fresh/stale/unknown observations, commitment fixture count, Grocy inventory and shopping-list state, and idempotent reseeding. `test-runner` checks scoped gateway reads and writes, memory isolation, durable task checkpoints, compound shopping-list changes, and independent Grocy read-back. The gateway integration test mutates the Amber shopping list; reset and reseed before running it again.

Destroy only this project's disposable data with:

```sh
docker compose -f experiment/compose.yaml --profile model-8b --profile model-14b down -v
```

That command stops the optional model server and deletes the lab database, Grocy database, and test-only Grocy API-key volume. Never point this Compose file at an existing household Grocy instance or non-fixture database.

## Current seed

- Inventory: Rice 2, Milk 1, Eggs 6, Pasta 1.
- Shopping list: Milk 1, Oats 1.
- Synthetic users: Amber and Cobalt, each assigned a separate domain.
- Grocy isolation: each domain maps to a separate pantry location and shopping list within the one Grocy instance; Cobalt starts with an empty pantry/list.
- Infrastructure: fresh, stale, and unknown observations; values and names are synthetic.

The shared tool API provides inventory, shopping-list, infrastructure, scoped memory, task/checkpoint, approval-gated simulated commitment, and per-user workspace execution operations. The commitment path uses durable pre-dispatch intent, target-side idempotency by effect ID, quarantine after ambiguous acknowledgment, and read-back reconciliation. Four targeted commitment executions and the workspace test passed with fixture verification. The Playwright-compatible interface is in `candidates/index.html`; run its UI smoke test with `docker compose -f experiment/compose.yaml --profile harness run --build --rm test-runner python /app/tests/test_ui.py`. Start the comparison API and Hermes fixture with `docker compose -f experiment/compose.yaml --profile harness up -d --build candidate-api hermes-amber hermes-cobalt`. A and C completed the repeated family 1 screen, three family 2 trajectories, and one limited family 3 prompt. The third family 2 trajectory passed 3/3 per candidate on Qwen3-8B with durable task traces and independently checked effects; the second still exposes repeated 8B partial completion despite shared canonical-name guidance, while Qwen3-14B passed that trajectory 3/3. A and C's forced-timeout task closure is validated; Hermes backend cancellation remains unverified. Candidate B is blocked on the verified CPU context of 40,960 versus its 64,000-token minimum. A separate homelab GPU endpoint meets the numeric floor but remains outside the isolated Compose network. Further family 2 cases, families 3–8, interruption recovery, maintenance comparison, historical qualification and owner evaluation remain pending. The shell fixture is an experimental isolation boundary, not a production security guarantee; aggregate workspace volume usage is not quota-limited.
