from __future__ import annotations

import hmac
import json
import os
import re
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.environ["DATABASE_URL"]
API_TOKEN = os.environ["COMMITMENT_API_TOKEN"]
MAX_BODY = 16 * 1024


def database():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


class Simulator(BaseHTTPRequestHandler):
    server_version = "HadesSyntheticCommitment/0.1"

    def log_message(self, fmt, *args):
        print(f"{self.log_date_time_string()} {self.command} {urlsplit(self.path).path}")

    def send_json(self, status, value):
        data = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authorized(self):
        value = self.headers.get("Authorization", "")
        return value.startswith("Bearer ") and hmac.compare_digest(value[7:], API_TOKEN)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("request too large")
        body = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("object required")
        return body

    def do_POST(self):
        if not self.authorized():
            return self.send_json(401, {"error": "simulator authentication required"})
        if urlsplit(self.path).path != "/v1/commit":
            return self.send_json(404, {"error": "route not found"})
        try:
            body = self.read_body()
            effect_id = uuid.UUID(body["effect_id"])
            target_id = body["target_id"]
            digest = body["effect_digest"]
            if not isinstance(target_id, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                return self.send_json(400, {"error": "invalid commitment request"})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "invalid commitment request"})

        response_status = 200
        response_body = {}
        lose_ack = False
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT effect_id, request, resource_key, state FROM effects "
                "WHERE effect_id=%s FOR UPDATE",
                (effect_id,),
            )
            effect = cur.fetchone()
            if (effect is None or effect["state"] != "DISPATCHED"
                    or effect["resource_key"] != f"commitment:{target_id}"
                    or effect["request"].get("effect_digest") != digest):
                return self.send_json(409, {"error": "no matching durable dispatched effect"})

            cur.execute(
                "SELECT target_id, behavior, accepted_effect_id, receive_count "
                "FROM commitment_targets WHERE target_id=%s FOR UPDATE",
                (target_id,),
            )
            target = cur.fetchone()
            if target is None:
                return self.send_json(404, {"error": "unknown target"})
            if target["accepted_effect_id"] == effect_id:
                response_body = {
                    "state": "ACCEPTED", "effect_id": str(effect_id), "idempotent_replay": True
                }
            elif target["accepted_effect_id"] is not None:
                response_status = 409
                response_body = {"error": "target already accepted a different effect"}
            elif target["behavior"] == "REJECT":
                cur.execute(
                    "UPDATE commitment_targets SET receive_count=receive_count+1, revision=revision+1 "
                    "WHERE target_id=%s",
                    (target_id,),
                )
                response_status = 409
                response_body = {"state": "REJECTED", "effect_id": str(effect_id)}
            else:
                cur.execute(
                    "UPDATE commitment_targets SET accepted_effect_id=%s, "
                    "receive_count=receive_count+1, revision=revision+1 WHERE target_id=%s",
                    (effect_id, target_id),
                )
                lose_ack = target["behavior"] in {"ACCEPT_ACK_LOST", "ACCEPT_ACK_LOST_DELAYED"}
                response_body = {
                    "state": "ACCEPTED", "effect_id": str(effect_id), "idempotent_replay": False
                }

        if lose_ack:
            # The state is committed before the simulated transport failure.
            # The delayed variant exposes a deterministic crash-injection window
            # for the disposable CP72 recovery runner.
            if target["behavior"] == "ACCEPT_ACK_LOST_DELAYED":
                time.sleep(3)
            return self.send_json(504, {"error": "acknowledgment unavailable"})
        return self.send_json(response_status, response_body)

    def do_GET(self):
        if urlsplit(self.path).path == "/health":
            with database() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
            return self.send_json(200, {"status": "ok"})
        if not self.authorized():
            return self.send_json(401, {"error": "simulator authentication required"})
        match = re.fullmatch(r"/v1/effects/([0-9a-fA-F-]{36})", urlsplit(self.path).path)
        if match is None:
            return self.send_json(404, {"error": "route not found"})
        try:
            effect_id = uuid.UUID(match.group(1))
        except ValueError:
            return self.send_json(400, {"error": "invalid effect id"})
        with database() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT target_id, behavior, accepted_effect_id, receive_count, reconcile_failures_remaining "
                "FROM commitment_targets WHERE accepted_effect_id=%s",
                (effect_id,),
            )
            accepted = cur.fetchone()
            cur.execute(
                "SELECT resource_key FROM effects WHERE effect_id=%s",
                (effect_id,),
            )
            effect = cur.fetchone()
        if effect is None:
            return self.send_json(404, {"error": "effect not found"})
        target_id = effect["resource_key"].removeprefix("commitment:")
        if accepted and accepted["reconcile_failures_remaining"] > 0:
            with database() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE commitment_targets SET reconcile_failures_remaining=reconcile_failures_remaining-1 "
                    "WHERE target_id=%s AND reconcile_failures_remaining > 0",
                    (target_id,),
                )
            return self.send_json(503, {"error": "injected reconciliation response interruption"})
        return self.send_json(200, {
            "effect_id": str(effect_id),
            "target_id": target_id,
            "state": "ACCEPTED" if accepted else "NOT_RECEIVED",
            "receive_count": accepted["receive_count"] if accepted else None,
        })


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8090), Simulator).serve_forever()
