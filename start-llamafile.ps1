$port = 8080
$modelPath = "C:\Users\kmkan\Qwen3.5-0.8B-Q8_0.exe"

try {
    $response = Invoke-WebRequest -Uri "http://localhost:$port/v1/models" -TimeoutSec 3 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "Llamafile is already running on http://localhost:$port"
        exit 0
    }
} catch {
    # Not running yet; start below.
}

Write-Host "Starting llamafile Qwen model on http://localhost:$port"
& $modelPath --server --port $port
