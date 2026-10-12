CREATE TABLE commitment_approvals (
    approval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL REFERENCES lab_users(user_id),
    domain_id text NOT NULL REFERENCES lab_domains(domain_id),
    task_id uuid NOT NULL REFERENCES tasks(task_id),
    target_id text NOT NULL REFERENCES commitment_targets(target_id),
    effect_digest text NOT NULL CHECK (effect_digest ~ '^[0-9a-f]{64}$'),
    approved_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    CHECK (expires_at > created_at)
);

CREATE INDEX commitment_approvals_scope
    ON commitment_approvals (user_id, domain_id, task_id, target_id, expires_at);
