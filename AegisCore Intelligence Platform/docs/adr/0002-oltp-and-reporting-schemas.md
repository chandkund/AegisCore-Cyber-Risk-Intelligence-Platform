# ADR 0002: Separate `reporting` schema on the same PostgreSQL database

- **Status:** Accepted
- **Date:** 2026-04-11
- **Context:** We need a star-oriented model for Power BI and aggregate APIs without denormalizing the OLTP system of record.
- **Decision:** Keep **one PostgreSQL database** with `public` (OLTP) and **`reporting`** (dimensions + facts). ETL jobs refresh dimensions type-1 style and rebuild daily fact grains idempotently.
- **Consequences:**
  - **Pros:** Simpler local/early-prod ops than two clusters; FK-like integrity within `reporting`; clear boundary for BI connection strings and read-only roles.
  - **Cons:** Heavy analytical queries can still contend on the same instance until a read replica or warehouse is introduced.
  - **Follow-up:** Add `reporting_ro` role (Phase 3/7), materialized views if fact growth demands it, and optional second database when SLOs require isolation.
