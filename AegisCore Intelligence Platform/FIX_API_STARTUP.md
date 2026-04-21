# Fix API Container Startup Error

## Step 1: Check Error Logs

Run this to see why the API failed:

```powershell
# Check API container logs
docker logs aegiscore-api

# Check last 50 lines
docker logs --tail 50 aegiscore-api

# Follow logs in real-time
docker logs -f aegiscore-api
```

## Step 2: Common Issues & Fixes

### Issue 1: Database Connection Error

**Symptom:** `sqlalchemy.exc.OperationalError: connection refused`

**Fix:**
```powershell
# Wait for database to be ready
docker compose restart api

# Or check if DB is healthy
docker compose ps db
```

### Issue 2: Missing Environment Variables

**Fix:**
```powershell
# Create .env file if not exists
copy .env.example .env

# Edit .env
notepad .env
```

Add these minimum settings:
```bash
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@db:5432/aegiscore
SECRET_KEY=your-secret-key-here-for-development
```

### Issue 3: Database Not Initialized

**Fix:**
```powershell
# Initialize database
docker compose exec db psql -U postgres -c "CREATE DATABASE aegiscore;"

# Run migrations
docker compose exec api alembic upgrade head

# Or create tables directly
docker compose exec api python -c "
from app.db.session import engine
from app.models.oltp import Base
Base.metadata.create_all(bind=engine)
print('Tables created')
"
```

### Issue 4: Port Conflict

**Fix:**
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Stop conflicting process or change port in docker-compose.yml
```

## Step 3: Quick Fix Script

Run this complete fix:

```powershell
# 1. Stop all containers
docker compose down

# 2. Remove old volumes (WARNING: deletes data)
docker volume rm aegiscore-platform_aegiscore_pgdata 2>$null

# 3. Start fresh
docker compose up -d db redis

# 4. Wait for DB
Start-Sleep -Seconds 10

# 5. Check DB is ready
docker compose exec db pg_isready -U postgres

# 6. Start API
docker compose up -d api

# 7. Check logs if it fails again
docker logs aegiscore-api --tail 30
```

## Step 4: Manual Database Setup

If migrations fail, manually create the database:

```powershell
# Access database container
docker compose exec db psql -U postgres

# Inside PostgreSQL:
CREATE DATABASE aegiscore;
\q

# Run API container with shell to debug
docker compose run --rm api bash

# Inside API container, test DB connection
python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:postgres@db:5432/aegiscore')
conn = engine.connect()
print('DB Connected!')
conn.close()
"
```

## Step 5: Alternative - Local Mode

If Docker keeps failing, run locally:

```powershell
# 1. Start only infrastructure
docker compose up -d db redis

# 2. Run API locally
cd backend
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/aegiscore"
$env:SECRET_KEY="dev-secret-key"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Check Current Status

```powershell
# Check all containers
docker compose ps

# Check specific service
docker compose ps api

# Check health
docker inspect --format='{{.State.Health.Status}}' aegiscore-api
```

## Most Likely Fix

The error is probably one of these:

1. **Database not ready when API started**
   ```powershell
   docker compose restart api
   ```

2. **Missing database**
   ```powershell
   docker compose exec db createdb -U postgres aegiscore
   docker compose exec api alembic upgrade head
   ```

3. **Entrypoint script error**
   ```powershell
   # Check entrypoint script
docker compose exec api cat /app/docker/scripts/api-entrypoint.sh
   ```

## Get Help

If none of these work, run this and share the output:

```powershell
docker logs aegiscore-api 2>&1 | Select-Object -First 50
```
