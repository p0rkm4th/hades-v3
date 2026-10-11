# Disposable fixture environment

This Compose project is a synthetic comparison fixture, not a production security boundary.

## Services and reset

- PostgreSQL `17.11-bookworm`, pinned by image digest. It owns the experiment's synthetic users/domains, task and effect ledger, scoped memory, infrastructure observations, and commitment behavior configuration.
- Grocy `4.7.1-ls342`, pinned by image digest. It owns the disposable inventory and shopping list. Its generated API key lives only in a dedicated Docker volume and is not mounted into candidate processes.
- The Python `3.13.16` tool gateway uses Psycopg `3.3.6`; it is the only candidate-adjacent service attached to both the fixture-backend network and the isolated operator network. The test runner (and future candidate workers) attach only to the operator network and receive no PostgreSQL credential or Grocy API-key volume.
- All Compose networks are internal; no service port is published to the host.

Start from the repository root:

```sh
docker compose -f experiment/compose.yaml up -d
docker compose -f experiment/compose.yaml exec -T grocy sh /opt/hades-v3-scripts/initialize_grocy.sh
docker compose -f experiment/compose.yaml exec -T grocy sh /opt/hades-v3-scripts/seed_grocy_data.sh
sh experiment/tests/smoke_fixtures.sh
docker compose -f experiment/compose.yaml up -d --build tool-gateway
docker compose -f experiment/compose.yaml run --build --rm test-runner
```

`smoke_fixtures.sh` checks domain separation, fresh/stale/unknown observations, commitment fixture count, Grocy inventory and shopping-list state, and idempotent reseeding. `test-runner` checks scoped gateway reads and writes, memory isolation, durable task checkpoints, compound shopping-list changes, and independent Grocy read-back. The gateway integration test mutates the Amber shopping list; reset and reseed before running it again.

Destroy only this project's disposable data with:

```sh
docker compose -f experiment/compose.yaml down -v
```

That command deletes the lab database, Grocy database, and test-only Grocy API-key volume. Never point this Compose file at an existing household Grocy instance or non-fixture database.

## Current seed

- Inventory: Rice 2, Milk 1, Eggs 6, Pasta 1.
- Shopping list: Milk 1, Oats 1.
- Synthetic users: Amber and Cobalt, each assigned a separate domain.
- Grocy isolation: each domain maps to a separate pantry location and shopping list within the one Grocy instance; Cobalt starts with an empty pantry/list.
- Infrastructure: fresh, stale, and unknown observations; values and names are synthetic.

The shared tool API now provides inventory, shopping-list, infrastructure, scoped memory, and task/checkpoint operations. The protected simulated commitment endpoint, disposable shell/Git workspace, Playwright-compatible app, candidate adapters, model-backed trials, and restart-kill test remain to be implemented. This fixture does not certify production security.
