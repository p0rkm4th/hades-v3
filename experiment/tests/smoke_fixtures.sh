#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
COMPOSE="docker compose -f $ROOT/experiment/compose.yaml"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cd "$ROOT"
$COMPOSE exec -T postgres psql -U fixture_writer -d hades_lab -v ON_ERROR_STOP=1 >/dev/null <<'SQL'
DO $$
BEGIN
  IF (SELECT count(*) FROM lab_users) <> 2 THEN RAISE EXCEPTION 'expected two synthetic users'; END IF;
  IF (SELECT count(DISTINCT domain_id) FROM lab_users) <> 2 THEN RAISE EXCEPTION 'user domains are not isolated'; END IF;
  IF (SELECT count(DISTINCT grocy_location_id) FROM lab_domains) <> 2 THEN RAISE EXCEPTION 'Grocy inventory locations are shared'; END IF;
  IF (SELECT count(DISTINCT grocy_shopping_list_id) FROM lab_domains) <> 2 THEN RAISE EXCEPTION 'Grocy shopping lists are shared'; END IF;
  IF NOT EXISTS (SELECT 1 FROM infra_observations WHERE observation_state='FRESH') THEN RAISE EXCEPTION 'fresh observation missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM infra_observations WHERE observation_state='STALE') THEN RAISE EXCEPTION 'stale observation missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM infra_observations WHERE observation_state='UNKNOWN') THEN RAISE EXCEPTION 'unknown observation missing'; END IF;
  IF (SELECT count(*) FROM commitment_targets) <> 4 THEN RAISE EXCEPTION 'commitment behavior fixtures missing'; END IF;
END $$;
SQL

$COMPOSE exec -T grocy sh /opt/hades-v3-scripts/initialize_grocy.sh >/dev/null
$COMPOSE exec -T grocy sh /opt/hades-v3-scripts/seed_grocy_data.sh >/dev/null
$COMPOSE exec -T grocy sh /opt/hades-v3-scripts/seed_grocy_data.sh >/dev/null

$COMPOSE exec -T grocy sh -c 'key=$(cat /run/fixture-secrets/grocy-api-key); curl -fsS -H "GROCY-API-KEY: $key" http://127.0.0.1/api/objects/products' >"$TMP/products.json"
$COMPOSE exec -T grocy sh -c 'key=$(cat /run/fixture-secrets/grocy-api-key); curl -fsS -H "GROCY-API-KEY: $key" http://127.0.0.1/api/stock' >"$TMP/stock.json"
$COMPOSE exec -T grocy sh -c 'key=$(cat /run/fixture-secrets/grocy-api-key); curl -fsS -H "GROCY-API-KEY: $key" http://127.0.0.1/api/objects/shopping_list' >"$TMP/shopping.json"
$COMPOSE exec -T grocy sh -c 'key=$(cat /run/fixture-secrets/grocy-api-key); curl -fsS -H "GROCY-API-KEY: $key" http://127.0.0.1/api/stock/locations/3/entries' >"$TMP/cobalt-stock.json"

python3 - "$TMP" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
products = {str(row["id"]): row["name"] for row in json.loads((root / "products.json").read_text())}
stock_rows = json.loads((root / "stock.json").read_text())
shopping_rows = json.loads((root / "shopping.json").read_text())
cobalt_stock_rows = json.loads((root / "cobalt-stock.json").read_text())
stock = {products[str(row["product_id"])]: row["amount_aggregated"] for row in stock_rows}
shopping = {products[str(row["product_id"])]: row["amount"] for row in shopping_rows}
assert stock == {"Rice": 2, "Milk": 1, "Eggs": 6, "Pasta": 1}, stock
assert shopping == {"Milk": 1, "Oats": 1}, shopping
assert all(row["shopping_list_id"] == 1 for row in shopping_rows), shopping_rows
assert cobalt_stock_rows == [], cobalt_stock_rows
assert len(products) == 5, products
print("Disposable fixture smoke checks passed: 2 isolated users, 4 infrastructure observations, 4 stocked products, 2 shopping-list entries, idempotent reseed.")
PY
