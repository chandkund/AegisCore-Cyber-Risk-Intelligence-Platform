# ADR 0003: FastAPI + HS256 JWT with DB-backed RBAC and opaque refresh tokens

- **Status:** Accepted
- **Date:** 2026-04-11
- **Context:** Phase 3 requires authenticated APIs, role separation (admin / analyst / manager), and recruiter-credible security hygiene without prematurely adopting an IdP.
- **Decision:**
  - **Access tokens:** JWT (PyJWT), HS256, short TTL; claims include `sub` and `typ=access` (roles in token are not trusted for authorization).
  - **Authorization:** On each protected request, load the user and **roles from PostgreSQL**; treat `admin` as super-role for RBAC checks.
  - **Refresh tokens:** Opaque random string; store **SHA-256 hash** in `refresh_tokens`; rotate on refresh; revoke on logout.
  - **Passwords:** `bcrypt` directly (avoid passlib + bcrypt incompatibility on newer Python/bcrypt combinations).
- **Consequences:**
  - **Pros:** Simple operations, clear interview narrative, aligns with existing schema.
  - **Cons:** HS256 requires strong `JWT_SECRET_KEY` rotation discipline; horizontal scaling benefits from Redis-backed token denylist later if access TTL grows.
  - **Follow-up:** OAuth2/OIDC enterprise IdP, asymmetric JWTs, Redis rate-limit store, and fine-grained scopes (Phase 7+).
