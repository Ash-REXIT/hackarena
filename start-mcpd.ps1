$mcpdDir = "/home/ashwin_pranav_m/mozilla-hackathon/mcpd"
$mcpdBin = "$mcpdDir/mcpd"

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8090/api/v1/servers" -TimeoutSec 3 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "MCPD is already running on http://localhost:8090"
        Write-Host $response.Content
        exit 0
    }
} catch {
    # Not running yet; start below.
}

Write-Host "Starting mcpd daemon in WSL ($mcpdDir)"
wsl -e bash -lc "cd '$mcpdDir' && '$mcpdBin' daemon --dev --log-level=INFO"
