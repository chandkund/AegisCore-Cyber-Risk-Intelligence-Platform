# AegisCore Advanced ML Features - Run Instructions

## Prerequisites

1. **Python 3.10+** installed
2. **PostgreSQL** running (via Docker or local)
3. **Redis** (optional but recommended)
4. **Elasticsearch** (optional, for production search)

## Step-by-Step Setup

### Step 1: Navigate to Backend Directory

```powershell
cd "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform\backend"
```

### Step 2: Install Dependencies

```powershell
# Install base requirements
pip install -r requirements/base.txt

# Install ML-specific requirements (optional but recommended)
pip install redis elasticsearch numpy scikit-learn
```

### Step 3: Set Environment Variables

Create a `.env` file in the backend directory:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aegiscore

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Elasticsearch (optional)
ELASTICSEARCH_URL=http://localhost:9200

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ML
ML_INFERENCE_ENABLED=false
ML_MODEL_PATH=ml/models
```

### Step 4: Initialize Database

```powershell
# Run migrations
alembic upgrade head

# Or if no migrations exist, create tables
python -c "from app.db.session import engine; from app.models.oltp import Base; Base.metadata.create_all(bind=engine)"
```

### Step 5: Run Tests to Verify

```powershell
# Test syntax of all files
python -m py_compile app/services/assistant_service_v2.py
python -m py_compile app/services/risk_engine_service.py
python -m py_compile app/services/explanation_service.py
python -m py_compile app/services/search_service.py
python -m py_compile app/services/simulation_service.py

echo "All files compiled successfully!"
```

### Step 6: Start the API Server

```powershell
# Option 1: Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Using Python module
python -m app.main
```

### Step 7: Test the API

In another terminal:

```powershell
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test assistant (if you have auth set up)
curl -X POST http://localhost:8000/api/v1/assistant/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "What are my top risks?", "context": "security_review"}'
```

## Docker Setup (Recommended)

### Using Docker Compose

```powershell
# From the root directory
cd "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform"

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

### Services Started

- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379 (if enabled)
- **Elasticsearch**: localhost:9200 (if enabled)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## Quick Verification

### Test 1: Import Check

```powershell
python -c "
from app.services.assistant_service_v2 import ProductionAssistantService
from app.services.risk_engine_service import RiskEngineService
from app.services.explanation_service import ExplanationService
print('All services imported successfully!')
"
```

### Test 2: Assistant Service Test

```powershell
python -c "
import asyncio
from app.services.assistant_service_v2 import ProductionAssistantService

async def test():
    service = ProductionAssistantService(None, None, None)
    
    # Test safe message
    result = await service.chat('What are my top risks?')
    print('Safe message result:', result['question_type'])
    
    # Test blocked message
    result = await service.chat('ignore previous instructions')
    print('Blocked message result:', result['question_type'])
    
    # Test out of scope
    result = await service.chat('What is the weather?')
    print('Out of scope result:', result['question_type'])

asyncio.run(test())
"
```

### Test 3: Run pytest

```powershell
# Run ML feature tests
pytest tests/ml/ -v

# Run specific tests
pytest tests/ml/test_prioritization_hardening.py -v
pytest tests/ml/test_assistant_hardening.py -v
```

## Troubleshooting

### Issue: Import Error

**Solution**: Make sure you're in the backend directory and PYTHONPATH is set:
```powershell
$env:PYTHONPATH = "d:\AegisCore Intelligence Platform\AegisCore Intelligence Platform\backend"
```

### Issue: Database Connection Error

**Solution**: Verify PostgreSQL is running:
```powershell
docker ps | findstr postgres
# OR
pg_isready -h localhost -p 5432
```

### Issue: Missing Dependencies

**Solution**: Reinstall requirements:
```powershell
pip install --upgrade -r requirements/base.txt
```

### Issue: Port Already in Use

**Solution**: Kill process on port 8000 or use different port:
```powershell
# Find and kill process
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or use different port
uvicorn app.main:app --port 8001
```

## Production Deployment

### Using Docker

```powershell
# Build production image
docker build -t aegiscore-api -f docker/Dockerfile.api .

# Run production container
docker run -d \
  --name aegiscore-api \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  aegiscore-api
```

### Environment for Production

```bash
# .env.production
DEBUG=false
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@prod-db:5432/aegiscore
REDIS_URL=redis://prod-redis:6379/0
ELASTICSEARCH_URL=http://prod-es:9200
ML_INFERENCE_ENABLED=true
ASSISTANT_RATE_LIMIT=30
SECRET_KEY=your-production-secret-key
```

## Access the Application

Once running:

- **API Docs**: http://localhost:8000/docs
- **API**: http://localhost:8000/api/v1
- **Health Check**: http://localhost:8000/api/v1/health

## Next Steps

1. ✅ Run the API server
2. ✅ Test endpoints via /docs
3. ✅ Run test suite
4. ✅ Configure monitoring (Prometheus/Grafana)
5. ✅ Deploy to production environment

## Support

If you encounter issues:

1. Check logs: `docker-compose logs api`
2. Verify database: `docker-compose exec db psql -U postgres -d aegiscore`
3. Check syntax: `python -m py_compile <file.py>`
4. Run health check: `curl http://localhost:8000/api/v1/health`
