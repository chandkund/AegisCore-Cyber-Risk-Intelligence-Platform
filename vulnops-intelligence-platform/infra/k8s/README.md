# Kubernetes manifests (reference)

Example **base** manifests for deploying API + web behind an Ingress. Replace image registry paths, hostnames, and secrets with values from your environment (Helm/Kustomize overlays recommended for multi-env).

## Prerequisites

- Cluster 1.26+  
- `kubectl` configured  
- Container images built and pushed (e.g. `ghcr.io/<org>/vulnops-api:<tag>`)  
- TLS: cert-manager **ClusterIssuer** or cloud load balancer certificate  

## Secrets

Create `vulnops-api-secret` in namespace `vulnops` with keys:

| Key | Example |
|-----|--------|
| `DATABASE_URL` | `postgresql+psycopg://...` |
| `JWT_SECRET_KEY` | 32+ random characters |

```bash
kubectl create namespace vulnops --dry-run=client -o yaml | kubectl apply -f -
kubectl -n vulnops create secret generic vulnops-api-secret \
  --from-literal=DATABASE_URL='postgresql+psycopg://...' \
  --from-literal=JWT_SECRET_KEY='...'
```

For **External Secrets Operator**, map the same keys from Azure Key Vault / AWS Secrets Manager (see `docs/deployment/secrets-management.md`).

## Apply

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/configmap-api.yaml
kubectl apply -f infra/k8s/deployment-api.yaml
kubectl apply -f infra/k8s/service-api.yaml
kubectl apply -f infra/k8s/deployment-web.yaml
kubectl apply -f infra/k8s/service-web.yaml
kubectl apply -f infra/k8s/hpa-api.yaml
kubectl apply -f infra/k8s/ingress.yaml
kubectl apply -f infra/k8s/networkpolicy-api.yaml
kubectl apply -f infra/k8s/networkpolicy-web.yaml
```

Edit `ingress.yaml` hosts and `deployment-*.yaml` images before applying. **NetworkPolicy** assumes the ingress controller lives in namespace `ingress-nginx` (label `kubernetes.io/metadata.name: ingress-nginx`) and PostgreSQL pods carry `app.kubernetes.io/name: postgres` — adjust selectors to match your cluster. Path-based restriction of `/metrics` is **not** possible with NetworkPolicy alone; see [metrics-path-isolation.md](../../docs/operations/metrics-path-isolation.md).

## HPA

`hpa-api.yaml` targets CPU ~70% average utilization. Tune `minReplicas` / `maxReplicas` for SLO and cost.

## Kustomize overlays

Environment-specific bundles: [overlays/README.md](overlays/README.md) (`staging`, `production`).

## Secret operator samples

See [samples/README.md](samples/README.md) (External Secrets, Sealed Secrets workflow).
