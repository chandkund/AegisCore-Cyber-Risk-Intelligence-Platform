# Isolating `/metrics` (path-aware exposure)

**Kubernetes `NetworkPolicy` cannot filter by HTTP path.** A policy that allows TCP `8000` allows both `/health` and `/metrics`.

## Options

| Approach | Notes |
|----------|--------|
| **Separate internal Service** | Expose metrics on another port (e.g. 9100) via a second container port + `Service` with `ClusterIP` and no Ingress; scrape from Prometheus inside the cluster only. |
| **Sidecar / auth proxy** | Terminate scrape on a small proxy that requires bearer token or mTLS before forwarding to the app. |
| **Service mesh** | Istio/Linkerd `AuthorizationPolicy` or equivalent for path-based rules. |
| **Ingress split** | Rare for metrics; prefer internal scrape without public Ingress. |

The reference `infra/k8s/networkpolicy-api.yaml` allows Prometheus-labeled pods in a `monitoring` namespace to reach port **8000**; tighten further using a **dedicated metrics port** once the API exposes one.
