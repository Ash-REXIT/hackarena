Write-Host "Mozilla AI Hackathon setup"
Write-Host "=========================="
Write-Host ""
Write-Host "Step 1/2: Setting up encoderfile in WSL (clone, export ONNX model, build binary)"
wsl -e bash /mnt/d/proj/scripts/setup-encoderfile.sh
Write-Host ""
Write-Host "Step 2/2: Running preflight checks"
powershell -NoProfile -File "$PSScriptRoot\preflight.ps1"
