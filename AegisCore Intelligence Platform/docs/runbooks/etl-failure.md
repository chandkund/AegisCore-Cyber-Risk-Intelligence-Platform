# Runbook: Reporting ETL failure

## Symptoms

- Power BI or internal reports show **stale** `snapshot_date`.  
- `SELECT * FROM etl_watermarks WHERE pipeline_name = 'reporting_daily'` shows `last_success_at` older than expected.  
- ETL job exits non-zero in scheduler logs.

## Immediate checks

1. Confirm **database** reachable from the ETL runner (`DATABASE_URL`).  
2. Re-run manually from repo root:  
   `python -m data_pipeline.jobs.run_reporting_etl --snapshot-date YYYY-MM-DD`  
3. Inspect PostgreSQL logs for **deadlock** or **disk full**.

## Common causes

| Cause | Mitigation |
|-------|------------|
| OLTP migration not applied | Run `alembic upgrade head` in `backend/`, then re-run ETL. |
| Invalid snapshot date (future) | Use UTC business date agreed with security ops. |
| Dimension sync conflict | Check for orphaned `assets.business_unit_id` violating FK expectations. |

## Communication

- Notify **analytics consumers** if data is >1 business day stale.  
- Pause **Power BI scheduled refresh** if repeated failures waste gateway quota (see [pbi-refresh-failure.md](pbi-refresh-failure.md)).

## Recovery

1. Fix root cause.  
2. Run ETL for the **missed date(s)** in order if downstream assumes monotonic snapshots.  
3. Validate row counts: `powerbi/scripts/verify_reporting_prereqs.sql`.  
4. Re-enable BI refresh.
