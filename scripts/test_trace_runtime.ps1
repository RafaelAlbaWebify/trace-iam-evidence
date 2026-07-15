Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontendRoot = Join-Path $repoRoot 'frontend'
$runtimeScript = Join-Path $PSScriptRoot 'trace.ps1'
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-runtime-test-{0}" -f [guid]::NewGuid().ToString('N'))
$workingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-runtime-caller-{0}" -f [guid]::NewGuid().ToString('N'))
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm) { $npm = (Get-Command npm -ErrorAction Stop).Source }
$statePath = Join-Path $tempRoot 'state\runtime.json'
$logDirectory = Join-Path $tempRoot 'logs'

function Invoke-TraceAction {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('start', 'status', 'stop')]
        [string]$Action,

        [switch]$SkipInstall
    )

    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $workingRoot -Force | Out-Null

    $arguments = @(
        '-Action', $Action,
        '-DataDirectory', $tempRoot,
        '-NoBrowser'
    )
    if ($SkipInstall) {
        $arguments += '-SkipInstall'
    }

    Push-Location $workingRoot
    try {
        if ($Action -eq 'status') {
            $stdout = (& $runtimeScript @arguments | Out-String)
        }
        else {
            & $runtimeScript @arguments
            $stdout = ''
        }
    }
    finally {
        Pop-Location
    }

    if (-not [string]::IsNullOrWhiteSpace($stdout)) {
        Write-Host "--- $Action stdout ---"
        Write-Host $stdout.TrimEnd()
    }

    return [pscustomobject]@{
        Stdout = $stdout
    }
}

function Wait-ForEndpoint {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [int]$Attempts = 60
    )

    for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "TRACE endpoint did not become available: $Uri"
}

function Assert-ProcessStopped {
    param([Parameter(Mandatory)][int]$ProcessId)

    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if ($null -eq (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
            return
        }
        Start-Sleep -Milliseconds 250
    }
    throw "TRACE process is still running after stop: $ProcessId"
}

try {
    Push-Location $frontendRoot
    try {
        & $npm install --ignore-scripts --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend dependency preparation failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }

    Invoke-TraceAction -Action start | Out-Null
    Wait-ForEndpoint -Uri 'http://127.0.0.1:8000/api/health'
    Wait-ForEndpoint -Uri 'http://127.0.0.1:5173'

    if (-not (Test-Path $statePath)) {
        throw "TRACE runtime state was not created: $statePath"
    }
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
    if ($state.runtime_root -ne $tempRoot) {
        throw "TRACE runtime root mismatch. Expected '$tempRoot', found '$($state.runtime_root)'."
    }
    if ($state.repo_root -ne $repoRoot) {
        throw 'TRACE runtime manager did not resolve the repository from its own location.'
    }
    if ($state.database_path -ne (Join-Path $tempRoot 'trace_iam.db')) {
        throw "TRACE database path mismatch: $($state.database_path)"
    }
    if ($null -eq (Get-Process -Id ([int]$state.backend_pid) -ErrorAction SilentlyContinue)) {
        throw "TRACE backend process is not running: $($state.backend_pid)"
    }
    if ($null -eq (Get-Process -Id ([int]$state.frontend_pid) -ErrorAction SilentlyContinue)) {
        throw "TRACE frontend process is not running: $($state.frontend_pid)"
    }

    $status = Invoke-TraceAction -Action status -SkipInstall
    if ($status.Stdout -notmatch 'backend_running\s*:\s*True') {
        throw 'TRACE status did not report the backend as running.'
    }
    if ($status.Stdout -notmatch 'frontend_running\s*:\s*True') {
        throw 'TRACE status did not report the frontend as running.'
    }

    Invoke-TraceAction -Action stop -SkipInstall | Out-Null
    Assert-ProcessStopped -ProcessId ([int]$state.backend_pid)
    Assert-ProcessStopped -ProcessId ([int]$state.frontend_pid)

    if (Test-Path $statePath) {
        throw "TRACE runtime state was not removed: $statePath"
    }
    foreach ($logName in @('backend.out.log', 'backend.err.log', 'frontend.out.log', 'frontend.err.log')) {
        if (-not (Test-Path (Join-Path $logDirectory $logName))) {
            throw "TRACE retained log is missing: $logName"
        }
    }

    Write-Host 'TRACE full Windows runtime lifecycle acceptance passed.'
}
finally {
    if (Test-Path $statePath) {
        try {
            Invoke-TraceAction -Action stop -SkipInstall | Out-Null
        }
        catch {
            Write-Warning "TRACE cleanup stop failed: $($_.Exception.Message)"
        }
    }
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $workingRoot -Recurse -Force -ErrorAction SilentlyContinue
}
