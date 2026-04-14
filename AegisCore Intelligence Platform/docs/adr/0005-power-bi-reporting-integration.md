# ADR 0005: Power BI against PostgreSQL `reporting` schema

- **Status:** Accepted  
- **Date:** 2026-04-11  
- **Context:** Leadership needs executive dashboards; operational teams already have Next.js and FastAPI. The warehouse is the **`reporting`** star schema on PostgreSQL, filled by `run_reporting_etl`. We must avoid committing `.pbix` binaries and still deliver a reproducible BI story.

- **Decision:**
  1. **Connect Power BI** (Desktop + Service) to PostgreSQL using a **read-only** role scoped to schema **`reporting`**.
  2. **Default semantic model** uses **`reporting.vw_fact_latest_snapshot`** plus dimensions for a **latest-day** star; optional second fact for **full snapshot history** when trend pages are required.
  3. **Specifications** live under `powerbi/` (connection, model, DAX, dashboard pages, RLS, refresh contract, embedding notes). **PBIX** is built locally per `powerbi/pbix-build-checklist.md`.
  4. **Row-level security** is enforced in the **Power BI dataset** (DAX roles), not in PostgreSQL row policies, unless a future ADR introduces warehouse-side enforcement.
  5. **Scheduled refresh** (Import) runs **after** successful ETL; gateway used when the database is private to the cloud.

- **Consequences:**
  - **Pros:** Clear separation from OLTP connections; analysts follow one doc set; git stays text-only; aligns with ADR 0002.  
  - **Cons:** Model and reports require **manual or separate pipeline** to export Template.pbix / BPA automation if desired; embed flow needs Azure AD and secrets (documented, not fully coded in repo).  
  - **Follow-up:** Optional Fabric migration, composite models to REST for strict API parity, and `reporting_ro` creation in production IaC (Phase 7).
