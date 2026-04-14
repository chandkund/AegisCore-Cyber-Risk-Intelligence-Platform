# Metrics and observability

## Current baseline (Phase 7–8)

| Signal | Where | Use |
|--------|--------|-----|
| **Structured logs** | Uvicorn / app loggers to stdout | Set `LOG_JSON=true` in containers for log aggregation (Azure Monitor, Datadog, ELK). Fields include ISO timestamp, level, logger, message; request middleware adds `request_id` when present. |
| **Liveness** | `GET /health` | Process up; **no database** — suitable for aggressive kube `livenessProbe`. |
| **Readiness** | `GET /ready` | Executes `SELECT 1` on the app DB pool — use for `readinessProbe`; fails if DB unavailable. |
| **ETL watermark** | `public.etl_watermarks` | Operational check that `reporting_daily` completed (`last_success_at`). |
| **Prometheus (opt-in)** | `GET /metrics` | Set `PROMETHEUS_METRICS_ENABLED=true`. Exposes `prometheus-fastapi-instrumentator` defaults (request latency, status codes). |

### Enabling `/metrics`

1. Set environment variable **`PROMETHEUS_METRICS_ENABLED=true`** on the API deployment (Compose, Kubernetes, or systemd).  
2. **Do not** publish `/metrics` on a public Ingress. Restrict to the mesh / internal ServiceMonitor (Prometheus Operator) or VPC-only scrape.  
3. Use **NetworkPolicy** or a **dedicated scrape port** so only observability workloads reach metrics — policies are **not** HTTP path-aware; see [metrics-path-isolation.md](metrics-path-isolation.md).

## Recommended probes (Kubernetes example)

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 20
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
```

## OpenTelemetry (optional follow-up)

For distributed traces, add OTLP export (SDK + collector sidecar) and propagate W3C `traceparent` from the Next.js BFF or browser fetch layer.

## Tracing

Correlate logs with **`X-Request-ID`** (or configured `REQUEST_ID_HEADER`) from `RequestIdMiddleware`. Propagate the same header from the Next.js frontend `apiFetch` layer when extending clients.
