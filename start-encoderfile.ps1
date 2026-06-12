$port = 8081
$wslBinary = "/home/ashwin_pranav_m/mozilla-hackathon/encoderfile/build/sentiment-analyzer.encoderfile"

try {
    $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -TimeoutSec 3 -UseBasicParsing
    if ($response.StatusCode -eq 200 -and $response.Content -match "OK") {
        $model = Invoke-WebRequest -Uri "http://localhost:$port/model" -TimeoutSec 3 -UseBasicParsing
        Write-Host "Encoderfile is already running on http://localhost:$port"
        Write-Host $model.Content
        exit 0
    }
} catch {
    # Not running yet; start below.
}

$binaryExists = wsl -e bash -lc "test -x '$wslBinary' && echo yes || echo no"
if ($binaryExists -ne "yes") {
    Write-Host "Encoderfile binary not found. Run setup first:"
    Write-Host "  wsl -e bash /mnt/d/proj/scripts/setup-encoderfile.sh"
    exit 1
}

Write-Host "Starting encoderfile on http://localhost:$port"
wsl -e bash -lc "chmod +x '$wslBinary' && '$wslBinary' serve --http-port $port --disable-grpc"
