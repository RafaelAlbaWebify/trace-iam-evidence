Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeScript = Join-Path $PSScriptRoot 'trace.ps1'
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-runtime-test-{0}" -f [guid]::NewGuid().ToString('N'))

try {
    Push-Location ([System.IO.Path]::GetTempPath())
    try {
        & $runtimeScript -Action status -DataDirectory $tempRoot -SkipInstall
        & $runtimeScript -Action stop -DataDirectory $tempRoot -SkipInstall
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path (Join-Path $repoRoot 'backend'))) {
        throw 'Runtime manager did not resolve the repository from its own location.'
    }
    Write-Host 'TRACE runtime manager smoke test passed.'
}
finally {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
