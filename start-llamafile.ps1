. "$PSScriptRoot\scripts\load-env.ps1"

$port = 8080
$modelPath = Get-DotEnvValue -Key "LLAMAFILE_PATH" -Default "C:\Users\kmkan\Qwen3.5-0.8B-Q8_0.exe"

try {
    $response = Invoke-WebRequest -Uri "http://localhost:$port/v1/models" -TimeoutSec 3 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "Llamafile is already running on http://localhost:$port"
        try {
            $payload = $response.Content | ConvertFrom-Json
            $modelName = $payload.data[0].id
            if ($modelName) {
                Write-Host "  Model: $modelName"
            }
        } catch {
            # Ignore JSON parse issues; server is up.
        }
        Write-Host "  Keep only one llamafile process on port $port."
        exit 0
    }
} catch {
    $portInUse = netstat -ano | findstr ":$port "
    if ($portInUse) {
        Write-Host "ERROR: Port $port is in use but llamafile is not responding on /v1/models."
        Write-Host "       Stop the other process, then run this script again."
        exit 1
    }
}

if (-not (Test-Path $modelPath)) {
    Write-Host "Model not found: $modelPath"
    Write-Host "Set LLAMAFILE_PATH in backend\.env"
    exit 1
}

Write-Host "Starting llamafile (Mozilla stack LLM) on http://localhost:$port"
Write-Host "  Path: $modelPath"
& $modelPath --server --port $port
