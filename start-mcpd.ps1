$port = 8090
$projectMcpdDir = "/mnt/d/proj/mcpd"
$mcpdBin = "/home/ashwin_pranav_m/mozilla-hackathon/mcpd/mcpd"
$configFile = "/mnt/d/proj/mcpd/.mcpd.toml"

$expectedServers = @("time", "fetch")
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$port/api/v1/servers" -TimeoutSec 3 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        $servers = $response.Content | ConvertFrom-Json
        $missing = $expectedServers | Where-Object { $_ -notin $servers }
        if ($missing.Count -eq 0) {
            Write-Host "MCPD is already running on http://localhost:$port"
            Write-Host "  Servers: $($servers -join ', ')"
            exit 0
        }
        Write-Host "MCPD running but missing servers: $($missing -join ', '). Restarting..."
        wsl -e bash -lc "pkill -f 'mcpd daemon' 2>/dev/null || true"
        Start-Sleep -Seconds 2
    }
} catch {
    # Not running yet; start below.
}

$binaryExists = wsl -e bash -lc "test -x '$mcpdBin' && echo yes || echo no"
if ($binaryExists -ne "yes") {
    Write-Host "MCPD binary not found. Expected: $mcpdBin"
    exit 1
}

$configExists = wsl -e bash -lc "test -f '$configFile' && echo yes || echo no"
if ($configExists -ne "yes") {
    Write-Host "MCPD config not found: $configFile"
    exit 1
}

Write-Host "Starting MCPD on http://localhost:$port"
Write-Host "  Servers: time (get_current_time, convert_time), fetch (fetch URL content)"
Write-Host "  Config:  d:\proj\mcpd\.mcpd.toml"
wsl -e bash -lc "cd '$projectMcpdDir' && '$mcpdBin' daemon --dev --log-level=INFO --config-file '$configFile'"
