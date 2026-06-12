Write-Host "Starting full Mozilla AI hackathon stack..."
Write-Host ""

$scripts = @(
    @{ Name = "llamafile"; Script = "start-llamafile.ps1" },
    @{ Name = "encoderfile"; Script = "start-encoderfile.ps1" },
    @{ Name = "mcpd"; Script = "start-mcpd.ps1" },
    @{ Name = "app"; Script = "start.ps1" }
)

Write-Host "Run these in separate terminals:"
foreach ($item in $scripts) {
    Write-Host "  d:\proj\$($item.Script)"
}
Write-Host ""
Write-Host "Then verify with:"
Write-Host "  d:\proj\preflight.ps1"
Write-Host ""
Write-Host "Open http://localhost:8000"
