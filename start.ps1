Write-Host "Building FoxZilla frontend..."
Set-Location "$PSScriptRoot\frontend"
if (-not (Test-Path node_modules)) {
    npm install
}
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed."
    exit 1
}

Write-Host "Stopping any stale backend on port 8000..."
& "$PSScriptRoot\stop.ps1"

$llmOk = $false
$encoderOk = $false
$mcpdOk = $false

try {
    $llm = Invoke-WebRequest -Uri "http://localhost:8080/v1/models" -TimeoutSec 3 -UseBasicParsing
    $llmOk = $llm.StatusCode -eq 200
} catch {
    Write-Host "WARNING: Llamafile is not running on http://localhost:8080"
    Write-Host "         Run: d:\proj\start-llamafile.ps1"
}

try {
    $encoder = Invoke-WebRequest -Uri "http://localhost:8081/health" -TimeoutSec 3 -UseBasicParsing
    $encoderOk = $encoder.Content -match "OK"
} catch {
    Write-Host "WARNING: Encoderfile is not running on http://localhost:8081"
    Write-Host "         Setup:  wsl -e bash /mnt/d/proj/scripts/setup-encoderfile.sh"
    Write-Host "         Start:  d:\proj\start-encoderfile.ps1"
}

try {
    $mcpd = Invoke-WebRequest -Uri "http://localhost:8090/api/v1/servers" -TimeoutSec 3 -UseBasicParsing
    $mcpdOk = $mcpd.StatusCode -eq 200
} catch {
    Write-Host "WARNING: MCPD is not running on http://localhost:8090"
    Write-Host "         Run: d:\proj\start-mcpd.ps1"
}

if ($llmOk -and $encoderOk -and $mcpdOk) {
    Write-Host "Mozilla stack ready: llamafile + encoderfile + mcpd + any-agent"
} else {
    Write-Host ""
    Write-Host "Run d:\proj\preflight.ps1 for a full check."
}

Write-Host "Starting backend on http://localhost:8000"
Write-Host "  UI + API both on port 8000 (frontend built to frontend/dist)"
Write-Host "Open http://localhost:8000 in your browser after startup."
Write-Host "  Dev-only alternative: cd frontend && npm run dev  ->  http://localhost:5173"
Write-Host ""

Set-Location "$PSScriptRoot\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
