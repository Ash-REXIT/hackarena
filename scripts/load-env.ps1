# Shared env loader for start scripts (reads backend/.env)
param(
    [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent) "backend\.env")
)

function Get-DotEnvValue {
    param(
        [string]$Key,
        [string]$Default = ""
    )
    if (-not (Test-Path $EnvFile)) {
        return $Default
    }
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match "^\s*#") { continue }
        if ($line -match "^\s*$Key\s*=\s*(.+)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $Default
}
