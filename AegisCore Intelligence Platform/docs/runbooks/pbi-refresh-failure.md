# Runbook: Power BI dataset refresh failure

## Symptoms

- Email or Power BI Service notification: **Refresh failed**.  
- Dashboards show old data while API/OLTP show new remediations.

## Checks

1. In Power BI Service → **Dataset** → **Refresh history**: read error detail (credentials, gateway, SQL timeout).  
2. If using **gateway**: confirm gateway machine can reach PostgreSQL and password not expired.  
3. Run `powerbi/scripts/verify_reporting_prereqs.sql` — zero fact rows may still “refresh succeed” but look empty.

## Actions

| Error class | Action |
|-------------|--------|
| **Login failed** for PostgreSQL | Rotate DB password in vault and update gateway data source credentials. |
| **Timeout** | Reduce Import table size, add indexes on `fact_vulnerability_snapshot (snapshot_date)`, or switch heavy pages to aggregates. |
| **ETL not run** | Follow [etl-failure.md](etl-failure.md); do not blame BI until upstream snapshot exists. |

## Prevention

- Schedule refresh **after** ETL buffer (see `powerbi/docs/refresh-and-etl-contract.md`).  
- Alert on **ETL watermark** age in parallel with BI refresh alerts.
