# GitHub Actions — deploy workflows

## Workflows

| File | Trigger | Purpose |
|------|---------|---------|
| [`.github/workflows/deploy-staging.yml`](../../.github/workflows/deploy-staging.yml) | `workflow_dispatch` | Staging rollout placeholder + optional HTTP smoke |
| [`.github/workflows/deploy-production.yml`](../../.github/workflows/deploy-production.yml) | `workflow_dispatch` | Production rollout placeholder + optional smoke |

## Environments

Create **GitHub Environments** named `staging` and `production`:

- **production**: add **required reviewers** and optional **wait timer**.
- **staging**: optional protection rules.

## OIDC (preferred over `KUBE_CONFIG`)

See [github-oidc-kubernetes.md](github-oidc-kubernetes.md). Deploy workflows request **`id-token: write`** for federated AWS/Azure/GCP login.

## Secrets (repository or environment-scoped)

| Secret | Used by |
|--------|---------|
| `STAGING_PUBLIC_API_BASE_URL` | Staging smoke: public base URL (e.g. `https://api.staging.example.com`) |
| `PRODUCTION_PUBLIC_API_BASE_URL` | Production smoke |
| `AWS_DEPLOY_ROLE_ARN` | (Optional) IAM role for staging EKS deploy |
| `AWS_DEPLOY_ROLE_ARN_PRODUCTION` | (Optional) IAM role for production |
| `KUBE_CONFIG` | Legacy base64 kubeconfig — avoid when OIDC is available |

If the public base URL secret is **unset**, smoke steps **skip** gracefully.

## Replacing placeholders

Edit the **“Apply rollout (replace with kubectl or Helm)”** step to run your Helm/Kustomize/`kubectl` flow (e.g. `kubectl apply -k infra/k8s/overlays/staging`) using the dispatched image tags. Keep smoke tests after the rollout to assert **`GET /health`** (process) and **`GET /ready`** (database).
