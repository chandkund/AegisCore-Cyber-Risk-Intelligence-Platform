# ADR 0007: Lint gates, supply-chain scanning, integration CI, Kubernetes reference, optional Prometheus

- **Status:** Accepted  
- **Date:** 2026-04-11  
- **Context:** Phase 7 delivered Compose and core CI. We need static analysis, scheduled full-stack tests, dependency update automation, baseline security scanning, and a **non-binding** Kubernetes reference for production pilots.

- **Decision:**
  1. **Ruff** and **mypy** run on every PR in CI (`backend-lint` job); Ruff fixes import order (`I`) across `backend/`, `data_pipeline/`, `ml/`, and `scripts/`. **mypy** targets `backend/app` only with `ignore_missing_imports` to limit noise.
  2. **Dependabot** v2 updates **npm** (`/frontend`), **Docker** (`/docker`), and **GitHub Actions** weekly. Python pins remain in `backend/requirements/*.txt` and are bumped via manual or Renovate-style PRs (Dependabot pip does not reliably follow `-r` includes in this layout).
  3. **Trivy** filesystem scan runs in CI with **CRITICAL** severity gate (`exit-code: 1`); `HIGH` is advisory-only to reduce false positives on dev dependencies. `skip-dirs` excludes `node_modules` and `.venv`.
  4. **Integration workflow** (`.github/workflows/integration.yml`) runs **weekly** and **`workflow_dispatch`**: Postgres service → Alembic → `seed_oltp.py` → `pytest -m integration`.
  5. **Kubernetes** manifests under `infra/k8s/` document Namespace, ConfigMap, Deployments (non-root), Services, HPA, and Ingress (TLS placeholders). Operators wire **External Secrets** outside this repo.
  6. **Prometheus:** `prometheus-fastapi-instrumentator` is a **runtime dependency**; metrics are exposed at **`/metrics`** only when **`PROMETHEUS_METRICS_ENABLED=true`**.

- **Consequences:**
  - **Pros:** Higher confidence in migrations and RBAC paths; repeatable K8s baseline; metrics available without default exposure.  
  - **Cons:** Trivy CRITICAL-only may miss important HIGH CVEs — teams should periodically review full Trivy HTML/SARIF reports. Integration workflow does not run on every PR by default (cost); enable `push` triggers if policy requires.  
  - **Follow-up:** Image vulnerability scan on built containers; `pip` Dependabot after consolidating requirements; NetworkPolicy samples for `/metrics`.
