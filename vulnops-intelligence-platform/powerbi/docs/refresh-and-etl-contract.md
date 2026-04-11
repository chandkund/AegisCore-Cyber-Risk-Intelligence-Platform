# Refresh schedule and ETL contract

## Upstream job

The reporting mart is populated by:

```text
python -m data_pipeline.jobs.run_reporting_etl --snapshot-date YYYY-MM-DD
```

Default behavior:

- Syncs dimensions from OLTP (`public`) into `reporting.dim_*`.
- Rebuilds `reporting.fact_vulnerability_snapshot` for the given **`snapshot_date`** (delete + insert for that date).

Watermark table: `public.etl_watermarks` row `pipeline_name = 'reporting_daily'`.

## Contract

1. **Order:** Run ETL **before** Power BI scheduled refresh.
2. **Frequency:** Daily is sufficient for executive KPIs; increase only if OLTP changes intraday and stakeholders require DirectQuery.
3. **Failure handling:** If ETL fails, **do not** advance dataset refresh (or accept stale data — document in runbook). Monitor `last_success_at` in `etl_watermarks`.

## Suggested orchestration

| Scheduler | Job 1 | Job 2 |
|-----------|-------|-------|
| Windows Task / cron / Airflow | ETL for `snapshot_date = today()` in UTC or business TZ | Power BI REST **Refresh Dataset** or rely on Service scheduled refresh after delay |

Add a **15–30 minute** buffer after ETL completes before BI refresh to allow replication if using read replicas.

## Import vs DirectQuery refresh

| Mode | Refresh |
|------|---------|
| **Import** | Full table load per partition; use for `vw_fact_latest_snapshot` + dims at MVP scale. |
| **DirectQuery** | No dataset refresh; every visual sends SQL — tune indexes on `fact_vulnerability_snapshot (snapshot_date, bu_key, status)`. |

## Incremental future state

If fact history grows large:

- Split **Import** partitions by `snapshot_date` in Premium/Fabric, or
- Materialize monthly aggregates in PostgreSQL and point BI to summary tables (document in new ADR).

## View dependency

If the model uses `reporting.vw_fact_latest_snapshot`, refreshing Import reloads the view result set automatically; no separate refresh for the view.
