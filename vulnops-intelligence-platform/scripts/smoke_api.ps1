# Black-box API smoke: GET /health and optionally GET /ready (needs PostgreSQL).
# Usage:
#   .\scripts\smoke_api.ps1
#   $env:API_BASE_URL = "http://localhost:8000"; .\scripts\smoke_api.ps1
#   $env:SKIP_READY = "1"; .\scripts\smoke_api.ps1
$ErrorActionPreference = "Stop"
$Base = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }
Write-Host "Smoke: GET $Base/health"
Invoke-WebRequest -Uri "$Base/health" -UseBasicParsing | Out-Null
if ($env:SKIP_READY -eq "1") {
    Write-Host "SKIP_READY=1 — skipping GET /ready"
    Write-Host "OK (health only)"
    exit 0
}
Write-Host "Smoke: GET $Base/ready"
Invoke-WebRequest -Uri "$Base/ready" -UseBasicParsing | Out-Null
Write-Host "OK (health + ready)"
