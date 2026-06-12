Write-Host "Local Agent startup checks..."

$llmOk = $false
$mcpdOk = $false

try {
    $llm = Invoke-WebRequest -Uri "http://localhost:8080/v1/models" -TimeoutSec 3 -UseBasicParsing
    $llmOk = $llm.StatusCode -eq 200
} catch {
    Write-Host "WARNING: Llamafile is not running on http://localhost:8080"
    Write-Host "         Run: d:\proj\start-llamafile.ps1"
}

try {
    $mcpd = Invoke-WebRequest -Uri "http://localhost:8090/api/v1/servers" -TimeoutSec 3 -UseBasicParsing
    $mcpdOk = $mcpd.StatusCode -eq 200
} catch {
    Write-Host "WARNING: MCPD is not running on http://localhost:8090"
    Write-Host "         Run: d:\proj\start-mcpd.ps1"
}

if ($llmOk -and $mcpdOk) {
    Write-Host "Prerequisites OK: LLM + MCPD are running."
} else {
    Write-Host ""
    Write-Host "The app will start, but chat may fail until both services are up."
}

Write-Host "Starting backend on http://localhost:8000"
Write-Host "Open http://localhost:8000 in your browser after startup."
Write-Host ""

Set-Location "$PSScriptRoot\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
