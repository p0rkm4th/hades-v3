#!/bin/sh
set -eu

# Run inside the disposable Grocy container. The default credentials and API key
# belong only to this synthetic lab volume and must never be reused elsewhere.
BASE=http://127.0.0.1
COOKIE=/tmp/hades-v3-grocy-cookies
PAGE=/tmp/hades-v3-grocy-keys.html
KEYFILE=/run/fixture-secrets/grocy-api-key

ready=false
for attempt in $(seq 1 30); do
  if curl -fsS "$BASE/login" -o /dev/null 2>/dev/null; then
    ready=true
    break
  fi
  sleep 1
done
if [ "$ready" != true ]; then
  echo 'Grocy did not become ready within 30 seconds.' >&2
  exit 1
fi
curl -fsS "$BASE/" -o /dev/null || true
curl -sS -c "$COOKIE" -o /dev/null \
  --data 'username=admin&password=admin&stay_logged_in=on' "$BASE/login"
curl -fsS -L -b "$COOKIE" "$BASE/manageapikeys" -o "$PAGE"
if ! grep -q 'data-apikey-description="hades-v3-fixture-tools"' "$PAGE"; then
  curl -fsS -L -b "$COOKIE" \
    "$BASE/manageapikeys/new?description=hades-v3-fixture-tools" -o "$PAGE"
fi

php -r '
$html = file_get_contents($argv[1]);
if (!preg_match("/<tr[^>]*>(?:(?!<\\/tr>).)*data-apikey-description=\\\"hades-v3-fixture-tools\\\"(?:(?!<\\/tr>).)*data-apikey-key=\\\"([^\\\"]+)\\\"(?:(?!<\\/tr>).)*<\\/tr>/s", $html, $matches)) {
    fwrite(STDERR, "Fixture API key row was not found.\n");
    exit(1);
}
if (file_put_contents($argv[2], $matches[1] . "\n") === false) {
    fwrite(STDERR, "Could not store fixture API key.\n");
    exit(1);
}
chmod($argv[2], 0600);
' "$PAGE" "$KEYFILE"

chown 10001:10001 "$KEYFILE"
chmod 0400 "$KEYFILE"

KEY=$(cat "$KEYFILE")
curl -fsS -H "GROCY-API-KEY: $KEY" "$BASE/api/system/info" -o /dev/null
unset KEY
echo 'Grocy fixture initialized; API key stored in the disposable secret volume.'
