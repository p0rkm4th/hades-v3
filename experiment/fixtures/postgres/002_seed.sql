INSERT INTO lab_domains (domain_id, grocy_location_id, grocy_shopping_list_id) VALUES
  ('domain-home-amber', 2, 1),
  ('domain-home-cobalt', 3, 2);

INSERT INTO lab_users (user_id, domain_id, display_name, token_sha256) VALUES
  ('user-amber', 'domain-home-amber', 'Amber (synthetic)', encode(digest('fixture-token-amber', 'sha256'), 'hex')),
  ('user-cobalt', 'domain-home-cobalt', 'Cobalt (synthetic)', encode(digest('fixture-token-cobalt', 'sha256'), 'hex'));

INSERT INTO infra_observations (domain_id, subject, observation_state, value, observed_at, source) VALUES
  ('domain-home-amber', 'synthetic-router', 'FRESH', '{"health":"ok","services":2}'::jsonb, now(), 'fixture-inventory-v1'),
  ('domain-home-amber', 'synthetic-backup', 'STALE', '{"health":"unknown","services":1}'::jsonb, now() - interval '2 days', 'fixture-inventory-v1'),
  ('domain-home-amber', 'synthetic-lab-host', 'UNKNOWN', NULL, NULL, 'fixture-inventory-v1'),
  ('domain-home-cobalt', 'synthetic-router', 'FRESH', '{"health":"degraded","services":1}'::jsonb, now(), 'fixture-inventory-v1');

INSERT INTO commitment_targets (target_id, behavior) VALUES
  ('target-accept', 'ACCEPT'),
  ('target-reject', 'REJECT'),
  ('target-ack-loss', 'ACCEPT_ACK_LOST'),
  ('target-idempotent', 'DUPLICATE_SAFE');
