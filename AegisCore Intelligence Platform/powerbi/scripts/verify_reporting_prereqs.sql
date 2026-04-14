-- Run against the same database used by DATABASE_URL (OLTP + reporting schema).
-- Expect non-zero row counts on dimensions after ETL; fact may be empty until first snapshot.

SELECT 'reporting.dim_business_unit' AS relation, COUNT(*)::bigint AS n FROM reporting.dim_business_unit
UNION ALL SELECT 'reporting.dim_team', COUNT(*)::bigint FROM reporting.dim_team
UNION ALL SELECT 'reporting.dim_asset', COUNT(*)::bigint FROM reporting.dim_asset
UNION ALL SELECT 'reporting.dim_cve', COUNT(*)::bigint FROM reporting.dim_cve
UNION ALL SELECT 'reporting.dim_severity', COUNT(*)::bigint FROM reporting.dim_severity
UNION ALL SELECT 'reporting.dim_date', COUNT(*)::bigint FROM reporting.dim_date
UNION ALL SELECT 'reporting.dim_assignee_user', COUNT(*)::bigint FROM reporting.dim_assignee_user
UNION ALL SELECT 'reporting.fact_vulnerability_snapshot', COUNT(*)::bigint FROM reporting.fact_vulnerability_snapshot
ORDER BY 1;

SELECT MAX(snapshot_date) AS latest_snapshot_date
FROM reporting.fact_vulnerability_snapshot;
