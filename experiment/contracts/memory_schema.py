"""Small idempotent schema upgrade shared by the gateway and integration tests."""


def ensure_memory_revision(cur):
    # Fresh fixtures declare the column; existing disposable volumes need the same
    # defaulted revision before the gateway serves keyed corrections.
    cur.execute(
        "ALTER TABLE scoped_memory ADD COLUMN IF NOT EXISTS "
        "revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1)"
    )
