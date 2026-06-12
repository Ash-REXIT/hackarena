Write-Host "Hackathon stack preflight check"
Write-Host "================================"

function Test-Service {
    param(
        [string]$Name,
        [string]$Url,
        [scriptblock]$Validate
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing
        $ok = & $Validate $response
        if ($ok) {
            Write-Host "[OK]   $Name -> $Url"
            return $true
        }
        Write-Host "[FAIL] $Name -> unexpected response"
        return $false
    } catch {
        Write-Host "[FAIL] $Name -> $($_.Exception.Message)"
        return $false
    }
}

$llm = Test-Service "llamafile" "http://localhost:8080/v1/models" { param($r) $r.StatusCode -eq 200 }
$encoder = Test-Service "encoderfile" "http://localhost:8081/health" { param($r) $r.Content -match "OK" }
$mcpd = Test-Service "mcpd" "http://localhost:8090/api/v1/servers" { param($r) $r.StatusCode -eq 200 }
$app = Test-Service "any-agent app" "http://localhost:8000/api/health" { param($r) $r.StatusCode -eq 200 }

Write-Host ""
if ($llm -and $encoder -and $mcpd) {
    Write-Host "Core hackathon stack is ready (llamafile + encoderfile + mcpd)."
} else {
    Write-Host "Some services are missing. Start them with:"
    Write-Host "  d:\proj\start-llamafile.ps1"
    Write-Host "  d:\proj\start-encoderfile.ps1"
    Write-Host "  d:\proj\start-mcpd.ps1"
    Write-Host "  d:\proj\start.ps1"
    Write-Host ""
    Write-Host "First-time encoderfile setup:"
    Write-Host "  wsl -e bash /mnt/d/proj/scripts/setup-encoderfile.sh"
}

if (-not $app) {
    Write-Host "App backend is not running yet. Start with d:\proj\start.ps1"
}
