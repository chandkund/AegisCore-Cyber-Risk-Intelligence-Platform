# Semantic model specification

## Grain

- **Fact table grain:** one row per **`(snapshot_date, finding_oltp_id)`** in `reporting.fact_vulnerability_snapshot`.
- **Latest-snapshot shortcut:** model `FactSnapshotLatest` from `reporting.vw_fact_latest_snapshot` when the business only needs **one day** of truth (executive KPIs). Use the full fact table for **trend / snapshot-date** slicers.

## Recommended star (latest snapshot)

Suitable for parity with the Next.js **dashboard** (single point in time).

| Model table | Source | Role |
|-------------|--------|------|
| `Fact Snapshot` | `reporting.vw_fact_latest_snapshot` | Fact |
| `Dim Business Unit` | `reporting.dim_business_unit` | Dimension |
| `Dim Team` | `reporting.dim_team` | Dimension |
| `Dim Asset` | `reporting.dim_asset` | Dimension |
| `Dim CVE` | `reporting.dim_cve` | Dimension |
| `Dim Severity` | `reporting.dim_severity` | Dimension |
| `Dim Date` | `reporting.dim_date` | Dimension (join on `date_key`) |
| `Dim Assignee` | `reporting.dim_assignee_user` | Dimension |

## Relationships (single direction: dim → fact)

Power BI should use **single active relationships** from dimension surrogate keys to the fact:

| From (dimension) | Column | To (fact) | Column | Cardinality |
|------------------|--------|-----------|--------|-------------|
| Dim Business Unit | `bu_key` | Fact Snapshot | `bu_key` | Many-to-one |
| Dim Team | `team_key` | Fact Snapshot | `team_key` | Many-to-one |
| Dim Asset | `asset_key` | Fact Snapshot | `asset_key` | Many-to-one |
| Dim CVE | `cve_key` | Fact Snapshot | `cve_key` | Many-to-one |
| Dim Severity | `severity_key` | Fact Snapshot | `severity_key` | Many-to-one |
| Dim Date | `date_key` | Fact Snapshot | `date_key` | Many-to-one |
| Dim Assignee | `user_key` | Fact Snapshot | `assignee_user_key` | Many-to-one |

**Mark as hidden** in the model (client tools):

- All `*_key` columns and OLTP UUIDs used only for integrity (`asset_id`, `business_unit_id`, etc.) unless explicitly needed for drillthrough.

## Column reference (fact — selected)

| Column | Type (semantic) | Usage |
|--------|-----------------|--------|
| `snapshot_date` | Date | Filter (constant for latest view) |
| `status` | Text | Slicer, matrix rows |
| `days_open` | Whole number | Aging visuals |
| `is_overdue` | True/False | KPI / conditional formatting |
| `exploit_available` | True/False | Risk flag |
| `cvss_base_score` | Decimal | Aggregates (max/avg) |
| `epss_score` | Decimal | Risk context |

## Naming

- Use **Title Case** display folders: `Dimensions`, `Facts`, `Measures`, `Parameters`.
- Avoid loading OLTP `public` tables into the same dataset unless you have a documented operational reporting need (separate dataset recommended).

## Alternate model (time series)

Add the full `reporting.fact_vulnerability_snapshot` as `Fact Snapshot History`, relate to `Dim Date` on `date_key`, and add a **Snapshot Date** slicer. Use this for week-over-week open findings and overdue trends.
