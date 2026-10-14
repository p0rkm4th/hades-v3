CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE lab_domains (
    domain_id text PRIMARY KEY,
    grocy_location_id integer NOT NULL UNIQUE,
    grocy_shopping_list_id integer NOT NULL UNIQUE
);

CREATE TABLE lab_users (
    user_id text PRIMARY KEY,
    domain_id text NOT NULL REFERENCES lab_domains(domain_id),
    display_name text NOT NULL,
    token_sha256 text NOT NULL UNIQUE,
    active boolean NOT NULL DEFAULT true
);

CREATE TABLE tasks (
    task_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL REFERENCES lab_users(user_id),
    domain_id text NOT NULL,
    goal text NOT NULL,
    state text NOT NULL CHECK (state IN ('READY','RUNNING','WAITING','COMPLETED','FAILED')),
    checkpoint jsonb NOT NULL DEFAULT '{}'::jsonb,
    revision integer NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE effects (
    effect_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid NOT NULL REFERENCES tasks(task_id),
    user_id text NOT NULL REFERENCES lab_users(user_id),
    domain_id text NOT NULL,
    effect_kind text NOT NULL,
    resource_key text NOT NULL,
    state text NOT NULL CHECK (state IN ('INTENDED','DISPATCHED','CONFIRMED','UNRESOLVED','QUARANTINED','REJECTED')),
    request jsonb NOT NULL,
    result jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE scoped_memory (
    memory_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL REFERENCES lab_users(user_id),
    domain_id text NOT NULL,
    memory_key text NOT NULL,
    value jsonb NOT NULL,
    revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, domain_id, memory_key)
);

CREATE TABLE infra_observations (
    observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id text NOT NULL,
    subject text NOT NULL,
    observation_state text NOT NULL CHECK (observation_state IN ('FRESH','STALE','UNKNOWN','ERROR')),
    value jsonb,
    observed_at timestamptz,
    source text NOT NULL,
    UNIQUE (domain_id, subject)
);

CREATE TABLE commitment_targets (
    target_id text PRIMARY KEY,
    behavior text NOT NULL CHECK (behavior IN ('ACCEPT','REJECT','ACCEPT_ACK_LOST','ACCEPT_ACK_LOST_DELAYED','DUPLICATE_SAFE')),
    accepted_effect_id uuid,
    receive_count integer NOT NULL DEFAULT 0,
    reconcile_failures_remaining integer NOT NULL DEFAULT 0 CHECK (reconcile_failures_remaining >= 0),
    revision integer NOT NULL DEFAULT 0
);

CREATE INDEX tasks_owner_recent ON tasks (user_id, updated_at DESC);
CREATE INDEX effects_resource_state ON effects (resource_key, state);
CREATE INDEX memories_scope ON scoped_memory (user_id, domain_id);
