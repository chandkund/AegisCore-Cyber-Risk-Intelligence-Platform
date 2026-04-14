# AegisCore Intelligence Platform

Enterprise-oriented cybersecurity risk analytics: OLTP + reporting schema, FastAPI backend, Next.js frontend, Python ETL, scikit-learn risk prioritization, and Power BI executive views.

## Current status

**Phase 10 complete:** **Operate at scale** — [GitHub OIDC → Kubernetes](docs/deployment/github-oidc-kubernetes.md) patterns, deploy workflows with **`id-token: write`** and commented AWS/EKS steps; **Kustomize overlays** ([`infra/k8s/overlays/`](infra/k8s/overlays/README.md)); **External Secrets** / **Sealed Secrets** ([samples](infra/k8s/samples/README.md), [sealed-secrets.md](docs/deployment/sealed-secrets.md)); **pip-compile enforced in CI** (`requirements-lock` in [ci.yml](.github/workflows/ci.yml), [`.in` → `.txt`](docs/deployment/python-dependency-lock.md)); [synthetic monitoring](docs/operations/synthetic-monitoring.md) aligned with [SLOs](docs/operations/slos-and-alerting.md); [post-mortem template](docs/operations/post-mortem-template.md); [ADR 0009](docs/adr/0009-operate-scale-oidc-kustomize-locks.md).  
**Phase 9 complete:** **Production polish** — **Trivy image** scan + **SARIF** upload to GitHub Security (fork PRs skip upload), **CRITICAL** gates on API/web images, **`ruff format --check`** in CI, **NetworkPolicy** samples (`infra/k8s/networkpolicy-*.yaml`), **deploy** workflows (`deploy-staging` / `deploy-production`) with **environment** gates and optional **`/health` + `/ready`** smoke, **SLO/alerting** doc (PagerDuty/Opsgenie patterns), [ADR 0008](docs/adr/0008-production-polish.md).  
**Phase 8 complete:** **Hardening & scale-out** — **Ruff** + **mypy** in CI, **Dependabot** (npm, Docker, GitHub Actions), **Trivy** filesystem scan (CRITICAL severity gate), optional **integration** workflow (Postgres + Alembic + `seed_oltp.py` + `pytest -m integration`), opt-in **`PROMETHEUS_METRICS_ENABLED`** exposing `/metrics`, reference **Kubernetes** manifests under `infra/k8s/` (Ingress TLS + HPA), `backend/requirements.txt` install aggregator, [ADR 0007](docs/adr/0007-hardening-lint-security-k8s.md).  
**Phase 7 complete:** **DevOps** — root `docker-compose.yml` (Postgres 16 + API with Alembic entrypoint + Next standalone), non-root Dockerfiles under `docker/`, `.github/workflows/ci.yml` (pytest, Alembic smoke on Postgres, frontend test/build, Docker Buildx), `infra/docker/grants_reporting_readonly.sql`, runbooks (`docs/runbooks/`), secrets and observability docs, [ADR 0006](docs/adr/0006-devops-containers-and-ci.md).  
**Phase 6 complete:** **Power BI** specification pack (`powerbi/`) — PostgreSQL `reporting` connection, star schema / DAX measures, executive dashboard page spec, RLS and workspace governance, ETL→refresh contract, optional embed env vars; helper view `database/views/002_vw_fact_latest_snapshot.sql` and prereq SQL script.  
**Phase 5 complete:** Next.js 14 **frontend** (App Router, Tailwind, session-based JWT client with refresh-on-401, protected app shell, dashboard / findings / assets / analytics with Recharts, ML model info + per-finding predict, admin users with 403 handling).  
**Phase 4 complete:** scikit-learn **risk prioritization** model (proxy labels, feature pipeline, training CLI, joblib bundle + metadata, `/api/v1/ml/*` inference + model info).  
**Phase 3 complete:** FastAPI `/api/v1` (JWT access + rotating refresh, RBAC, findings/assets/CVE/analytics APIs, audit logging on mutations, structured logging hooks, global error envelope).  
**Phase 2 complete:** OLTP + `reporting` star schema (SQLAlchemy models, Alembic migration, reference DDL, CSV seeds, reporting ETL job, validation tests).

## Documentation

- [System architecture](docs/architecture/system-architecture.md)
- [ADR 0002 — OLTP vs reporting schema](docs/adr/0002-oltp-and-reporting-schemas.md)
- [ADR 0003 — JWT / RBAC / refresh strategy](docs/adr/0003-fastapi-jwt-rbac.md)
- [ADR 0004 — ML prioritization packaging](docs/adr/0004-ml-risk-prioritization.md)
- [ADR 0005 — Power BI / reporting integration](docs/adr/0005-power-bi-reporting-integration.md)
- [ADR 0006 — Docker, Compose, and CI](docs/adr/0006-devops-containers-and-ci.md)
- [ADR 0007 — Lint, security scan, integration CI, K8s, Prometheus](docs/adr/0007-hardening-lint-security-k8s.md)
- [ADR 0008 — Image SARIF, format, NetworkPolicy, deploy, SLOs](docs/adr/0008-production-polish.md)
- [ADR 0009 — OIDC, Kustomize, secret operators, pip locks, synthetics, post-mortems](docs/adr/0009-operate-scale-oidc-kustomize-locks.md)
- [GitHub OIDC and Kubernetes deploy](docs/deployment/github-oidc-kubernetes.md)
- [Sealed Secrets workflow](docs/deployment/sealed-secrets.md)
- [Secrets management (Key Vault pattern)](docs/deployment/secrets-management.md)
- [GitHub Actions deploy workflows](docs/deployment/github-actions-deploy.md)
- [Python dependency lock (pip-tools)](docs/deployment/python-dependency-lock.md)
- [Metrics and observability](docs/operations/metrics-and-observability.md)
- [Metrics path isolation (NetworkPolicy limits)](docs/operations/metrics-path-isolation.md)
- [SLOs and alerting](docs/operations/slos-and-alerting.md)
- [Synthetic monitoring (SLO-aligned checks)](docs/operations/synthetic-monitoring.md)
- [Post-mortem template](docs/operations/post-mortem-template.md)
- [Runbooks](docs/runbooks/README.md)
- [Power BI — connection, model, dashboards](powerbi/README.md)
- [Docker image notes](docker/README.md) · [Infra — SQL + Kubernetes](infra/README.md)
- [ML assumptions (labels, leakage, features)](ml/docs/ASSUMPTIONS.md)

## Database and ETL (Phase 2)

Prerequisites: PostgreSQL 15+ (or 14+), Python 3.11+.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements\base.txt -r requirements\dev.txt
$env:DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/aegiscore"
.\.venv\Scripts\alembic upgrade head
```

Load demo data (idempotent by primary keys / natural keys; use a fresh DB for clean re-runs if email conflicts appear):

```powershell
cd ..
$env:DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/aegiscore"
python scripts\seed_oltp.py
```

Run reporting ETL for a calendar day (dimensions sync + `fact_vulnerability_snapshot`). From repository root:

```powershell
python -m data_pipeline.jobs.run_reporting_etl --snapshot-date 2026-04-01
```

Optional: apply analytic views under `database/views/` (after ETL has produced at least one snapshot), including `002_vw_fact_latest_snapshot.sql` for Power BI default models.

Tests:

```powershell
pytest
```

Integration tests (`@pytest.mark.integration`) run only when `DATABASE_URL` is set and the schema exists.

## API server (Phase 3)

From `backend/` with virtualenv activated:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/aegiscore"
$env:JWT_SECRET_KEY = "<32+ random chars — openssl rand -hex 32>"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- OpenAPI UI: http://localhost:8000/api/v1/docs  
- Liveness: `GET /health` (no DB)  
- Readiness: `GET /ready` (checks DB)

**Seeds / passwords:** `scripts/seed_oltp.py` now hashes passwords with `bcrypt` (same as the API). Re-run seeds on a fresh DB if you previously used passlib-only hashes.

**Pytest:** default run excludes `@pytest.mark.integration` (avoids long TCP timeouts). Run:

`pytest -m integration` when `AEGISCORE_TEST_DATABASE_URL` points at a migrated, seeded PostgreSQL instance.

## Machine learning (Phase 4)

Train a prioritization model (writes `ml/models/artifacts/risk_prioritization.joblib` — gitignored except `.gitkeep`):

```powershell
# Synthetic bootstrap (no DB required)
python -m ml.training.train_prioritizer --source synthetic --output ml/models/artifacts/risk_prioritization.joblib

# Or from PostgreSQL rows (augments with synthetic if too few rows)
$env:DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/aegiscore"
python -m ml.training.train_prioritizer --source db --output ml/models/artifacts/risk_prioritization.joblib
```

API (after login):

- `GET /api/v1/ml/model-info` — bundle / metrics metadata  
- `POST /api/v1/ml/predict/finding/{uuid}` — `probability_urgent` + lightweight explanation vector

See [ml/docs/ASSUMPTIONS.md](ml/docs/ASSUMPTIONS.md) for label definitions and limitations.

## Web UI (Phase 5)

Prerequisites: Node.js 20+ recommended, API running with CORS allowing the UI origin (default dev: http://localhost:3000).

```powershell
cd frontend
copy .env.local.example .env.local
# Edit NEXT_PUBLIC_API_BASE_URL if the API is not on http://localhost:8000
npm install
npm run dev
```

- App: http://localhost:3000 — sign in with a seeded user (e.g. admin).  
- **Vitest:** `npm test` · **production build:** `npm run build`

## Power BI (Phase 6)

Authoring is **not** committed as `.pbix` files. Use the specification pack and checklist:

1. Run ETL (see above) so `reporting.fact_vulnerability_snapshot` has data.
2. Apply optional view `database/views/002_vw_fact_latest_snapshot.sql`.
3. Run `powerbi/scripts/verify_reporting_prereqs.sql` to validate row counts.
4. Follow [powerbi/README.md](powerbi/README.md) and [powerbi/pbix-build-checklist.md](powerbi/pbix-build-checklist.md) in Power BI Desktop.
5. Publish to a workspace; schedule **Import** refresh **after** the daily ETL job ([refresh contract](powerbi/docs/refresh-and-etl-contract.md)).

Embedding in Next.js is optional; see [powerbi/docs/embedding-and-nextjs.md](powerbi/docs/embedding-and-nextjs.md) and `.env.example` (`POWERBI_*`).

## Docker Compose (Phase 7)

Prerequisites: [Docker Engine](https://docs.docker.com/engine/) 24+ with Compose v2.

```powershell
# From repository root — set a strong JWT for shared environments (≥32 characters)
$env:JWT_SECRET_KEY = "<use openssl rand -hex 32 or another CSPRNG>"
docker compose up --build
```

- **PostgreSQL:** `localhost:${POSTGRES_PUBLISH_PORT:-5432}` (user/password/db default `aegiscore` / see compose file).  
- **API:** http://localhost:8000 — migrations run on container start; `GET /ready` waits for DB.  
- **Web:** http://localhost:3000 — `NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000` (browser calls host port).

Optional ML artifact: copy `docker-compose.override.example.yml` to `docker-compose.override.yml` and mount a trained `risk_prioritization.joblib`.

**Reporting read-only role:** see [infra/docker/grants_reporting_readonly.sql](infra/docker/grants_reporting_readonly.sql).

## Continuous integration

Workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (every **push** / **pull_request**): **Ruff** check + **`ruff format --check`**, **mypy**, **`requirements-lock`** (re-runs `pip-compile` and **diffs** committed `backend/requirements/*.txt`), backend **pytest** (integration excluded by default), **Alembic upgrade head** on Postgres, **frontend** `npm ci` / `npm test` / **`npm run lint`** / `npm run build` / **Playwright E2E** (`frontend/tests/e2e/`, Chromium), **Docker Buildx** image builds (**`load: true`**), **Trivy** **container** scans with **SARIF** upload to the **Security** tab (same-repo PRs only) + **CRITICAL** gates, and **Trivy** filesystem scan (CRITICAL gate).

**Local smoke (optional):** with API running, `scripts/smoke_api.sh` or `scripts/smoke_api.ps1` hits **`GET /health`** and **`GET /ready`** (set `SKIP_READY=1` if Postgres is down). Frontend E2E: from `frontend/`, run `npm run build` then `npm run test:e2e` (install browsers once: `npx playwright install chromium`).

Scheduled / manual integration: [`.github/workflows/integration.yml`](.github/workflows/integration.yml) — migrates, seeds OLTP, runs **`pytest -m integration`**.

Dependency updates: [`.github/dependabot.yml`](.github/dependabot.yml) (weekly: npm, Dockerfiles, GitHub Actions). Python pins live under `backend/requirements/*.txt` (see [backend/requirements/README.md](backend/requirements/README.md) and optional [pip-tools doc](docs/deployment/python-dependency-lock.md)).

**Deploy:** [Deploy staging](.github/workflows/deploy-staging.yml) and [Deploy production](.github/workflows/deploy-production.yml) (`workflow_dispatch`) — **`id-token: write`** for OIDC, GitHub **Environments**, optional public API URL secrets for smoke tests (see [github-actions-deploy.md](docs/deployment/github-actions-deploy.md) and [github-oidc-kubernetes.md](docs/deployment/github-oidc-kubernetes.md)). Apply manifests with **`kubectl apply -k infra/k8s/overlays/<env>`** after image tags are set.

## License

Proprietary / educational use — set explicitly before public distribution.
