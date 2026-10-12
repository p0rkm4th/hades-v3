from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid

import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.environ["DATABASE_URL"]


def effect_digest(target_id: str, details: str) -> str:
    canonical = json.dumps(
        {"target_id": target_id, "details": details},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def approve(args):
    args.details = args.details.strip()
    if not args.details:
        raise SystemExit("details cannot be empty")
    digest = effect_digest(args.target, args.details)
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT t.task_id, t.user_id, t.domain_id "
                "FROM tasks t JOIN lab_users u USING (user_id, domain_id) "
                "WHERE t.task_id=%s AND t.user_id=%s AND u.active",
                (args.task, args.user),
            )
            task = cur.fetchone()
            if task is None:
                raise SystemExit("active user-owned task not found")
            cur.execute("SELECT target_id FROM commitment_targets WHERE target_id=%s", (args.target,))
            if cur.fetchone() is None:
                raise SystemExit("unknown simulated commitment target")
            cur.execute(
                "INSERT INTO commitment_approvals "
                "(user_id, domain_id, task_id, target_id, effect_digest, approved_by, expires_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, now() + make_interval(secs => %s)) "
                "RETURNING approval_id, expires_at",
                (args.user, task["domain_id"], args.task, args.target, digest,
                 args.approved_by, args.ttl_seconds),
            )
            approval = cur.fetchone()
    print(json.dumps({
        "approval_id": str(approval["approval_id"]),
        "task_id": str(args.task),
        "target_id": args.target,
        "effect_digest": digest,
        "expires_at": approval["expires_at"].isoformat(),
    }, separators=(",", ":")))


def inspect(args):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT c.target_id, c.behavior, c.accepted_effect_id, c.receive_count, c.revision, "
            "e.state AS effect_state "
            "FROM commitment_targets c LEFT JOIN effects e ON e.effect_id=c.accepted_effect_id "
            "WHERE c.target_id=%s",
            (args.target,),
        )
        row = cur.fetchone()
    if row is None:
        raise SystemExit("unknown simulated commitment target")
    if row["accepted_effect_id"] is not None:
        row["accepted_effect_id"] = str(row["accepted_effect_id"])
    print(json.dumps(row, default=str, separators=(",", ":")))


def main():
    parser = argparse.ArgumentParser(
        description="Issue one short-lived exact-effect grant for a synthetic fixture trial."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    issue = subparsers.add_parser("approve")
    issue.add_argument("--user", required=True)
    issue.add_argument("--task", type=uuid.UUID, required=True)
    issue.add_argument("--target", required=True)
    issue.add_argument("--details", required=True)
    issue.add_argument("--approved-by", default="fixture-operator")
    issue.add_argument("--ttl-seconds", type=int, default=300)
    read = subparsers.add_parser("inspect")
    read.add_argument("--target", required=True)
    args = parser.parse_args()
    if args.command == "approve":
        if args.ttl_seconds < 1 or args.ttl_seconds > 600:
            parser.error("--ttl-seconds must be between 1 and 600")
        if len(args.details) > 1000:
            parser.error("--details must be no more than 1000 characters")
        approve(args)
    else:
        inspect(args)


if __name__ == "__main__":
    main()
