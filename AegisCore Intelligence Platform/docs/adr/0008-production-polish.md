# ADR 0008: Container SARIF, Ruff format, NetworkPolicy samples, deploy workflows, SLO docs

- **Status:** Accepted  
- **Date:** 2026-04-11  
- **Context:** Phase 8 added filesystem Trivy and reference Kubernetes manifests. Production pilots need **image-level** vulnerability signal in GitHub Security, **consistent formatting**, **network defaults**, **deploy automation stubs**, and **operational SLO/alert** guidance.

- **Decision:**
  1. **CI `docker-build` job** loads images into the runner (`load: true`), runs **Trivy** in **image** mode with **SARIF** output per image, uploads via **`github/codeql-action/upload-sarif`** (skipped on fork PRs where `security-events: write` is unavailable). A separate **CRITICAL gate** fails the job on either image.
  2. **`ruff format --check`** runs in **`backend-lint`**; the codebase is formatted with **`ruff format`** on Python trees under `backend/app`, `backend/tests`, `data_pipeline`, `ml`, and `scripts`.
  3. **NetworkPolicy** samples under `infra/k8s/` restrict ingress to an **ingress-nginx** namespace label and egress to **kube-dns** + **postgres** (with commented **ipBlock** for managed DB). A short doc explains that **path-based `/metrics` isolation** is not possible with NetworkPolicy alone.
  4. **Deploy workflows** (`deploy-staging`, `deploy-production`) use **`workflow_dispatch`**, **`environment:`** gates, placeholder kubectl/Helm steps, and **optional curl smoke** against secrets `STAGING_PUBLIC_API_BASE_URL` / `PRODUCTION_PUBLIC_API_BASE_URL`.
  5. **pip-tools** adoption is **documented** plus a **non-destructive** `scripts/compile_python_requirements.sh` stub; compiled outputs are not yet the source of truth.
  6. **`docs/operations/slos-and-alerting.md`** defines example SLOs, error budgets, and PagerDuty/Opsgenie routing tables tied to `/ready` and ETL watermarks.

- **Consequences:**
  - **Pros:** Security tab gains container findings; formatting is enforced; operators get copy-paste NetworkPolicies and deploy patterns.  
  - **Cons:** SARIF upload may still be limited on some fork/enterprise policies; CRITICAL gates can block CI until base images are patched; NetworkPolicies require label alignment with the real ingress and Postgres workloads.  
  - **Follow-up:** Dedicated metrics port; Helm chart; pip-compile `.in` files in repo; OIDC-based registry push from deploy workflows.
