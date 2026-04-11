-- Example: read-only role for Power BI / BI tools against schema `reporting` only.
-- Run as a superuser or owner; replace password via your secret manager workflow.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'reporting_ro') THEN
    CREATE ROLE reporting_ro WITH LOGIN PASSWORD 'replace-me-from-secret-store';
  END IF;
END
$$;

GRANT USAGE ON SCHEMA reporting TO reporting_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO reporting_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA reporting GRANT SELECT ON TABLES TO reporting_ro;
-- Views are relations in PostgreSQL; future views inherit default privileges where applicable.
