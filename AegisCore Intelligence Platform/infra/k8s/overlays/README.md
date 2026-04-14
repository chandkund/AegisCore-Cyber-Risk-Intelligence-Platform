# Kustomize overlays

Environment-specific patches on top of the shared manifests in `infra/k8s/`.

## Usage

```bash
kubectl apply -k infra/k8s/overlays/staging
kubectl apply -k infra/k8s/overlays/production
```

Edit **`kustomization.yaml`** `images` entries to match your registry and tags (or let CI inject `kustomize edit set image` before apply).

## Layout

| Overlay | Purpose |
|---------|---------|
| [staging](staging/) | Lower replicas / relaxed tags for pre-prod |
| [production](production/) | Production tags; optional replica or resource patches |

Base manifests remain in the parent directory (`../`) so existing `kubectl apply -f` workflows keep working.
