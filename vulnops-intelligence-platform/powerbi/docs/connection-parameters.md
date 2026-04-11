# Connection parameters (PostgreSQL → Power BI)

## Target

| Parameter | Example | Notes |
|-----------|---------|--------|
| **Server** | `localhost` or `your-host.region.rds.amazonaws.com` | Use FQDN in production. |
| **Port** | `5432` | |
| **Database** | Same as `DATABASE_URL` database name (e.g. `vulnops`) | OLTP and `reporting` schema coexist per ADR 0002. |
| **Schema** | `reporting` | Prefer a **single schema** in the initial model to reduce noise. |

## Authentication modes

| Mode | When to use |
|------|----------------|
| **Database username / password** | Dev, gateway with stored credential. |
| **Azure AD (PostgreSQL AAD auth)** | Azure Database for PostgreSQL flexible server with managed identity or user UPN — map in gateway data source. |

Create a dedicated **read-only** PostgreSQL role for BI (example — run by DBA):

```sql
CREATE ROLE reporting_ro WITH LOGIN PASSWORD '<use-secret-store>';
GRANT USAGE ON SCHEMA reporting TO reporting_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO reporting_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA reporting GRANT SELECT ON TABLES TO reporting_ro;
```

## Power Query: Get Data

1. **Get Data** → **PostgreSQL database** (or **ODBC** if your org standardizes on a driver).
2. **Server** and **Database** as above.
3. **Data Connectivity mode**
   - **Import** — default for executive dashboards; refresh after nightly ETL.
   - **DirectQuery** — use only if near-real-time is required; validate query folding and gateway latency.

## Advanced options

- **SQL statement** (optional): start from `reporting.vw_fact_latest_snapshot` plus dimension tables, or use **Navigator** to select tables individually.
- **SSL**: enable **Encrypt connection** for any non-localhost host; align with server `sslmode`.

## On-premises data gateway

Required when:

- Dataset is published to **Power BI Service**, and
- PostgreSQL is **not** reachable from the cloud (private VPC, on-prem).

Install gateway on a host that can reach PostgreSQL, register the data source with the same credentials, and route scheduled refresh through that gateway.

## Environment variables (repository)

See repository root `.env.example` — `POSTGRES_*` and optional `POWERBI_*` for embedding scenarios (not required for Desktop-only).
