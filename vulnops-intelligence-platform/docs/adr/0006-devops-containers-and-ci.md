# ADR 0006: Containers, Compose, and GitHub Actions CI

- **Status:** Accepted  
- **Date:** 2026-04-11  
- **Context:** The platform needs reproducible local stacks, non-root container processes, automated verification of migrations and unit tests, and a path toward production hardening without committing secrets.

- **Decision:**
  1. **Docker Compose** at repository root runs **PostgreSQL 16**, **FastAPI** (Alembic on entrypoint, then Uvicorn), and **Next.js** (standalone build). Images run as **non-root** UIDs (`aegiscore` / `nextjs`).
  2. **Build context** is the **monorepo root** so the API image includes `backend/` and `ml/` with the same relative layout `app.ml.prioritizer` expects (`/app` as logical repo root).
  3. **GitHub Actions** workflow **CI** runs: **pytest** (default excludes integration), **Alembic `upgrade head`** against an ephemeral Postgres service, **frontend** `npm ci` + `npm test` + `npm run build`, and **Docker Buildx** builds for API and frontend (no push).
  4. **Secrets** are not stored in Compose defaults for production; **Key Vault / secret manager** patterns are documented under `docs/deployment/`. Local Compose uses a **documented dev-only** JWT default that must be overridden in any shared environment.
  5. **Prometheus** metrics endpoint is **not** added as a hard dependency in this phase; observability is **structured JSON logs** (`LOG_JSON`) plus `/health` and `/ready` for orchestration probes.

- **Consequences:**
  - **Pros:** One-command demo stack; CI catches migration drift and broken frontend builds early; aligns with Phase 1 architecture.  
  - **Cons:** Compose does not include Redis, Airflow, or gateway; integration tests remain opt-in; image sizes are not optimized for distroless yet.  
  - **Follow-up:** Optional `ruff`/`mypy` gates, Trivy image scan, Kubernetes manifests under `infra/k8s`, and workflow_dispatch integration job with seeded DB.
