# AegisCore Intelligence Platform - Production Startup Script
# This script handles proper startup including database migrations

param(
    [switch]$Rebuild,
    [switch]$Fresh,
    [switch]$SkipMigration
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 AegisCore Intelligence Platform - Startup Script" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Step 1: Full cleanup if requested
if ($Fresh) {
    Write-Host "`n📦 Step 1: Fresh start - cleaning everything..." -ForegroundColor Yellow
    docker compose down -v
    docker system prune -f
    docker volume rm aegiscore_pgdata aegiscore_uploads 2>$null
    Write-Host "✅ Cleanup complete" -ForegroundColor Green
}

# Step 2: Build containers
if ($Rebuild -or $Fresh) {
    Write-Host "`n🔨 Step 2: Building containers (no cache)..." -ForegroundColor Yellow
    docker compose build --no-cache api web
    Write-Host "✅ Build complete" -ForegroundColor Green
}

# Step 3: Start PostgreSQL
Write-Host "`n🐘 Step 3: Starting PostgreSQL..." -ForegroundColor Yellow
docker compose up -d postgres

# Wait for postgres to be healthy
Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Cyan
$attempts = 0
$maxAttempts = 30
while ($attempts -lt $maxAttempts) {
    $status = docker inspect --format='{{.State.Health.Status}}' aegiscore-intelligence-platform-postgres-1 2>$null
    if ($status -eq "healthy") {
        Write-Host "✅ PostgreSQL is healthy" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 2
    $attempts++
    Write-Host "  Attempt $attempts/$maxAttempts..." -ForegroundColor Gray
}

if ($attempts -eq $maxAttempts) {
    Write-Host "❌ PostgreSQL failed to start" -ForegroundColor Red
    exit 1
}

# Step 4: Apply database migrations manually if not skipped
if (-not $SkipMigration) {
    Write-Host "`n🗄️ Step 4: Applying database schema..." -ForegroundColor Yellow
    
    # Add columns for risk prioritization
    $sql = @"
ALTER TABLE vulnerability_findings 
ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS risk_factors JSONB,
ADD COLUMN IF NOT EXISTS risk_calculated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_findings_risk_score ON vulnerability_findings(risk_score);

ALTER TABLE assets 
ADD COLUMN IF NOT EXISTS is_external BOOLEAN DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_assets_is_external ON assets(is_external);

-- Ensure alembic version is correct
DELETE FROM alembic_version WHERE version_num = '0002';
INSERT INTO alembic_version (version_num) VALUES ('0002')
ON CONFLICT (version_num) DO NOTHING;
"@
    
    docker exec aegiscore-intelligence-platform-postgres-1 psql -U aegiscore -d aegiscore -c $sql 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database schema updated" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Database schema may already be up to date" -ForegroundColor Yellow
    }
}

# Step 5: Start API
Write-Host "`n🔌 Step 5: Starting API..." -ForegroundColor Yellow
docker compose up -d api

# Wait for API to be healthy
Write-Host "⏳ Waiting for API to be ready..." -ForegroundColor Cyan
$attempts = 0
while ($attempts -lt 60) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.status -eq "healthy" -or $response.status -eq "ok") {
            Write-Host "✅ API is healthy" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    Start-Sleep -Seconds 2
    $attempts++
    if ($attempts % 10 -eq 0) {
        Write-Host "  Attempt $attempts/60..." -ForegroundColor Gray
    }
}

if ($attempts -eq 60) {
    Write-Host "❌ API failed to start. Check logs:" -ForegroundColor Red
    docker logs aegiscore-intelligence-platform-api-1 --tail 50
    exit 1
}

# Step 6: Start Web
Write-Host "`n🌐 Step 6: Starting Web Frontend..." -ForegroundColor Yellow
docker compose up -d web

# Wait for web to be ready
Write-Host "⏳ Waiting for Web to be ready..." -ForegroundColor Cyan
$attempts = 0
while ($attempts -lt 30) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -Method HEAD -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Web is ready" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    Start-Sleep -Seconds 2
    $attempts++
}

# Step 7: Display status
Write-Host "`n✨ AegisCore is now running!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "📊 API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "🔌 API Base:     http://localhost:8000" -ForegroundColor White
Write-Host "🌐 Frontend:     http://localhost:3000" -ForegroundColor White
Write-Host "`n🔑 Test Login:" -ForegroundColor Yellow
Write-Host "   Email:    admin@aegiscore.local" -ForegroundColor White
Write-Host "   Password: AegisCore!demo2026" -ForegroundColor White
Write-Host "`n📋 Useful Commands:" -ForegroundColor Yellow
Write-Host "   View API logs:    docker logs aegiscore-intelligence-platform-api-1 -f" -ForegroundColor Gray
Write-Host "   View DB logs:     docker logs aegiscore-intelligence-platform-postgres-1 -f" -ForegroundColor Gray
Write-Host "   Stop services:    docker compose down" -ForegroundColor Gray
Write-Host "   Full reset:       .\start-aegiscore.ps1 -Fresh" -ForegroundColor Gray
