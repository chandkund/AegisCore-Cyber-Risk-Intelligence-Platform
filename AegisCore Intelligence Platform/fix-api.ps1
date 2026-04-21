# AegisCore API Fix Script
# Run this to diagnose and fix API startup issues

Write-Host "=== AegisCore API Fix Script ===" -ForegroundColor Green

# Step 1: Get error logs
Write-Host "`n[1/6] Checking API error logs..." -ForegroundColor Yellow
$logs = docker logs aegiscore-api 2>&1
if ($logs) {
    Write-Host "ERROR LOGS:" -ForegroundColor Red
    $logs | Select-Object -First 20 | ForEach-Object { Write-Host $_ -ForegroundColor Red }
} else {
    Write-Host "No logs found" -ForegroundColor Gray
}

# Step 2: Check if database exists
Write-Host "`n[2/6] Checking database..." -ForegroundColor Yellow
docker compose exec -T db psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='aegiscore';" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Database 'aegiscore' not found. Creating..." -ForegroundColor Yellow
    docker compose exec -T db psql -U postgres -c "CREATE DATABASE aegiscore;" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Database created successfully!" -ForegroundColor Green
    } else {
        Write-Host "Failed to create database" -ForegroundColor Red
    }
} else {
    Write-Host "Database exists" -ForegroundColor Green
}

# Step 3: Check .env file
Write-Host "`n[3/6] Checking environment file..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    @"
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@db:5432/aegiscore
SECRET_KEY=dev-secret-key-$(Get-Random -Maximum 99999)
REDIS_URL=redis://redis:6379/0
ELASTICSEARCH_URL=http://elasticsearch:9200
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
"@ | Out-File -FilePath .env -Encoding UTF8
    Write-Host ".env file created" -ForegroundColor Green
} else {
    Write-Host ".env file exists" -ForegroundColor Green
}

# Step 4: Run migrations
Write-Host "`n[4/6] Running database migrations..." -ForegroundColor Yellow
docker compose run --rm api alembic upgrade head 2>&1 | ForEach-Object {
    if ($_ -match "error|Error|ERROR") {
        Write-Host $_ -ForegroundColor Red
    } else {
        Write-Host $_ -ForegroundColor Gray
    }
}

# Step 5: Restart API
Write-Host "`n[5/6] Restarting API container..." -ForegroundColor Yellow
docker compose down api 2>$null
docker compose up -d api 2>&1 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }

# Step 6: Check final status
Write-Host "`n[6/6] Checking final status..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$status = docker inspect --format='{{.State.Status}}' aegiscore-api 2>$null

if ($status -eq "running") {
    Write-Host "`n✅ SUCCESS! API is now running!" -ForegroundColor Green
    Write-Host "   API URL: http://localhost:8000/api/v1" -ForegroundColor Cyan
    Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    
    # Test health endpoint
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 5
        Write-Host "   Health Check: $($health.status)" -ForegroundColor Green
    } catch {
        Write-Host "   Health Check: Pending (API may still be starting)" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n❌ API is still not running" -ForegroundColor Red
    Write-Host "   Status: $status" -ForegroundColor Red
    Write-Host "`nLast 10 log lines:" -ForegroundColor Red
    docker logs --tail 10 aegiscore-api 2>&1 | ForEach-Object { Write-Host "   $_" -ForegroundColor Red }
    
    Write-Host "`n💡 Alternative: Run API locally instead:" -ForegroundColor Yellow
    Write-Host "   1. Keep infrastructure: docker compose up -d db redis" -ForegroundColor Cyan
    Write-Host "   2. Run API locally:" -ForegroundColor Cyan
    Write-Host "      cd backend" -ForegroundColor White
    Write-Host "      `$env:DATABASE_URL='postgresql://postgres:postgres@localhost:5432/aegiscore'" -ForegroundColor White
    Write-Host "      uvicorn app.main:app --reload" -ForegroundColor White
}

Write-Host "`n=== Done ===" -ForegroundColor Green
