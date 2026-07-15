Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$runtimeScript = Join-Path $PSScriptRoot 'trace.ps1'
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-runtime-test-{0}" -f [guid]::NewGuid().ToString('N'))
$workingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-runtime-caller-{0}" -f [guid]::NewGuid().ToString('N'))
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$statePath = Join-Path $tempRoot 'state\runtime.json'
$logDirectory = Join-Path $tempRoot 'logs'

function Invoke-TraceAction {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('start', 'status', 'stop')]
        [string]$Action,

        [switch]$SkipInstall
    )

    $stdoutPath = Join-Path $tempRoot "$Action.out.log"
    $stderrPath = Join-Path $tempRoot "$Action.err.log"
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $workingRoot -Force | Out-Null

    $arguments = @(
        '-NoLogo',
        '-NoProfile',
        '-NonInteractive',
        '-File',
        $runtimeScript,
        '-Action',
        $Action,
        '-DataDirectory',
        $tempRoot,
        '-NoBrowser'
    )
    if ($SkipInstall) {
        $arguments += '-SkipInstall'
    }

    $process = Start-Process -FilePath $pwsh -ArgumentList $arguments -WorkingDirectory $workingRoot -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -Wait
    $stdout = if (Test-Path $stdoutPath) { Get-Content $stdoutPath -Raw } else { '' }
    $stderr = if (Test-Path $stderrPath) { Get-Content $stderrPath -Raw } else { '' }

    Write-Host "TRACE $Action exit code: $($process.ExitCode)"
    if (-not [string]::IsNullOrWhiteSpace($stdout)) {
        Write-Host "--- $Action stdout ---"
        Write-Host $stdout.TrimEnd()
    }
    if (-not [string]::IsNullOrWhiteSpace($stderr)) {
        Write-Host "--- $Action stderr ---"
        Write-Host $stderr.TrimEnd()
    }

    if ($process.ExitCode -ne 0) {
        throw "TRACE runtime action '$Action' failed with exit code $($process.ExitCode)."
    }
    return [pscustomobject]@{
        Stdout = $stdout
        Stderr = $stderr
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
    if ($state.repo_root -ne (Resolve-Path (Join-Path $PSScriptRoot '..')).Path) {
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
