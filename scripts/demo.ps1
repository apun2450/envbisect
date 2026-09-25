$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location -LiteralPath $repoRoot
try {
    Write-Host 'EnvBisect: 46 differences, one two-variable interaction'
    Start-Sleep -Seconds 2
    & envbisect diagnose --pass examples/demo/pass.env --fail examples/demo/fail.env -- python examples/demo/app.py
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Write-Host ''
    Write-Host 'Result: FEATURE_CACHE and TZ act together in this demo.'
    Start-Sleep -Seconds 12
}
finally {
    Pop-Location
}
