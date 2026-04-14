# Docker images

| File | Image |
|------|--------|
| [Dockerfile.api](Dockerfile.api) | FastAPI + Alembic entrypoint; non-root user `aegiscore` (UID 10001). |
| [Dockerfile.frontend](Dockerfile.frontend) | Next.js **standalone** production server; non-root `nextjs` (UID 1001). |
| [scripts/api-entrypoint.sh](scripts/api-entrypoint.sh) | `alembic upgrade head` then `uvicorn`. |

Build from **repository root** (same as Compose `context: .`):

```bash
docker build -f docker/Dockerfile.api -t aegiscore-api:local .
docker build -f docker/Dockerfile.frontend -t aegiscore-web:local .
```

Full stack: see root [docker-compose.yml](../docker-compose.yml).

**Image tags:** production should pin **immutable digests** or patch-level tags; [Dependabot](../.github/dependabot.yml) can propose base-image bumps for `docker/Dockerfile.*`.
