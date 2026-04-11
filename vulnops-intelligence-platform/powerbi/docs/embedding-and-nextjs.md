# Embedding in Next.js (optional)

Power BI **embedded analytics** lets the web app host a report iframe with a short-lived embed token. This is **optional**; many teams link out to `app.powerbi.com` for Phase 6.

## High-level flow

1. **Azure AD** app registration with Power BI API delegated or application permissions (tenant-dependent).
2. **Backend** (FastAPI or a small Node BFF) exchanges AAD token for **Power BI REST** access, calls **Generate Token** for the report/workspace.
3. **Frontend** uses [powerbi-client](https://github.com/microsoft/PowerBI-JavaScript) or an iframe `src` with embed URL + token.

## Repository environment variables

See root `.env.example`:

- `POWERBI_WORKSPACE_ID`
- `POWERBI_REPORT_ID`
- `POWERBI_TENANT_ID` (optional, for authority URL)
- `POWERBI_CLIENT_ID` / `POWERBI_CLIENT_SECRET` (app-only flow — never expose to browser)

**Do not** commit secrets. Production: Key Vault / CI variables.

## Security notes

- Embed tokens expire; refresh before expiry (client timer + silent backend call).
- Enforce **same user** or **RLS** so the embedded view matches the caller’s data scope.
- Prefer **App owns data** (service principal) for org dashboards, or **User owns data** for per-user OAuth — align with your InfoSec standard.

## Next.js integration sketch (not shipped in repo)

1. Add API route or FastAPI endpoint `POST /api/v1/integrations/powerbi/embed` (admin-only) returning `{ embedUrl, accessToken, expiration }`.
2. Lazy-load `powerbi-client` in a client component; call `powerbi.embed(domElement, config)`.

Full implementation is deferred to Phase 7 / a dedicated integration task to avoid blocking BI documentation.
