# Test runner script for AegisCore backend
# This script sets up environment variables and runs pytest

$ErrorActionPreference = "Stop"

# Set test environment variables
$env:PYTHONPATH = "AegisCore Intelligence Platform\backend"
$env:DATABASE_URL = "sqlite:///AegisCore Intelligence Platform/backend/test.db"
$env:AEGISCORE_TEST_DATABASE_URL = "sqlite:///AegisCore Intelligence Platform/backend/test.db"
$env:JWT_SECRET_KEY = "test-jwt-secret-key-32-chars-long!!"
$env:ML_INFERENCE_ENABLED = "false"
$env:APP_ENV = "test"
$env:LOG_LEVEL = "DEBUG"

Write-Host "Running AegisCore tests..." -ForegroundColor Green
Write-Host "Database: $env:DATABASE_URL" -ForegroundColor Cyan

# Run pytest with the specified arguments
python -m pytest "AegisCore Intelligence Platform\backend\tests\unit\test_security.py" -v --tb=short

Write-Host "Tests complete!" -ForegroundColor Green
