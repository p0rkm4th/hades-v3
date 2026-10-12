from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


DATABASE_URL = os.environ["DATABASE_URL"]
GROCY_URL = os.environ.get("GROCY_URL", "http://grocy").rstrip("/")
GROCY_API_KEY_FILE = os.environ["GROCY_API_KEY_FILE"]
COMMITMENT_URL = os.environ.get("COMMITMENT_URL", "http://commitment-simulator:8090").rstrip("/")
COMMITMENT_API_TOKEN = os.environ["COMMITMENT_API_TOKEN"]
WORKSPACE_URLS = {
    "user-amber": os.environ.get("WORKSPACE_AMBER_URL", "http://workspace-amber:8091"),
    "user-cobalt": os.environ.get("WORKSPACE_COBALT_URL", "http://workspace-cobalt:8091"),
}
TOOLS_PATH = os.environ.get("TOOLS_PATH", "/app/tools.json")
MAX_BODY = 64 * 1024


class ClientError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def database():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def json_default(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def grocy_request(method: str, path: str, body: dict | None = None):
    key = open(GROCY_API_KEY_FILE, encoding="utf-8").read().strip()
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{GROCY_URL}/api{path}",
        data=data,
        method=method,
        headers={"GROCY-API-KEY": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Grocy returned HTTP {exc.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Grocy did not respond") from None
    return json.loads(raw) if raw else None


def commitment_request(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    request = urllib.request.Request(
        f"{COMMITMENT_URL}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {COMMITMENT_API_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            value = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            value = {}
        return exc.code, value
    except urllib.error.URLError:
        raise RuntimeError("simulated commitment outcome is uncertain") from None


def commitment_digest(target_id: str, details: str):
    canonical = json.dumps(
        {"target_id": target_id, "details": details},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def workspace_request(user_id: str, command: str):
    base = WORKSPACE_URLS.get(user_id)
    if base is None:
        raise ClientError(403, "no disposable workspace for this identity")
    request = urllib.request.Request(
        f"{base.rstrip('/')}/v1/exec",
        data=json.dumps({"command": command}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            value = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            value = {}
        return exc.code, value
    except urllib.error.URLError:
        raise RuntimeError("workspace outcome is uncertain") from None


def grocy_products():
    return grocy_request("GET", "/objects/products")


def domain_config(domain_id: str):
    with database() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT grocy_location_id, grocy_shopping_list_id "
            "FROM lab_domains WHERE domain_id = %s",
            (domain_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ClientError(403, "domain has no fixture mapping")
    return row


def inventory_for(domain_id: str):
    domain = domain_config(domain_id)
    products = grocy_products()
    entries = grocy_request(
        "GET", f"/stock/locations/{domain['grocy_location_id']}/entries"
    )
    amounts: dict[str, float] = {}
    for entry in entries:
        product_id = str(entry["product_id"])
        amounts[product_id] = amounts.get(product_id, 0) + float(entry["amount"])
    return [
        {"name": row["name"], "amount": amounts.get(str(row["id"]), 0)}
        for row in products
    ]


def shopping_for(domain_id: str):
    domain = domain_config(domain_id)
    products = {str(row["id"]): row["name"] for row in grocy_products()}
    rows = grocy_request("GET", "/objects/shopping_list")
    return [
        {
            "name": products.get(str(row["product_id"]), "unknown"),
            "amount": float(row["amount"]),
            "done": bool(row["done"]),
        }
        for row in rows
        if int(row["shopping_list_id"]) == int(domain["grocy_shopping_list_id"])
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "HadesFixtureGateway/0.1"

    def log_message(self, fmt, *args):
        # Keep prompts, tokens, and synthetic values out of ordinary logs.
        print(f"{self.log_date_time_string()} {self.command} {self.path.split('?')[0]}")

    def send_json(self, status: int, value):
        payload = json.dumps(value, separators=(",", ":"), default=json_default).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ClientError(413, "request body too large")
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            raise ClientError(400, "invalid JSON") from None

    def identity(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise ClientError(401, "bearer authentication required")
        token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, domain_id FROM lab_users "
                "WHERE token_sha256 = %s AND active",
                (token_hash,),
            )
            row = cur.fetchone()
        if row is None:
            raise ClientError(401, "invalid fixture identity")
        return row

    def dispatch_request(self):
        try:
            route = urlsplit(self.path)
            if self.command == "GET" and route.path == "/health":
                with database() as conn, conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return self.send_json(200, {"status": "ok"})
            if self.command == "GET" and route.path == "/tools.json":
                with open(TOOLS_PATH, encoding="utf-8") as source:
                    return self.send_json(200, json.load(source))

            identity = self.identity()
            user_id = identity["user_id"]
            domain_id = identity["domain_id"]

            if self.command == "GET" and route.path == "/v1/inventory":
                return self.send_json(200, {"items": inventory_for(domain_id)})
            if self.command == "GET" and route.path == "/v1/shopping-list":
                return self.send_json(200, {"items": shopping_for(domain_id)})
            if self.command == "GET" and route.path == "/v1/infrastructure":
                with database() as conn, conn.cursor() as cur:
                    cur.execute(
                        "SELECT subject, observation_state, value, observed_at, source "
                        "FROM infra_observations WHERE domain_id = %s ORDER BY subject",
                        (domain_id,),
                    )
                    rows = cur.fetchall()
                return self.send_json(200, {"observations": rows})

            if self.command == "GET" and route.path == "/v1/memory/search":
                query = parse_qs(route.query).get("q", [""])[0].strip()
                if not 2 <= len(query) <= 200:
                    raise ClientError(400, "query must contain 2 to 200 characters")
                terms = re.findall(r"[a-zA-Z0-9]+", query.lower())
                if not terms:
                    raise ClientError(400, "query must include searchable words")
                tsquery = " | ".join(terms)
                document = "to_tsvector('simple', memory_key || ' ' || value::text)"
                with database() as conn, conn.cursor() as cur:
                    cur.execute(
                        f"SELECT memory_key, value, updated_at, ts_rank_cd({document}, to_tsquery('simple', %s)) AS score "
                        f"FROM scoped_memory WHERE user_id = %s AND domain_id = %s "
                        f"AND {document} @@ to_tsquery('simple', %s) "
                        "ORDER BY score DESC, updated_at DESC, memory_key LIMIT 5",
                        (tsquery, user_id, domain_id, tsquery),
                    )
                    rows = cur.fetchall()
                return self.send_json(200, {"memories": rows})

            memory_match = re.fullmatch(r"/v1/memory/([^/]+)", route.path)
            if self.command == "GET" and memory_match:
                key = unquote(memory_match.group(1))
                with database() as conn, conn.cursor() as cur:
                    cur.execute(
                        "SELECT value, updated_at FROM scoped_memory "
                        "WHERE user_id = %s AND domain_id = %s AND memory_key = %s",
                        (user_id, domain_id, key),
                    )
                    row = cur.fetchone()
                if row is None:
                    raise ClientError(404, "memory not found")
                return self.send_json(200, row)

            if self.command == "POST" and route.path == "/v1/memory":
                body = self.read_json()
                key = body.get("key")
                if not isinstance(key, str) or not 1 <= len(key) <= 80 or "value" not in body:
                    raise ClientError(400, "key and value are required")
                with database() as conn, conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO scoped_memory (user_id, domain_id, memory_key, value) "
                        "VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, domain_id, memory_key) "
                        "DO UPDATE SET value = EXCLUDED.value, updated_at = now() "
                        "RETURNING memory_key, value, updated_at",
                        (user_id, domain_id, key, Jsonb(body["value"])),
                    )
                    row = cur.fetchone()
                return self.send_json(200, row)

            if self.command == "POST" and route.path == "/v1/tasks":
                body = self.read_json()
                goal = body.get("goal")
                if not isinstance(goal, str) or not goal.strip() or len(goal) > 1000:
                    raise ClientError(400, "goal must contain 1 to 1000 characters")
                with database() as conn, conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO tasks (user_id, domain_id, goal, state) "
                        "VALUES (%s, %s, %s, 'RUNNING') "
                        "RETURNING task_id, user_id, domain_id, goal, state, checkpoint, revision, updated_at",
                        (user_id, domain_id, goal.strip()),
                    )
                    row = cur.fetchone()
                return self.send_json(201, row)

            task_match = re.fullmatch(r"/v1/tasks/([0-9a-fA-F-]{36})", route.path)
            checkpoint_match = re.fullmatch(
                r"/v1/tasks/([0-9a-fA-F-]{36})/checkpoint", route.path
            )
            if self.command == "GET" and task_match:
                return self.task_read(task_match.group(1), user_id, domain_id)
            if self.command == "POST" and checkpoint_match:
                body = self.read_json()
                state = body.get("state")
                checkpoint = body.get("checkpoint")
                if state not in {"RUNNING", "WAITING", "COMPLETED", "FAILED"} or not isinstance(checkpoint, dict):
                    raise ClientError(400, "valid state and checkpoint object are required")
                with database() as conn, conn.cursor() as cur:
                    cur.execute(
                        "UPDATE tasks SET state=%s, checkpoint=%s, revision=revision+1, updated_at=now() "
                        "WHERE task_id=%s AND user_id=%s AND domain_id=%s "
                        "RETURNING task_id, user_id, domain_id, goal, state, checkpoint, revision, updated_at",
                        (state, Jsonb(checkpoint), checkpoint_match.group(1), user_id, domain_id),
                    )
                    row = cur.fetchone()
                if row is None:
                    raise ClientError(404, "task not found")
                return self.send_json(200, row)

            if self.command == "POST" and route.path == "/v1/shopping-list/changes":
                return self.change_shopping_list(user_id, domain_id)

            if self.command == "POST" and route.path == "/v1/commitments":
                return self.commitment_submit(user_id, domain_id)
            if self.command == "POST" and route.path == "/v1/workspace/exec":
                return self.workspace_exec(user_id, domain_id)
            reconcile_match = re.fullmatch(
                r"/v1/commitments/([0-9a-fA-F-]{36})/reconcile", route.path
            )
            if self.command == "POST" and reconcile_match:
                return self.commitment_reconcile(
                    reconcile_match.group(1), user_id, domain_id
                )

            raise ClientError(404, "route not found")
        except ClientError as exc:
            self.send_json(exc.status, {"error": str(exc)})
        except (psycopg.Error, RuntimeError, OSError, ValueError):
            self.send_json(502, {"error": "fixture source unavailable or operation unresolved"})

    def task_read(self, task_id: str, user_id: str, domain_id: str):
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT task_id, user_id, domain_id, goal, state, checkpoint, revision, updated_at "
                "FROM tasks WHERE task_id=%s AND user_id=%s AND domain_id=%s",
                (task_id, user_id, domain_id),
            )
            row = cur.fetchone()
        if row is None:
            raise ClientError(404, "task not found")
        return self.send_json(200, row)

    def change_shopping_list(self, user_id: str, domain_id: str):
        body = self.read_json()
        additions = body.get("add", [])
        removals = body.get("remove", [])
        if not isinstance(additions, list) or not isinstance(removals, list):
            raise ClientError(400, "add and remove must be arrays")
        if len(additions) + len(removals) == 0 or len(additions) + len(removals) > 12:
            raise ClientError(400, "one to twelve list changes are required")
        for item in additions:
            if (not isinstance(item, dict) or not isinstance(item.get("name"), str)
                    or not isinstance(item.get("amount"), (int, float)) or item["amount"] <= 0):
                raise ClientError(400, "each addition needs a product name and positive amount")
        if any(not isinstance(name, str) for name in removals):
            raise ClientError(400, "remove values must be product names")

        products = grocy_products()
        by_name = {row["name"].casefold(): row for row in products}
        requested = [item["name"] for item in additions] + removals
        if any(name.casefold() not in by_name for name in requested):
            canonical_names = ", ".join(sorted(row["name"] for row in products))
            raise ClientError(
                404,
                "No changes applied: use exact canonical product names returned by "
                f"inventory_read, then retry the compound change. Valid names: {canonical_names}.",
            )
        domain = domain_config(domain_id)
        list_id = int(domain["grocy_shopping_list_id"])
        initial = shopping_for(domain_id)
        expected = {item["name"].casefold(): item["amount"] for item in initial}
        for name in removals:
            expected.pop(name.casefold(), None)
        for item in additions:
            key = item["name"].casefold()
            expected[key] = expected.get(key, 0) + float(item["amount"])

        supplied_task_id = body.get("task_id")
        with database() as conn, conn.cursor() as cur:
            if supplied_task_id is not None:
                try:
                    task_id = uuid.UUID(str(supplied_task_id))
                except (ValueError, TypeError):
                    raise ClientError(400, "task_id must be a UUID") from None
                cur.execute(
                    "SELECT task_id FROM tasks WHERE task_id=%s AND user_id=%s AND domain_id=%s",
                    (task_id, user_id, domain_id),
                )
                if cur.fetchone() is None:
                    raise ClientError(404, "task not found")
            else:
                cur.execute(
                    "INSERT INTO tasks (user_id, domain_id, goal, state) "
                    "VALUES (%s, %s, %s, 'RUNNING') RETURNING task_id",
                    (user_id, domain_id, "compound shopping-list change"),
                )
                task_id = cur.fetchone()["task_id"]
            request_body = Jsonb(body)
            cur.execute(
                "INSERT INTO effects (task_id, user_id, domain_id, effect_kind, resource_key, state, request) "
                "VALUES (%s, %s, %s, 'GROCERY_LIST', %s, 'INTENDED', %s) RETURNING effect_id",
                (task_id, user_id, domain_id, f"grocy-list:{list_id}", request_body),
            )
            effect_id = cur.fetchone()["effect_id"]

        try:
            current_rows = grocy_request("GET", "/objects/shopping_list")
            current_ids = {
                int(row["product_id"]): float(row["amount"])
                for row in current_rows if int(row["shopping_list_id"]) == list_id
            }
            for name in removals:
                product_id = int(by_name[name.casefold()]["id"])
                amount = current_ids.get(product_id)
                if amount is not None:
                    grocy_request("POST", "/stock/shoppinglist/remove-product", {
                        "product_id": product_id, "list_id": list_id, "product_amount": amount
                    })
            for item in additions:
                grocy_request("POST", "/stock/shoppinglist/add-product", {
                    "product_id": int(by_name[item["name"].casefold()]["id"]),
                    "list_id": list_id,
                    "product_amount": float(item["amount"]),
                })
            verified = shopping_for(domain_id)
            actual = {item["name"].casefold(): item["amount"] for item in verified}
            if actual != expected:
                raise RuntimeError("Grocy read-back did not match requested changes")
        except Exception:
            with database() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE effects SET state='UNRESOLVED', updated_at=now() WHERE effect_id=%s",
                    (effect_id,),
                )
            raise RuntimeError("shopping-list effect is unresolved") from None

        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE effects SET state='CONFIRMED', result=%s, updated_at=now() WHERE effect_id=%s",
                (Jsonb({"verified_after": verified}), effect_id),
            )
            cur.execute(
                "UPDATE tasks SET state='COMPLETED', updated_at=now() WHERE task_id=%s",
                (task_id,),
            )
        return self.send_json(200, {
            "task_id": str(task_id), "effect_id": str(effect_id), "state": "CONFIRMED",
            "verified_after": verified,
        })

    def commitment_submit(self, user_id: str, domain_id: str):
        body = self.read_json()
        task_id = body.get("task_id")
        target_id = body.get("target_id")
        details = body.get("details")
        approval_id = body.get("approval_id")
        if not isinstance(target_id, str) or not re.fullmatch(r"[a-z0-9-]{1,80}", target_id):
            raise ClientError(400, "valid target_id is required")
        if not isinstance(details, str) or not details.strip() or len(details) > 1000:
            raise ClientError(400, "details must contain 1 to 1000 characters")
        try:
            task_uuid = uuid.UUID(str(task_id))
            approval_uuid = uuid.UUID(str(approval_id))
        except (ValueError, TypeError, AttributeError):
            raise ClientError(400, "task_id and approval_id must be UUIDs") from None
        details = details.strip()
        digest = commitment_digest(target_id, details)

        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT task_id FROM tasks WHERE task_id=%s AND user_id=%s AND domain_id=%s",
                (task_uuid, user_id, domain_id),
            )
            if cur.fetchone() is None:
                raise ClientError(404, "task not found")
            cur.execute(
                "SELECT approval_id FROM commitment_approvals "
                "WHERE approval_id=%s AND user_id=%s AND domain_id=%s AND task_id=%s "
                "AND target_id=%s AND effect_digest=%s AND consumed_at IS NULL "
                "AND expires_at > now() FOR UPDATE",
                (approval_uuid, user_id, domain_id, task_uuid, target_id, digest),
            )
            if cur.fetchone() is None:
                raise ClientError(403, "current exact-effect approval required")
            cur.execute(
                "INSERT INTO effects "
                "(task_id, user_id, domain_id, effect_kind, resource_key, state, request) "
                "VALUES (%s, %s, %s, 'EXTERNAL_COMMITMENT', %s, 'INTENDED', %s) "
                "RETURNING effect_id",
                (task_uuid, user_id, domain_id, f"commitment:{target_id}", Jsonb({
                    "target_id": target_id, "details": details, "effect_digest": digest,
                    "approval_id": str(approval_uuid),
                })),
            )
            effect_id = cur.fetchone()["effect_id"]
            cur.execute(
                "UPDATE commitment_approvals SET consumed_at=now() WHERE approval_id=%s",
                (approval_uuid,),
            )

        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE effects SET state='DISPATCHED', updated_at=now() WHERE effect_id=%s",
                (effect_id,),
            )
        try:
            status, result = commitment_request("POST", "/v1/commit", {
                "effect_id": str(effect_id), "target_id": target_id, "effect_digest": digest,
            })
        except RuntimeError:
            status, result = -1, {}
        if status == 200 and result.get("state") == "ACCEPTED":
            with database() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE effects SET state='CONFIRMED', result=%s, updated_at=now() "
                    "WHERE effect_id=%s",
                    (Jsonb({"target_result": result}), effect_id),
                )
            return self.send_json(200, {
                "task_id": str(task_uuid), "effect_id": str(effect_id),
                "state": "CONFIRMED", "target_result": result,
            })
        if status == 409 and result.get("state") == "REJECTED":
            with database() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE effects SET state='REJECTED', result=%s, updated_at=now() "
                    "WHERE effect_id=%s",
                    (Jsonb({"target_result": result}), effect_id),
                )
            return self.send_json(200, {
                "task_id": str(task_uuid), "effect_id": str(effect_id),
                "state": "REJECTED", "target_result": result,
            })

        uncertain = status == 504 or status < 0
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE effects SET state='QUARANTINED', result=%s, updated_at=now() "
                "WHERE effect_id=%s",
                (Jsonb({"dispatch_state": "ACK_UNCERTAIN" if uncertain else "TARGET_ERROR"}), effect_id),
            )
        return self.send_json(202, {
            "task_id": str(task_uuid), "effect_id": str(effect_id),
            "state": "QUARANTINED", "reconcile_required": True,
        })

    def commitment_reconcile(self, effect_id: str, user_id: str, domain_id: str):
        try:
            effect_uuid = uuid.UUID(effect_id)
        except ValueError:
            raise ClientError(400, "invalid effect id") from None
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT state, resource_key FROM effects "
                "WHERE effect_id=%s AND user_id=%s AND domain_id=%s",
                (effect_uuid, user_id, domain_id),
            )
            effect = cur.fetchone()
        if effect is None:
            raise ClientError(404, "effect not found")
        if effect["state"] not in {"DISPATCHED", "QUARANTINED", "UNRESOLVED"}:
            raise ClientError(409, "effect is not awaiting reconciliation")
        status, target = commitment_request("GET", f"/v1/effects/{effect_uuid}")
        if status != 200:
            with database() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE effects SET state='QUARANTINED', updated_at=now() "
                    "WHERE effect_id=%s AND state IN ('DISPATCHED','QUARANTINED','UNRESOLVED')",
                    (effect_uuid,),
                )
            return self.send_json(202, {
                "effect_id": str(effect_uuid), "state": "QUARANTINED",
                "reconcile_required": True,
            })
        if target.get("state") == "ACCEPTED" and target.get("target_id") == effect["resource_key"].removeprefix("commitment:"):
            with database() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE effects SET state='CONFIRMED', result=%s, updated_at=now() "
                    "WHERE effect_id=%s AND state IN ('QUARANTINED','UNRESOLVED')",
                    (Jsonb({"reconciled_target_state": target}), effect_uuid),
                )
            return self.send_json(200, {
                "effect_id": str(effect_uuid), "state": "CONFIRMED",
                "reconciled_target_state": target,
            })
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE effects SET state='QUARANTINED', result=%s, updated_at=now() "
                "WHERE effect_id=%s AND state IN ('DISPATCHED','QUARANTINED','UNRESOLVED')",
                (Jsonb({"reconciled_target_state": target}), effect_uuid),
            )
        return self.send_json(202, {
            "effect_id": str(effect_uuid), "state": "QUARANTINED",
            "reconcile_required": True,
        })

    def workspace_exec(self, user_id: str, domain_id: str):
        body = self.read_json()
        command = body.get("command")
        try:
            task_uuid = uuid.UUID(str(body.get("task_id")))
        except (ValueError, TypeError, AttributeError):
            raise ClientError(400, "task_id must be a UUID") from None
        if not isinstance(command, str) or not command.strip() or len(command) > 8192:
            raise ClientError(400, "command must contain 1 to 8192 characters")
        command = command.strip()
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT state FROM tasks WHERE task_id=%s AND user_id=%s AND domain_id=%s",
                (task_uuid, user_id, domain_id),
            )
            task = cur.fetchone()
            if task is None:
                raise ClientError(404, "task not found")
            if task["state"] not in {"RUNNING", "WAITING"}:
                raise ClientError(409, "task is not active")
            cur.execute(
                "INSERT INTO effects "
                "(task_id, user_id, domain_id, effect_kind, resource_key, state, request) "
                "VALUES (%s, %s, %s, 'WORKSPACE_COMMAND', %s, 'INTENDED', %s) "
                "RETURNING effect_id",
                (task_uuid, user_id, domain_id, f"workspace:{user_id}", Jsonb({"command": command})),
            )
            effect_id = cur.fetchone()["effect_id"]
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE effects SET state='DISPATCHED', updated_at=now() WHERE effect_id=%s",
                (effect_id,),
            )
        try:
            status, result = workspace_request(user_id, command)
        except RuntimeError:
            status, result = -1, {}
        if status != 200 or result.get("timed_out"):
            with database() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE effects SET state='QUARANTINED', result=%s, updated_at=now() "
                    "WHERE effect_id=%s",
                    (Jsonb({"runner_status": status, "result": result}), effect_id),
                )
            return self.send_json(202, {
                "task_id": str(task_uuid), "effect_id": str(effect_id),
                "state": "QUARANTINED", "inspection_required": True,
            })
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE effects SET state='CONFIRMED', result=%s, updated_at=now() "
                "WHERE effect_id=%s",
                (Jsonb(result), effect_id),
            )
        return self.send_json(200, {
            "task_id": str(task_uuid), "effect_id": str(effect_id),
            "state": "CONFIRMED", **result,
        })

    def do_GET(self):
        self.dispatch_request()

    def do_POST(self):
        self.dispatch_request()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
