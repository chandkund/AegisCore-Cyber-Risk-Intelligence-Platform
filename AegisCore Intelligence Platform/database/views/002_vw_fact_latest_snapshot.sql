-- Latest daily snapshot only (convenient default for Import/DirectQuery semantic models).
-- When no facts exist, the view returns zero rows.
CREATE OR REPLACE VIEW reporting.vw_fact_latest_snapshot AS
SELECT f.*
FROM reporting.fact_vulnerability_snapshot f
WHERE f.snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM reporting.fact_vulnerability_snapshot
);
