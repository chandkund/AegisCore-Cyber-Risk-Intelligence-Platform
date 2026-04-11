# Infrastructure (Phase 7+)

This directory holds **infrastructure-as-code and SQL helpers** that are not tied to the application Python tree.

| Path | Purpose |
|------|---------|
| [docker/grants_reporting_readonly.sql](docker/grants_reporting_readonly.sql) | Example DDL for a **read-only** PostgreSQL role on schema `reporting` (Power BI / analysts). |
| [k8s/](k8s/README.md) | Reference Kubernetes manifests, **Kustomize overlays**, NetworkPolicies, operator **samples**. |

## Future work

- **Helm / Kustomize overlays:** parameterize image tags and environments on top of `infra/k8s/`.  
- **Terraform / Bicep:** Network, managed PostgreSQL, Container Apps.  
- **CI:** Extend `.github/workflows/` with deploy jobs gated on environment approval.

## Docker stack

The primary local stack is defined at **repository root**: `docker-compose.yml` and `docker/Dockerfile.*`.
