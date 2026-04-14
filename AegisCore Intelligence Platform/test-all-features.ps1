# AegisCore Intelligence Platform - Complete Feature Testing Script
# Tests all 5 AI features one by one with detailed output

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:3000"
)

$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Header = "Magenta"
}

function Write-TestHeader($text) {
    Write-Host "`n========================================" -ForegroundColor $Colors.Header
    Write-Host $text -ForegroundColor $Colors.Header
    Write-Host "========================================" -ForegroundColor $Colors.Header
}

function Write-TestStep($step, $description) {
    Write-Host "`n[$step] $description" -ForegroundColor $Colors.Info
}

function Write-Success($text) {
    Write-Host "✅ $text" -ForegroundColor $Colors.Success
}

function Write-Error($text) {
    Write-Host "❌ $text" -ForegroundColor $Colors.Error
}

function Write-Warning($text) {
    Write-Host "⚠️ $text" -ForegroundColor $Colors.Warning
}

# Global variables
$script:AccessToken = $null
$script:TestResults = @()

# ============================================
# TEST 1: Health Check & Basic Connectivity
# ============================================
Write-TestHeader "TEST 1: Health Check & Basic Connectivity"

try {
    Write-TestStep "1.1" "Testing API health endpoint"
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 10
    if ($health.status -eq "healthy" -or $health.status -eq "ok") {
        Write-Success "API is healthy - Status: $($health.status)"
        $script:TestResults += @{ Test = "Health Check"; Status = "PASS"; Details = $health.status }
    } else {
        Write-Warning "API returned unexpected status: $($health.status)"
        $script:TestResults += @{ Test = "Health Check"; Status = "WARN"; Details = $health.status }
    }
} catch {
    Write-Error "Health check failed: $_"
    $script:TestResults += @{ Test = "Health Check"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "1.2" "Testing API docs endpoint"
    $docs = Invoke-WebRequest -Uri "$BaseUrl/docs" -Method GET -TimeoutSec 10
    if ($docs.StatusCode -eq 200) {
        Write-Success "API docs accessible at $BaseUrl/docs"
        $script:TestResults += @{ Test = "API Docs"; Status = "PASS"; Details = "HTTP 200" }
    }
} catch {
    Write-Error "API docs not accessible: $_"
    $script:TestResults += @{ Test = "API Docs"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "1.3" "Testing Frontend accessibility"
    $web = Invoke-WebRequest -Uri $FrontendUrl -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($web.StatusCode -eq 200) {
        Write-Success "Frontend accessible at $FrontendUrl"
        $script:TestResults += @{ Test = "Frontend"; Status = "PASS"; Details = "HTTP 200" }
    }
} catch {
    Write-Error "Frontend not accessible: $_"
    $script:TestResults += @{ Test = "Frontend"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 2: Authentication
# ============================================
Write-TestHeader "TEST 2: Authentication System"

try {
    Write-TestStep "2.1" "Testing login with valid credentials"
    $loginBody = @{
        email = "admin@aegiscore.local"
        password = "AegisCore!demo2026"
    } | ConvertTo-Json
    
    $loginResponse = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $loginBody -TimeoutSec 10
    
    if ($loginResponse.access_token) {
        $script:AccessToken = $loginResponse.access_token
        Write-Success "Login successful - Token received (length: $($script:AccessToken.Length))"
        $script:TestResults += @{ Test = "Login"; Status = "PASS"; Details = "Token received" }
    } else {
        Write-Error "Login succeeded but no token received"
        $script:TestResults += @{ Test = "Login"; Status = "FAIL"; Details = "No token" }
    }
} catch {
    Write-Error "Login failed: $_"
    $script:TestResults += @{ Test = "Login"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "2.2" "Testing /me endpoint with valid token"
    $me = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/me" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10
    Write-Success "Me endpoint working - User: $($me.email)"
    $script:TestResults += @{ Test = "Me Endpoint"; Status = "PASS"; Details = "User: $($me.email)" }
} catch {
    Write-Error "Me endpoint failed: $_"
    $script:TestResults += @{ Test = "Me Endpoint"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 3: Auto-Prioritization Engine
# ============================================
Write-TestHeader "TEST 3: FEATURE 1 - Auto-Prioritization Engine"

try {
    Write-TestStep "3.1" "Testing GET /prioritization/findings endpoint"
    $findings = Invoke-RestMethod -Uri "$BaseUrl/api/v1/prioritization/findings?limit=5" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 15
    
    if ($findings.items -and $findings.items.Count -gt 0) {
        $firstFinding = $findings.items[0]
        Write-Success "Prioritized findings retrieved - Count: $($findings.items.Count)"
        
        # Check if risk_score exists
        if ($firstFinding.risk_score -ne $null) {
            Write-Success "Risk score present on findings - Score: $($firstFinding.risk_score)"
            $script:TestResults += @{ Test = "Prioritization API"; Status = "PASS"; Details = "$($findings.items.Count) findings with risk scores" }
        } else {
            Write-Warning "Findings retrieved but no risk_score field present"
            $script:TestResults += @{ Test = "Prioritization API"; Status = "WARN"; Details = "No risk_score field" }
        }
    } else {
        Write-Warning "No findings available in database"
        $script:TestResults += @{ Test = "Prioritization API"; Status = "WARN"; Details = "No findings in DB" }
    }
} catch {
    Write-Error "Prioritization API failed: $_"
    $script:TestResults += @{ Test = "Prioritization API"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "3.2" "Testing GET /prioritization/top-risks endpoint"
    $topRisks = Invoke-RestMethod -Uri "$BaseUrl/api/v1/prioritization/top-risks?limit=5" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 15
    
    if ($topRisks) {
        Write-Success "Top risks retrieved - Count: $($topRisks.Count)"
        $script:TestResults += @{ Test = "Top Risks API"; Status = "PASS"; Details = "$($topRisks.Count) top risks" }
    } else {
        Write-Warning "Top risks endpoint returned empty"
        $script:TestResults += @{ Test = "Top Risks API"; Status = "WARN"; Details = "Empty response" }
    }
} catch {
    Write-Error "Top risks API failed: $_"
    $script:TestResults += @{ Test = "Top Risks API"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "3.3" "Testing POST /prioritization/risk/recalculate endpoint"
    $recalcBody = @{
        batch_size = 10
        use_ml = $false
    } | ConvertTo-Json
    
    $recalc = Invoke-RestMethod -Uri "$BaseUrl/api/v1/prioritization/risk/recalculate" -Method POST -ContentType "application/json" -Body $recalcBody -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 30
    
    Write-Success "Risk recalculation triggered - Processed: $($recalc.processed) findings"
    $script:TestResults += @{ Test = "Risk Recalculation"; Status = "PASS"; Details = "Processed $($recalc.processed) findings" }
} catch {
    Write-Error "Risk recalculation failed: $_"
    $script:TestResults += @{ Test = "Risk Recalculation"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 4: AI Risk Explanation
# ============================================
Write-TestHeader "TEST 4: FEATURE 2 - AI Risk Explanation"

try {
    Write-TestStep "4.1" "Testing GET /explanations/finding/{id} endpoint"
    
    # First get a finding ID
    $findings = Invoke-RestMethod -Uri "$BaseUrl/api/v1/prioritization/findings?limit=1" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10
    
    if ($findings.items -and $findings.items.Count -gt 0) {
        $findingId = $findings.items[0].id
        
        Write-TestStep "4.2" "Getting explanation for finding $findingId"
        $explanation = Invoke-RestMethod -Uri "$BaseUrl/api/v1/explanations/finding/$findingId" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 15
        
        if ($explanation.explanation -and $explanation.overall_assessment) {
            Write-Success "Explanation generated successfully"
            Write-Host "   Assessment: $($explanation.overall_assessment)" -ForegroundColor Gray
            Write-Host "   Top Factors: $($explanation.top_factors.Count)" -ForegroundColor Gray
            $script:TestResults += @{ Test = "Risk Explanation"; Status = "PASS"; Details = "Generated for finding $findingId" }
        } else {
            Write-Warning "Explanation endpoint returned incomplete data"
            $script:TestResults += @{ Test = "Risk Explanation"; Status = "WARN"; Details = "Incomplete response" }
        }
    } else {
        Write-Warning "No findings available to test explanation"
        $script:TestResults += @{ Test = "Risk Explanation"; Status = "SKIP"; Details = "No findings available" }
    }
} catch {
    Write-Error "Risk explanation failed: $_"
    $script:TestResults += @{ Test = "Risk Explanation"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 5: Smart NLP Search
# ============================================
Write-TestHeader "TEST 5: FEATURE 3 - Smart NLP Search"

try {
    Write-TestStep "5.1" "Testing POST /search endpoint with keyword search"
    $searchBody = @{
        query = "critical vulnerabilities"
        limit = 5
    } | ConvertTo-Json
    
    $search = Invoke-RestMethod -Uri "$BaseUrl/api/v1/search" -Method POST -ContentType "application/json" -Body $searchBody -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 15
    
    if ($search.results -or $search.total -ne $null) {
        Write-Success "Search executed - Results: $($search.total)"
        if ($search.results.Count -gt 0) {
            Write-Host "   First result: $($search.results[0].title)" -ForegroundColor Gray
        }
        $script:TestResults += @{ Test = "NLP Search"; Status = "PASS"; Details = "$($search.total) results" }
    } else {
        Write-Warning "Search returned empty results"
        $script:TestResults += @{ Test = "NLP Search"; Status = "WARN"; Details = "Empty results" }
    }
} catch {
    Write-Error "NLP search failed: $_"
    $script:TestResults += @{ Test = "NLP Search"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "5.2" "Testing GET /search/suggestions endpoint"
    $suggestions = Invoke-RestMethod -Uri "$BaseUrl/api/v1/search/suggestions?query=crit&limit=5" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10
    
    Write-Success "Search suggestions retrieved - Count: $($suggestions.Count)"
    $script:TestResults += @{ Test = "Search Suggestions"; Status = "PASS"; Details = "$($suggestions.Count) suggestions" }
} catch {
    Write-Error "Search suggestions failed: $_"
    $script:TestResults += @{ Test = "Search Suggestions"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 6: What-If Risk Simulation
# ============================================
Write-TestHeader "TEST 6: FEATURE 4 - What-If Risk Simulation"

try {
    Write-TestStep "6.1" "Testing POST /simulation/remediate endpoint"
    
    # Get some finding IDs first
    $findings = Invoke-RestMethod -Uri "$BaseUrl/api/v1/prioritization/findings?limit=3" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10
    
    if ($findings.items -and $findings.items.Count -gt 0) {
        $findingIds = $findings.items | Select-Object -First 2 | ForEach-Object { $_.id }
        
        $remediateBody = @{
            finding_ids = $findingIds
        } | ConvertTo-Json
        
        $simulation = Invoke-RestMethod -Uri "$BaseUrl/api/v1/simulation/remediate" -Method POST -ContentType "application/json" -Body $remediateBody -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 15
        
        if ($simulation.current_risk -ne $null -and $simulation.simulated_risk -ne $null) {
            $reduction = $simulation.current_risk - $simulation.simulated_risk
            Write-Success "Simulation completed - Risk reduction: $([math]::Round($reduction, 2)) points"
            Write-Host "   Current: $($simulation.current_risk)" -ForegroundColor Gray
            Write-Host "   Simulated: $($simulation.simulated_risk)" -ForegroundColor Gray
            $script:TestResults += @{ Test = "Risk Simulation"; Status = "PASS"; Details = "Reduction: $([math]::Round($reduction, 2))" }
        } else {
            Write-Warning "Simulation returned incomplete data"
            $script:TestResults += @{ Test = "Risk Simulation"; Status = "WARN"; Details = "Incomplete response" }
        }
    } else {
        Write-Warning "No findings available for simulation test"
        $script:TestResults += @{ Test = "Risk Simulation"; Status = "SKIP"; Details = "No findings" }
    }
} catch {
    Write-Error "Risk simulation failed: $_"
    $script:TestResults += @{ Test = "Risk Simulation"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "6.2" "Testing GET /simulation/recommendations endpoint"
    $recommendations = Invoke-RestMethod -Uri "$BaseUrl/api/v1/simulation/recommendations?limit=5" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 15
    
    if ($recommendations.recommendations) {
        Write-Success "Recommendations retrieved - Count: $($recommendations.recommendations.Count)"
        $script:TestResults += @{ Test = "Simulation Recommendations"; Status = "PASS"; Details = "$($recommendations.recommendations.Count) recommendations" }
    } else {
        Write-Warning "Recommendations endpoint returned empty"
        $script:TestResults += @{ Test = "Simulation Recommendations"; Status = "WARN"; Details = "Empty response" }
    }
} catch {
    Write-Error "Recommendations failed: $_"
    $script:TestResults += @{ Test = "Simulation Recommendations"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 7: AI Security Assistant
# ============================================
Write-TestHeader "TEST 7: FEATURE 5 - AI Security Assistant"

try {
    Write-TestStep "7.1" "Testing POST /assistant/ask endpoint"
    $askBody = @{
        question = "What are my top 3 critical vulnerabilities?"
        context = @{}
    } | ConvertTo-Json -Depth 3
    
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/assistant/ask" -Method POST -ContentType "application/json" -Body $askBody -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 20
    
    if ($response.answer) {
        Write-Success "Assistant responded successfully"
        Write-Host "   Answer preview: $($response.answer.Substring(0, [Math]::Min(100, $response.answer.Length)))..." -ForegroundColor Gray
        Write-Host "   Question type: $($response.question_type)" -ForegroundColor Gray
        $script:TestResults += @{ Test = "AI Assistant Ask"; Status = "PASS"; Details = "Type: $($response.question_type)" }
    } else {
        Write-Warning "Assistant returned empty answer"
        $script:TestResults += @{ Test = "AI Assistant Ask"; Status = "WARN"; Details = "Empty answer" }
    }
} catch {
    Write-Error "AI Assistant failed: $_"
    $script:TestResults += @{ Test = "AI Assistant Ask"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "7.2" "Testing GET /assistant/quick-query endpoint"
    $quickQuery = Invoke-RestMethod -Uri "$BaseUrl/api/v1/assistant/quick-query?type=top_risks&limit=3" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 15
    
    if ($quickQuery.result) {
        Write-Success "Quick query executed successfully"
        $script:TestResults += @{ Test = "Assistant Quick Query"; Status = "PASS"; Details = "Query type: top_risks" }
    } else {
        Write-Warning "Quick query returned empty"
        $script:TestResults += @{ Test = "Assistant Quick Query"; Status = "WARN"; Details = "Empty response" }
    }
} catch {
    Write-Error "Quick query failed: $_"
    $script:TestResults += @{ Test = "Assistant Quick Query"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 8: Core API Endpoints
# ============================================
Write-TestHeader "TEST 8: Core API Endpoints"

$endpoints = @(
    @{ Name = "Assets"; Url = "/api/v1/assets?limit=1" },
    @{ Name = "CVE Records"; Url = "/api/v1/cve-records?limit=1" },
    @{ Name = "Findings"; Url = "/api/v1/findings?limit=1" },
    @{ Name = "Analytics"; Url = "/api/v1/analytics/summary" },
    @{ Name = "ML Models"; Url = "/api/v1/ml/models" }
)

foreach ($endpoint in $endpoints) {
    try {
        Write-TestStep "8.$($endpoints.IndexOf($endpoint) + 1)" "Testing $($endpoint.Name) endpoint"
        $response = Invoke-RestMethod -Uri "$BaseUrl$($endpoint.Url)" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10 -ErrorAction SilentlyContinue
        Write-Success "$($endpoint.Name) endpoint accessible"
        $script:TestResults += @{ Test = "$($endpoint.Name) API"; Status = "PASS"; Details = "HTTP 200" }
    } catch {
        Write-Error "$($endpoint.Name) endpoint failed: $_"
        $script:TestResults += @{ Test = "$($endpoint.Name) API"; Status = "FAIL"; Details = $_.Exception.Message }
    }
}

# ============================================
# TEST 9: Frontend Integration
# ============================================
Write-TestHeader "TEST 9: Frontend Integration"

try {
    Write-TestStep "9.1" "Testing frontend login page"
    $loginPage = Invoke-WebRequest -Uri "$FrontendUrl/login" -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($loginPage.StatusCode -eq 200) {
        Write-Success "Frontend login page accessible"
        $script:TestResults += @{ Test = "Frontend Login"; Status = "PASS"; Details = "HTTP 200" }
    }
} catch {
    Write-Error "Frontend login page failed: $_"
    $script:TestResults += @{ Test = "Frontend Login"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "9.2" "Testing frontend dashboard"
    # Dashboard requires auth, but we can check if it loads
    $dashboard = Invoke-WebRequest -Uri "$FrontendUrl/dashboard" -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($dashboard.StatusCode -eq 200 -or $dashboard.StatusCode -eq 307) {
        Write-Success "Frontend dashboard route accessible"
        $script:TestResults += @{ Test = "Frontend Dashboard"; Status = "PASS"; Details = "HTTP $($dashboard.StatusCode)" }
    }
} catch {
    Write-Error "Frontend dashboard failed: $_"
    $script:TestResults += @{ Test = "Frontend Dashboard"; Status = "FAIL"; Details = $_.Exception.Message }
}

try {
    Write-TestStep "9.3" "Testing frontend prioritized page"
    $prioritized = Invoke-WebRequest -Uri "$FrontendUrl/prioritized" -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($prioritized.StatusCode -eq 200 -or $prioritized.StatusCode -eq 307) {
        Write-Success "Frontend prioritized page accessible"
        $script:TestResults += @{ Test = "Frontend Prioritized"; Status = "PASS"; Details = "HTTP $($prioritized.StatusCode)" }
    }
} catch {
    Write-Error "Frontend prioritized page failed: $_"
    $script:TestResults += @{ Test = "Frontend Prioritized"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# TEST 10: Cross-Feature Integration
# ============================================
Write-TestHeader "TEST 10: Cross-Feature Integration"

try {
    Write-TestStep "10.1" "Testing end-to-end workflow: Search → Prioritize → Explain"
    
    # Search for findings
    $searchBody = @{ query = "high severity"; limit = 1 } | ConvertTo-Json
    $search = Invoke-RestMethod -Uri "$BaseUrl/api/v1/search" -Method POST -ContentType "application/json" -Body $searchBody -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10
    
    if ($search.results -and $search.results.Count -gt 0) {
        $findingId = $search.results[0].id
        
        # Get risk score
        $riskScore = Invoke-RestMethod -Uri "$BaseUrl/api/v1/prioritization/risk-score/$findingId" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10 -ErrorAction SilentlyContinue
        
        # Get explanation
        $explanation = Invoke-RestMethod -Uri "$BaseUrl/api/v1/explanations/finding/$findingId" -Method GET -Headers @{Authorization = "Bearer $script:AccessToken"} -TimeoutSec 10 -ErrorAction SilentlyContinue
        
        Write-Success "End-to-end workflow successful"
        Write-Host "   Found: $($search.results.Count) via search" -ForegroundColor Gray
        Write-Host "   Risk: $($riskScore.risk_score)" -ForegroundColor Gray
        Write-Host "   Explanation: $($explanation.explanation.Substring(0, [Math]::Min(50, $explanation.explanation.Length)))..." -ForegroundColor Gray
        $script:TestResults += @{ Test = "E2E Workflow"; Status = "PASS"; Details = "Search→Risk→Explain" }
    } else {
        Write-Warning "E2E workflow - no findings via search"
        $script:TestResults += @{ Test = "E2E Workflow"; Status = "WARN"; Details = "No search results" }
    }
} catch {
    Write-Error "E2E workflow failed: $_"
    $script:TestResults += @{ Test = "E2E Workflow"; Status = "FAIL"; Details = $_.Exception.Message }
}

# ============================================
# FINAL SUMMARY
# ============================================
Write-TestHeader "FINAL TEST SUMMARY"

# Calculate statistics
$passed = ($script:TestResults | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($script:TestResults | Where-Object { $_.Status -eq "FAIL" }).Count
$warnings = ($script:TestResults | Where-Object { $_.Status -eq "WARN" }).Count
$skipped = ($script:TestResults | Where-Object { $_.Status -eq "SKIP" }).Count
$total = $script:TestResults.Count
$score = [math]::Round(($passed / $total) * 100)

Write-Host "`n📊 Test Statistics:" -ForegroundColor $Colors.Info
Write-Host "   Total Tests:    $total" -ForegroundColor White
Write-Host "   ✅ Passed:       $passed" -ForegroundColor $Colors.Success
Write-Host "   ❌ Failed:       $failed" -ForegroundColor $Colors.Error
Write-Host "   ⚠️ Warnings:     $warnings" -ForegroundColor $Colors.Warning
Write-Host "   ⏭️ Skipped:      $skipped" -ForegroundColor Gray
Write-Host "   📈 Score:        $score%" -ForegroundColor $(if ($score -ge 80) { $Colors.Success } elseif ($score -ge 60) { $Colors.Warning } else { $Colors.Error })

Write-Host "`n📋 Detailed Results:" -ForegroundColor $Colors.Info
$script:TestResults | ForEach-Object {
    $color = switch ($_.Status) {
        "PASS" { $Colors.Success }
        "FAIL" { $Colors.Error }
        "WARN" { $Colors.Warning }
        "SKIP" { "Gray" }
        default { "White" }
    }
    Write-Host "   [$($_.Status)] $($_.Test) - $($_.Details)" -ForegroundColor $color
}

# Feature-specific scores
Write-Host "`n🎯 Feature Scores:" -ForegroundColor $Colors.Info

$featureTests = @{
    "Auto-Prioritization" = $script:TestResults | Where-Object { $_.Test -match "Prioritization|Top Risks|Risk Recalculation" }
    "AI Risk Explanation" = $script:TestResults | Where-Object { $_.Test -match "Explanation" }
    "Smart NLP Search" = $script:TestResults | Where-Object { $_.Test -match "Search" }
    "What-If Simulation" = $script:TestResults | Where-Object { $_.Test -match "Simulation" }
    "AI Security Assistant" = $script:TestResults | Where-Object { $_.Test -match "Assistant" }
}

foreach ($feature in $featureTests.GetEnumerator()) {
    $featurePassed = ($feature.Value | Where-Object { $_.Status -eq "PASS" }).Count
    $featureTotal = $feature.Value.Count
    $featureScore = if ($featureTotal -gt 0) { [math]::Round(($featurePassed / $featureTotal) * 100) } else { 0 }
    $color = if ($featureScore -ge 80) { $Colors.Success } elseif ($featureScore -ge 60) { $Colors.Warning } else { $Colors.Error }
    Write-Host "   $($feature.Key): $featureScore% ($featurePassed/$featureTotal tests)" -ForegroundColor $color
}

# Final verdict
Write-Host "`n🏆 FINAL VERDICT:" -ForegroundColor $Colors.Header
if ($score -ge 85) {
    Write-Host "   ✅ ALL SYSTEMS OPERATIONAL - Production Ready!" -ForegroundColor $Colors.Success
} elseif ($score -ge 70) {
    Write-Host "   ⚠️ MOSTLY FUNCTIONAL - Minor issues remain" -ForegroundColor $Colors.Warning
} elseif ($score -ge 50) {
    Write-Host "   ⚠️ PARTIALLY FUNCTIONAL - Issues need attention" -ForegroundColor $Colors.Warning
} else {
    Write-Host "   ❌ NOT FUNCTIONAL - Major fixes required" -ForegroundColor $Colors.Error
}

Write-Host "`n📖 Next Steps:" -ForegroundColor $Colors.Info
if ($failed -gt 0) {
    Write-Host "   1. Check failed tests above and fix issues" -ForegroundColor White
    Write-Host "   2. Review API logs: docker logs aegiscore-intelligence-platform-api-1 --tail 100" -ForegroundColor White
}
if ($warnings -gt 0) {
    Write-Host "   3. Consider addressing warnings for full functionality" -ForegroundColor White
}
Write-Host "   4. Access application at: $FrontendUrl" -ForegroundColor White
Write-Host "   5. API documentation at: $BaseUrl/docs" -ForegroundColor White

# Save results to file
$timestamp = Get-Date -Format "yyyy-MM-dd-HH-mm-ss"
$outputFile = "test-results-$timestamp.json"
$script:TestResults | ConvertTo-Json -Depth 3 | Out-File $outputFile
Write-Host "`n💾 Test results saved to: $outputFile" -ForegroundColor $Colors.Info
