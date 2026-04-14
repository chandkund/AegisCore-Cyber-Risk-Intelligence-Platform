# Power BI Desktop — build checklist

Use this list to produce **`AegisCore-Executive-Risk.pbix`** locally (file stays out of git).

## Before you start

- [ ] PostgreSQL `reporting` schema exists (Alembic / DDL).
- [ ] ETL run completed for at least one date.
- [ ] Applied `database/views/002_vw_fact_latest_snapshot.sql` (optional but recommended).
- [ ] Ran `powerbi/scripts/verify_reporting_prereqs.sql` — dimensions non-zero where expected.

## Model

- [ ] Get Data → PostgreSQL → connect with `reporting_ro` (or dev user).
- [ ] Load tables: `vw_fact_latest_snapshot` (rename to **Fact Snapshot**), all `dim_*` tables per [semantic-model-specification.md](docs/semantic-model-specification.md).
- [ ] Set relationships (single direction, many-to-one into fact).
- [ ] Hide surrogate keys and internal UUIDs.
- [ ] Add measures from [dax-measures.md](docs/dax-measures.md).

## Report

- [ ] Build pages per [dashboard-pages-spec.md](docs/dashboard-pages-spec.md).
- [ ] Set **Phone layout** for summary page.
- [ ] Add **Reset** bookmark.

## Publish

- [ ] Publish to `AegisCore — Production` workspace.
- [ ] Configure **Scheduled refresh** (Import) **after** ETL window; set gateway if needed.
- [ ] Configure **RLS** roles per [governance-security-rls.md](docs/governance-security-rls.md).
- [ ] Certify dataset (if policy allows).

## Validation

- [ ] Cross-check **Open Findings** card vs `reporting.vw_open_findings_by_bu` totals (sum of BU rows vs distinct findings — definitions may differ slightly; document variance).
- [ ] Export PDF snapshot for change control archive (optional).
