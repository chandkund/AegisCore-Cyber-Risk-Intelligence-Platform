# Secrets management (production pattern)

## Principles

1. **Never** commit real credentials, JWT signing keys, or API keys to git.  
2. **Inject** secrets at runtime from a **secret store** or orchestrator-native secrets.  
3. **Rotate** credentials on a schedule and after incidents (see [runbooks](../runbooks/credential-rotation.md)).

## Azure (reference)

| Secret | Store | Consumer |
|--------|--------|----------|
| `JWT_SECRET_KEY` | Azure Key Vault secret | Container App / AKS pod (mounted or env from SecretProviderClass) |
| `DATABASE_URL` | Key Vault or AAD-authenticated connection string | API workload only |
| `POWERBI_CLIENT_SECRET` | Key Vault | Backend embed-token service (Phase 6 optional) |

### Key Vault integration (high level)

1. Create a Key Vault with **RBAC** or access policies.  
2. Enable **managed identity** on the API workload.  
3. Grant identity **Get** permission on required secrets.  
4. At startup, resolve secrets via **Azure SDK** or **Azure App Configuration** references (`@Microsoft.KeyVault(SecretUri=...)` in App Service / Container Apps).

### Local and CI

- **Local:** `.env` (gitignored) or shell exports.  
- **CI:** GitHub **encrypted secrets** / **environments** for staging and production deploy workflows (not used in the default open-source-style `ci.yml` beyond placeholder JWT for builds).

### Docker Compose

- Override `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, and `DATABASE_URL` for anything beyond a **single-developer laptop**.  
- Use `docker-compose.override.yml` (gitignored) for machine-specific mounts; never commit passwords into `docker-compose.override.example.yml`.
