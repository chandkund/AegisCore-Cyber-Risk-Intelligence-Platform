# Power BI — AegisCore Intelligence (Phase 6)

This folder is the **engineering specification** for connecting Microsoft Power BI to the PostgreSQL **`reporting`** star schema populated by `data_pipeline.jobs.run_reporting_etl`. It does **not** commit `.pbix` binaries (binary merge conflicts, licensing); analysts build the dataset in Power BI Desktop using the docs below.

## Contents

| Document | Purpose |
|----------|---------|
| [docs/connection-parameters.md](docs/connection-parameters.md) | Server, database, schema, credentials, gateway, Import vs DirectQuery |
| [docs/semantic-model-specification.md](docs/semantic-model-specification.md) | Tables, relationships, keys, modeling conventions |
| [docs/dax-measures.md](docs/dax-measures.md) | Reusable measures aligned with API `/analytics` semantics |
| [docs/dashboard-pages-spec.md](docs/dashboard-pages-spec.md) | Executive page layout and visuals (parity with Next.js analytics) |
| [docs/governance-security-rls.md](docs/governance-security-rls.md) | Workspace, sharing, RLS patterns, service principals |
| [docs/refresh-and-etl-contract.md](docs/refresh-and-etl-contract.md) | Schedule ordering: ETL before dataset refresh |
| [docs/embedding-and-nextjs.md](docs/embedding-and-nextjs.md) | Secure embed, Azure AD, env vars for optional in-app reports |
| [pbix-build-checklist.md](pbix-build-checklist.md) | Step-by-step Desktop checklist |

## Prerequisites

1. PostgreSQL reachable from Power BI (Desktop: direct; Service: **on-premises data gateway** if not cloud-hosted).
2. At least one successful ETL run so `reporting.fact_vulnerability_snapshot` is non-empty for visual QA.
3. Optional view: `database/views/002_vw_fact_latest_snapshot.sql` applied for a **single latest snapshot** fact table in the model.

## Quick verify (SQL)

Run `scripts/verify_reporting_prereqs.sql` in your SQL client before publishing the dataset.

## Architecture reference

- [ADR 0002 — OLTP vs reporting](../docs/adr/0002-oltp-and-reporting-schemas.md)
- [ADR 0005 — Power BI integration](../docs/adr/0005-power-bi-reporting-integration.md)
- [System architecture — BI layer](../docs/architecture/system-architecture.md)
