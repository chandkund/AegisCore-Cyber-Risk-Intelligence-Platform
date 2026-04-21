# AegisCore - Complete Run Guide

This guide covers running the full AegisCore platform with all services.

---

## Prerequisites

### Required
- Docker Desktop 4.25+ (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.20+
- Git 2.40+
- 4GB+ free RAM
- 10GB+ free disk space

### Optional (for local development)
- Python 3.11+
- Node.js 18+
- VS Code or PyCharm

---

## Method 1: Docker Compose (EASIEST) ⭐

### Step 1: Navigate to Project

```powershell
cd "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform"
```

### Step 2: Create Environment File

```powershell
copy .env.example .env
```

Or create `.env` manually:

```bash
# Core settings
DEBUG=false
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=postgresql://postgres:postgres@db:5432/aegiscore
REDIS_URL=redis://redis:6379/0
ELASTICSEARCH_URL=http://elasticsearch:9200

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Monitoring
ENABLE_PROMETHEUS=true
ENABLE_GRAFANA=true
```

### Step 3: Start All Services

```powershell
# Build and start everything
docker compose up --build -d

# Or without build (if already built)
docker compose up -d
```

### Step 4: Verify Services

```powershell
# Check all services are running
docker compose ps

# View logs
docker compose logs -f

# Check specific service
docker compose logs -f api
```

### Step 5: Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **API** | http://localhost:8000/api/v1 | - |
| **Grafana** | http://localhost:3001 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |

### Step 6: Initialize Data (First Run)

```powershell
# Run database migrations
docker compose exec api alembic upgrade head

# Seed initial data (if seed script exists)
docker compose exec api python scripts/seed_data.py
```

### Step 7: Test the Platform

```powershell
# Test API health
curl http://localhost:8000/api/v1/health

# Test login (if auth is set up)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@platform.com","password":"admin123","company_code":"PLATFORM"}'
```

---

## Method 2: Local Development (Backend Only)

### Step 1: Setup Python Environment

```powershell
cd "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform\backend"

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
venv\Scripts\Activate.ps1

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Activate (Linux/Mac)
source venv/bin/activate
```

### Step 2: Install Dependencies

```powershell
# Install all requirements
pip install -r requirements/base.txt
pip install -r requirements/dev.txt

# Or install manually
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary redis elasticsearch
```

### Step 3: Start Infrastructure Services

```powershell
# Start only database and supporting services
docker compose up -d db redis elasticsearch

# Wait for database to be ready (30 seconds)
Start-Sleep -Seconds 30
```

### Step 4: Setup Database

```powershell
# Run migrations
alembic upgrade head

# Or create tables directly
python -c "
from app.db.session import engine
from app.models.oltp import Base
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
```

### Step 5: Start API Server

```powershell
# Option 1: With auto-reload (development)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Step 6: Run Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/e2e/test_full_scenarios.py -v
```

---

## Method 3: Full Local Development (Backend + Frontend)

### Terminal 1: Start Backend

```powershell
cd "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform\backend"
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Start Frontend

```powershell
cd "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform\frontend"

# Install dependencies
npm install

# Start dev server
npm run dev
```

### Terminal 3: Start Supporting Services

```powershell
cd "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform"
docker compose up -d db redis elasticsearch prometheus grafana
```

---

## Method 4: Production Deployment

### Using Docker Compose

```powershell
# Create production env
copy .env .env.production

# Edit .env.production with production values
notepad .env.production
```

```bash
# .env.production
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=secure-random-key-here
DATABASE_URL=postgresql://prod-user:prod-pass@prod-db:5432/aegiscore
REDIS_URL=redis://prod-redis:6379/0
ELASTICSEARCH_URL=http://prod-es:9200
```

```powershell
# Start production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Using Kubernetes

```powershell
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -n aegiscore
```

---

## Verification Steps

### 1. Health Check

```powershell
# Check API is running
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status": "healthy", "version": "1.0.0", "services": {...}}
```

### 2. Test Authentication

```powershell
# Register a user (if registration is open)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@company.com",
    "password": "SecurePass123!",
    "company_code": "TESTCO"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@company.com",
    "password": "SecurePass123!",
    "company_code": "TESTCO"
  }'
```

### 3. Test ML Features

```powershell
# Test prioritization
curl http://localhost:8000/api/v1/findings/prioritized

# Test search
curl "http://localhost:8000/api/v1/search?q=CVE-2023"

# Test assistant
curl -X POST http://localhost:8000/api/v1/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top risks?", "context": "security_review"}'
```

### 4. Check Monitoring

- **Grafana Dashboards**: http://localhost:3001
- **Prometheus Metrics**: http://localhost:9090
- **API Metrics**: http://localhost:8000/metrics

---

## Troubleshooting

### Issue: Docker fails to start

```powershell
# Check Docker is running
docker version

# Check compose is installed
docker compose version

# Reset Docker context
docker context use default
```

### Issue: Database connection error

```powershell
# Check database is running
docker compose ps db

# Check logs
docker compose logs db

# Reset database
docker compose down -v  # WARNING: Deletes all data
docker compose up -d db
```

### Issue: Port conflicts

```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill process
Stop-Process -Id <PID>

# Or change port in .env
API_PORT=8001
```

### Issue: Frontend can't connect to API

```powershell
# Check backend is running
curl http://localhost:8000/api/v1/health

# Check CORS settings in .env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Restart frontend
```

### Issue: Tests failing

```powershell
# Check database is up
docker compose ps db

# Check migrations
alembic current

# Run specific test with verbose output
pytest tests/e2e/test_full_scenarios.py::TestPlatformOwner::test_a1_owner_login -vvs
```

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AegisCore Platform                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Frontend   │  │     API      │  │  Assistant   │       │
│  │   (Next.js)  │  │   (FastAPI)  │  │   Service    │       │
│  │   :3000      │  │    :8000     │  │              │       │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘       │
│         │                 │                                  │
│         └─────────────────┼─────────────────┐                │
│                           │                 │                │
│  ┌──────────────┐  ┌─────┴──────┐  ┌──────┴──────┐         │
│  │   Redis      │  │  Postgres  │  │Elasticsearch│         │
│  │   :6379      │  │    :5432   │  │    :9200    │         │
│  └──────────────┘  └────────────┘  └─────────────┘         │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │  Prometheus  │  │   Grafana    │                        │
│  │   :9090      │  │    :3001     │                        │
│  └──────────────┘  └──────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Commands

```powershell
# Start everything
docker compose up -d

# Stop everything
docker compose down

# Restart API
docker compose restart api

# View API logs
docker compose logs -f api

# Rebuild API
docker compose build api
docker compose up -d api

# Database shell
docker compose exec db psql -U postgres -d aegiscore

# Redis CLI
docker compose exec redis redis-cli

# Clean everything (WARNING: deletes all data)
docker compose down -v
docker system prune -a
```

---

## Next Steps

After successful startup:

1. ✅ Open http://localhost:3000 (Frontend)
2. ✅ Check http://localhost:8000/docs (API docs)
3. ✅ Login with test credentials
4. ✅ Upload vulnerability data
5. ✅ Test ML features
6. ✅ Explore Grafana dashboards

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start all | `docker compose up -d` |
| Stop all | `docker compose down` |
| View logs | `docker compose logs -f` |
| Restart API | `docker compose restart api` |
| Rebuild | `docker compose up --build -d` |
| Clean data | `docker compose down -v` |
| Run tests | `docker compose exec api pytest` |

---

**You're ready to run AegisCore!** 🚀
