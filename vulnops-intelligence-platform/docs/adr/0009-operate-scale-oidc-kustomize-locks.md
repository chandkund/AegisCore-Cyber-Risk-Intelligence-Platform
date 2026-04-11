# ADR 0009: OIDC deploy docs, Kustomize overlays, secret operator samples, pip-compile locks, synthetics & post-mortems

- **Status:** Accepted  
- **Date:** 2026-04-11  
- **Context:** Phase 9 added deploy placeholders and NetworkPolicies. Teams need **federated identity** to Kubernetes, **GitOps-friendly** env overlays, **secret operator** examples, **reproducible Python locks** enforced in CI, and **operational** rituals (synthetics, blameless reviews).

- **Decision:**
  1. **`backend/requirements/base.in` / `dev.in`** are the **source** for runtime + dev dependencies; **`base.txt` / `dev.txt`** are **`pip-compile`** outputs (fully pinned transitive set). **`backend/pyproject.toml`** `[tool.pip-tools]` sets **`no_header`**, **`strip_extras`**, **`newline = "lf"`** for stable cross-OS diffs. **`.python-version`** pins **3.12** to align with CI.
  2. **CI job `requirements-lock`** runs `pip-compile` to **`/tmp`** and **`diff`** against committed `base.txt` and `dev.txt` (from `backend/` so config is picked up).
  3. **Kustomize overlays** under `infra/k8s/overlays/{staging,production}` compose parent manifests, set **image tags**, and patch **HPA** max/min replicas.
  4. **Samples:** `infra/k8s/samples/external-secret-api.yaml` (External Secrets Operator) and **documentation** for **Sealed Secrets** (`docs/deployment/sealed-secrets.md`, `infra/k8s/samples/README.md`).
  5. **`docs/deployment/github-oidc-kubernetes.md`** documents **AWS / Azure / GCP** OIDC → `kubectl` patterns; **deploy workflows** gain **`id-token: write`** and **commented** AWS credential + `eks update-kubeconfig` steps.
  6. **`docs/operations/synthetic-monitoring.md`** ties external probes to SLOs; **`docs/operations/post-mortem-template.md`** provides a **blameless** incident template.

- **Consequences:**
  - **Pros:** Supply-chain reproducibility; fewer long-lived secrets; clearer env promotion path.  
  - **Cons:** Lock files must be regenerated on **Python 3.12** when changing `.in` files; resolver output can still drift if PyPI metadata changes — CI catches drift. Kustomize **image** names must match Deployment `image` fields exactly.  
  - **Follow-up:** `--generate-hashes` for higher assurance; Helm chart if teams prefer charts over raw YAML + Kustomize.
