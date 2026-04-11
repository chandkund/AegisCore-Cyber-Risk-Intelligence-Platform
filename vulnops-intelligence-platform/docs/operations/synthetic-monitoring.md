# Synthetic monitoring (external probes)

Synthetic checks complement **in-cluster** probes and **Prometheus** by testing the **same paths users hit** (DNS, TLS, CDN, WAF).

## Tools

| Vendor | Typical use |
|--------|-------------|
| **Checkly** | HTTP checks on `/health`, `/ready`, critical API routes; multi-region. |
| **Datadog Synthetics** | Browser + API tests; SLO integration. |
| **Grafana Cloud k6 / Ping** | Scripted flows and global ping. |
| **Azure Application Insights availability** | URL ping from Azure POPs. |

## Recommended checks (align with [SLOs](slos-and-alerting.md))

| Check | URL | Success | Frequency |
|-------|-----|---------|-----------|
| **API liveness** | `GET https://api.example.com/health` | 200 + JSON `status` | 1–5 min |
| **API readiness** | `GET https://api.example.com/ready` | 200 + DB OK | 1–5 min |
| **Auth smoke** | `POST /api/v1/auth/login` with synthetic **read-only** test user | 200 or expected 401 policy | 15–60 min |

## Alerting

- Route **synthetic failures** to the same **PagerDuty/Opsgenie** service as **readiness** alerts, with **lower priority** than kube `readinessProbe` storms (synthetics catch edge/DNS; kube catches pod health).  
- Tag alerts with **`source:synthetic`** for correlation.

## Security

- Use a **dedicated** low-privilege test account for login checks; rotate with [credential rotation](../runbooks/credential-rotation.md).  
- Do **not** embed production admin credentials in synthetics.
