# Debug API Container Error

## Immediate Steps

### Step 1: Get the Exact Error

Run this in your terminal:

```powershell
docker logs aegiscore-api 2>&1
```

### Step 2: Common Fixes to Try

**Fix A: Database Connection Issue**
```powershell
# Check if DB is actually ready
docker compose exec db pg_isready -U postgres

# If not ready, restart DB
docker compose restart db

# Wait and create database
docker compose exec db createdb -U postgres aegiscore

# Then restart API
docker compose restart api
```

**Fix B: Environment Variables Missing**
```powershell
# Check if .env exists
cat .env

# Create minimal .env
@"
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@db:5432/aegiscore
SECRET_KEY=dev-secret-key-12345
REDIS_URL=redis://redis:6379/0
"@ | Out-File -FilePath .env -Encoding UTF8

# Restart with new env
docker compose down
docker compose up -d
```

**Fix C: Entrypoint Script Error**
```powershell
# Check entrypoint script inside container
docker run --rm aegiscore-platform-api cat /app/docker/scripts/api-entrypoint.sh

# Run API container with bash to debug
docker run -it --rm --network aegiscore-platform_aegiscore-network aegiscore-platform-api bash

# Inside container, test:
python -c "from app.db.session import engine; print('DB OK')"
python -c "from app.main import app; print('App OK')"
```

### Step 3: Manual Database Setup

If the API is failing because DB doesn't exist:

```powershell
# 1. Access DB container
docker compose exec db psql -U postgres

# 2. Inside PostgreSQL, run:
CREATE DATABASE aegiscore;
\q

# 3. Run migrations manually
docker compose run --rm api alembic upgrade head

# 4. Start API
docker compose up -d api
```

### Step 4: Nuclear Option (Complete Reset)

```powershell
# Destroy everything and start fresh
docker compose down -v
docker system prune -a --volumes -f

# Rebuild from scratch
docker compose build --no-cache api
docker compose up -d

# Check logs
docker logs -f aegiscore-api
```

### Step 5: Bypass Docker for API (Quick Dev Mode)

If Docker API keeps failing:

```powershell
# Terminal 1: Keep infrastructure
docker compose up -d db redis prometheus grafana

# Terminal 2: Run API locally
cd backend
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/aegiscore"
$env:SECRET_KEY = "dev-secret-key"
$env:REDIS_URL = "redis://localhost:6379/0"
uvicorn app.main:app --reload

# Terminal 3: Run frontend locally
cd frontend
npm run dev
```

## Get Error Output

**Copy and paste this command output:**

```powershell
docker logs aegiscore-api 2>&1 | Select-Object -First 30
```

This will show us the exact error message.

## Most Likely Causes

Based on the pattern, it's probably:

1. **Database not initialized** - Need to create `aegiscore` database
2. **Entrypoint script failing** - Migration or permission issue
3. **Import error** - Missing dependency in container

**Run the first command and share the error output!**
