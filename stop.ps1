# Stop FoxZilla backend and free port 8000
Write-Host "Stopping FoxZilla backend on port 8000..."

Get-CimInstance Win32_Process -Filter "name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "uvicorn|main:app" } |
    ForEach-Object {
        Write-Host "  Stopping PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Start-Sleep -Seconds 2

$listener = netstat -ano | Select-String ":8000\s+.*LISTENING"
if ($listener) {
    $pid = ($listener -split "\s+")[-1]
    Write-Host "  Force-killing listener PID $pid"
    taskkill /F /PID $pid 2>$null
    Start-Sleep -Seconds 2
}

$still = netstat -ano | Select-String ":8000\s+.*LISTENING"
if ($still) {
    Write-Host "Port 8000 still in use. Close the browser tab on localhost:8000, wait 30s, then retry."
    Write-Host $still
} else {
    Write-Host "Port 8000 is free. Run: .\start.ps1"
}
