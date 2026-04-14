-- Latest snapshot: open findings count by business unit (for BI / quick QA).
CREATE OR REPLACE VIEW reporting.vw_open_findings_by_bu AS
SELECT
    dbu.code AS business_unit_code,
    dbu.name AS business_unit_name,
    COUNT(*) AS open_findings
FROM reporting.fact_vulnerability_snapshot f
JOIN reporting.dim_business_unit dbu ON dbu.bu_key = f.bu_key
WHERE f.snapshot_date = (SELECT MAX(snapshot_date) FROM reporting.fact_vulnerability_snapshot)
  AND f.status NOT IN ('REMEDIATED', 'FALSE_POSITIVE')
GROUP BY dbu.code, dbu.name;
