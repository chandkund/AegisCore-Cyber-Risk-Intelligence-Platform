# SLOs, error budgets, and alerting

## Service level objectives (examples)

| Service | SLI | SLO target | Measurement window |
|---------|-----|------------|---------------------|
| **API availability** | Ratio of successful `GET /ready` (200) | 99.5% | 30-day rolling |
| **API latency** | p95 `/api/v1/*` &lt; 500 ms | 99% of hours | 7-day |
| **ETL freshness** | `reporting_daily` `last_success_at` &lt; 25 h old | 99% of days | Calendar month |

Tune targets to stakeholder expectations; document exclusions (planned maintenance, dependency outages).

## Error budget

- **Budget** = 1 − SLO (e.g. 0.5% downtime/month for 99.5% availability).  
- **Burn:** When burn exceeds policy (e.g. multi-window alerts), freeze non-critical releases and focus on reliability work.  
- **Review:** Monthly error-budget review with platform + product.

## Alert routing (PagerDuty / Opsgenie / Slack)

| Signal | Condition | Severity | Route |
|--------|-----------|----------|--------|
| **Readiness** | `/ready` fails or missing for &gt; 2 min | P1 | On-call |
| **Liveness** | `/health` fails on majority of replicas | P1 | On-call |
| **ETL stale** | `etl_watermarks.last_success_at` older than SLA | P2 | Data platform |
| **DB connections** | Pool exhaustion / saturation | P2 | On-call |
| **Trivy CRITICAL** | New CRITICAL in default branch image scan | P3 | Security |

Wire **Prometheus** or **cloud monitors** (Azure Monitor, Datadog) to send webhooks to **PagerDuty Events v2** or **Opsgenie Heartbeat**. Use `LOG_JSON` logs as secondary evidence in incident timelines.

## Synthetic checks

- **Black-box:** periodic `GET /health` and `GET /ready` from outside the cluster (same path users/load balancers use).  
- **Correlation:** include `X-Request-ID` in alert payloads when using API middleware.  
- **Vendor tooling:** see [synthetic-monitoring.md](synthetic-monitoring.md) (Checkly, Datadog, etc.).

## Dashboards

- Uptime / readiness ratio  
- ETL watermark age (hours since last success)  
- Error rate by route (`5xx` / total) if metrics enabled (`PROMETHEUS_METRICS_ENABLED`)

See [metrics-and-observability.md](metrics-and-observability.md) for `/metrics` enablement and path-isolation limits ([metrics-path-isolation.md](metrics-path-isolation.md)).
