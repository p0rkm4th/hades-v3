#!/bin/sh
set -eu

# Reproducible household fixtures. All names and quantities are synthetic.
KEY=$(cat /run/fixture-secrets/grocy-api-key)
BASE=http://127.0.0.1/api

api_get() {
  curl -fsS -H "GROCY-API-KEY: $KEY" "$BASE$1"
}

api_post() {
  curl -fsS -X POST -H "GROCY-API-KEY: $KEY" \
    -H 'Content-Type: application/json' --data-binary "$2" "$BASE$1"
}

product_id() {
  printf '%s' "$1" | php -r '
    $rows = json_decode(stream_get_contents(STDIN), true);
    foreach ($rows as $row) { if ($row["name"] === $argv[1]) { echo $row["id"]; exit; } }
  ' "$2"
}

ensure_named_entity() {
  entity=$1
  name=$2
  rows=$(api_get "/objects/$entity")
  id=$(product_id "$rows" "$name")
  if [ -z "$id" ]; then
    created=$(api_post "/objects/$entity" "{\"name\":\"$name\"}")
    id=$(printf '%s' "$created" | php -r '$x=json_decode(stream_get_contents(STDIN), true); echo $x["created_object_id"];')
  fi
  printf '%s' "$id"
}

ensure_product() {
  name=$1
  stock_amount=$2
  list_amount=$3
  rows=$(api_get /objects/products)
  id=$(product_id "$rows" "$name")
  if [ -z "$id" ]; then
    created=$(api_post /objects/products \
      "{\"name\":\"$name\",\"location_id\":2,\"qu_id_purchase\":2,\"qu_id_stock\":2,\"min_stock_amount\":0}")
    id=$(printf '%s' "$created" | php -r '$x=json_decode(stream_get_contents(STDIN), true); echo $x["created_object_id"];')
    if [ "$stock_amount" != 0 ]; then
      api_post "/stock/products/$id/add" \
        "{\"amount\":$stock_amount,\"best_before_date\":\"2030-12-31\",\"transaction_type\":\"purchase\",\"stock_label_type\":1}" >/dev/null
    fi
  fi

  if [ "$list_amount" != 0 ]; then
    shopping=$(api_get /objects/shopping_list)
    listed=$(printf '%s' "$shopping" | php -r '
      $rows=json_decode(stream_get_contents(STDIN), true);
      foreach ($rows as $row) { if ((string)$row["product_id"] === $argv[1]) { echo "yes"; exit; } }
    ' "$id")
    if [ -z "$listed" ]; then
      api_post /stock/shoppinglist/add-product \
        "{\"product_id\":$id,\"list_id\":1,\"product_amount\":$list_amount}" >/dev/null
    fi
  fi
}

ensure_named_entity locations 'Cobalt pantry' >/dev/null
ensure_named_entity shopping_lists 'Cobalt list' >/dev/null
ensure_product Rice 2 0
ensure_product Milk 1 1
ensure_product Eggs 6 0
ensure_product Pasta 1 0
ensure_product Oats 0 1
unset KEY
echo 'Grocy inventory and shopping-list fixtures initialized.'
