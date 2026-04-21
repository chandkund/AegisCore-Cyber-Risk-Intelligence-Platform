# AegisCore - Quick Start Guide

**Get the entire platform running in 5 minutes**

---

## Prerequisites

| Requirement | Version | Download |
|-------------|---------|----------|
| Docker Desktop | 4.25+ | [docker.com](https://www.docker.com/products/docker-desktop) |
| Git | 2.40+ | [git-scm.com](https://git-scm.com) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) (for local dev) |
| Python | 3.11+ | [python.org](https://python.org) (for local dev) |

**Verify installation:**
```bash
docker --version  # Docker version 24.0+
docker compose version  # Docker Compose v2.20+
git --version
```

---

## Method 1: Docker Compose (Recommended) ⭐

**Fastest way - runs everything with one command**

### Step 1: Clone & Configure

```bash
# Clone the repository
git clone <repository-url>
cd "AegisCore Intelligence Platform"

# Copy environment file
copy .env.example .env

# (Optional) Edit .env for custom settings
# Default values work out of the box
```

### Step 2: Start All Services

```bash
# Build and start all services
docker compose up --build -d

# Wait for services to be healthy (~2 minutes)
# You'll see: ✔ Container aegiscore-api Healthy
```

### Step 3: Access the Application

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **Web App** | http://localhost:3000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **Health Check** | http://localhost:8000/health | - |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3001 | admin / admin |

### Step 4: Login

**Default test accounts:**
```
Platform Owner:
  Email: platform@aegiscore.local
  Password: (auto-generated, check API logs)

Admin:
  Email: admin@aegiscore.local
  Password: AegisCore!demo2026

Analyst:
  Email: analyst@aegiscore.local
  Password: AegisCore!demo2026
```

---

## Method 2: Local Development (Advanced)

**Run backend and frontend separately for development**

### Terminal 1: Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Setup database (PostgreSQL must be running)
alembic upgrade head

# Start API server
python -m app.main

# API running at: http://localhost:8000
```

### Terminal 2: Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# App running at: http://localhost:3000
```

---

## Common Commands

### Docker Compose Operations

```bash
# View logs
docker compose logs -f api           # API logs
docker compose logs -f web          # Frontend logs
docker compose logs -f              # All logs

# Restart a service
docker compose restart api
docker compose restart web

# Stop everything
docker compose down

# Stop and remove all data (clean slate)
docker compose down -v

# Run database migrations
docker compose exec api alembic upgrade head

# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Shell into API container
docker compose exec api bash

# Run tests
docker compose exec api python -m pytest
```

### Database Operations

```bash
# Reset database (WARNING: loses all data)
docker compose down -v
docker compose up -d postgres
docker compose exec api alembic upgrade head

# Backup database
docker compose exec postgres pg_dump -U aegiscore aegiscore > backup.sql

# Restore database
docker compose exec -T postgres psql -U aegiscore aegiscore < backup.sql
```

---

## Troubleshooting

### Issue: "Ports already in use"

```bash
# Find what's using port 3000 or 8000
netstat -ano | findstr :3000

# Kill the process or use different ports in .env:
echo "WEB_PUBLISH_PORT=3001" >> .env
echo "API_PUBLISH_PORT=8001" >> .env
docker compose up -d
```

### Issue: "Database connection failed"

```bash
# Check if postgres is healthy
docker compose ps

# Reset and start fresh
docker compose down -v
docker compose up -d postgres
sleep 10  # Wait for postgres
docker compose up -d api
```

### Issue: "API container keeps restarting"

```bash
# Check logs
docker compose logs api

# Common fixes:
# 1. JWT_SECRET_KEY not set
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# 2. Database not ready
docker compose restart api

# 3. Check health endpoint
curl http://localhost:8000/health
```

### Issue: "Frontend can't connect to API"

```bash
# Check API is running
curl http://localhost:8000/health

# Check environment variable
docker compose exec web env | grep API

# Should show: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Development Workflow

### Day-to-Day Development

```bash
# 1. Start all services
docker compose up -d

# 2. Watch logs while developing
docker compose logs -f api

# 3. Make code changes (hot reload works)

# 4. Run tests before committing
docker compose exec api python -m pytest

# 5. Stop when done
docker compose down
```

### Running Tests

```bash
# Unit tests
docker compose exec api python -m pytest backend/tests/unit -v

# Integration tests
docker compose exec api python -m pytest backend/tests/integration -v

# E2E tests
docker compose exec api python -m pytest backend/tests/e2e -v

# All tests with coverage
docker compose exec api python -m pytest --cov=app --cov-report=html

# Specific test file
docker compose exec api python -m pytest backend/tests/unit/test_security.py -v
```

### Code Quality Checks

```bash
# Install pre-commit (run once)
pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run specific check
pre-commit run black --all-files
pre-commit run ruff --all-files
```

---

## Environment Configuration

### Required Environment Variables

```env
# Database
DATABASE_URL=postgresql+psycopg://aegiscore:aegiscore_local_dev_only@postgres:5432/aegiscore

# Security (MUST change in production)
JWT_SECRET_KEY=your-secret-key-min-32-characters-long

# CORS (for local development)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email (development uses console)
EMAIL_PROVIDER=console

# Logging
LOG_LEVEL=INFO
LOG_JSON=false
```

### Optional Environment Variables

```env
# Ports (change if conflicts)
POSTGRES_PUBLISH_PORT=5432
REDIS_PUBLISH_PORT=6379
API_PUBLISH_PORT=8000
WEB_PUBLISH_PORT=3000

# External Services (production)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Redis (for caching)
REDIS_URL=redis://redis:6379/0

# Monitoring
PROMETHEUS_METRICS_ENABLED=true
OTEL_SERVICE_NAME=aegiscore-api
```

---

## Production Deployment

### Prerequisites
- AWS Account with appropriate permissions
- Terraform 1.5+
- Docker Hub or ECR access

### Deploy to AWS

```bash
cd infrastructure/terraform/environments/production

# Initialize terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply (costs incurred)
terraform apply tfplan
```

**See**: `docs/deployment/AWS_DEPLOYMENT.md` for detailed production setup.

---

## Project Structure Overview

```
AegisCore Intelligence Platform/
├── backend/              # FastAPI Python backend
│   ├── app/             # Application code
│   ├── tests/           # Test suites
│   ├── alembic/         # Database migrations
│   └── requirements.txt # Python dependencies
├── frontend/            # Next.js React frontend
│   ├── src/            # Source code
│   ├── public/         # Static assets
│   └── package.json    # Node dependencies
├── infrastructure/     # Terraform IaC
│   └── terraform/
├── monitoring/        # Prometheus & Grafana configs
├── docker/            # Dockerfiles
├── docs/              # Documentation
├── docker-compose.yml # Local development stack
└── .env.example       # Environment template
```

---

## Next Steps

### After successful startup:

1. **Login as Platform Owner**
   - URL: http://localhost:3000/platform
   - Check API logs for auto-generated password

2. **Create a Tenant**
   - Platform Dashboard → Tenants → Create

3. **Add Users**
   - Invite team members with roles

4. **Import Assets**
   - Use CSV upload or API

5. **Explore Features**
   - Vulnerability scanning
   - Risk prioritization
   - Compliance reporting

---

## Getting Help

| Resource | Location |
|----------|----------|
| **Documentation** | `docs/` directory |
| **API Docs** | http://localhost:8000/docs |
| **Architecture** | `docs/ARCHITECTURE.md` |
| **Troubleshooting** | `docs/runbooks/` |
| **Security** | `docs/compliance/` |

**Issues?** Check the troubleshooting section above or review logs with `docker compose logs`.

---

**Happy building!** 🚀

The entire AegisCore platform is now running locally with:
- ✅ PostgreSQL 16 database
- ✅ Redis 7 cache
- ✅ FastAPI backend
- ✅ Next.js frontend
- ✅ Prometheus metrics
- ✅ Grafana dashboards
- ✅ All security features active
