# Runbook: Credential rotation

## JWT signing key (`JWT_SECRET_KEY`)

**Impact:** All existing access and refresh tokens become invalid when the key changes (users must sign in again).

### Steps

1. Generate a new random secret (≥32 characters), e.g. `openssl rand -hex 32`.  
2. Store in secret manager under a **new** secret version.  
3. Deploy API with updated env **during a maintenance window** if you cannot tolerate mass logout.  
4. Invalidate outstanding refresh tokens in DB if your policy requires (`refresh_tokens` table truncate or per-user revoke) — optional depending on threat model.

## PostgreSQL application user

1. Create new password in vault.  
2. `ALTER USER vulnops PASSWORD '...'` (use secure session).  
3. Update **gateway** / **Compose** / **K8s secret** references.  
4. Rolling restart API pods so pools pick up new DSN if embedded in connection string.

## Read-only BI user (`reporting_ro`)

1. Create parallel user `reporting_ro_v2`, grant same `SELECT` on `reporting`.  
2. Update Power BI data source credentials to `reporting_ro_v2`.  
3. After one successful refresh cycle, drop old role login or rotate password on old user.

## Document

Record rotation date and ticket ID in your security ticketing system.
