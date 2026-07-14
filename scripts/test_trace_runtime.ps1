Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeScript = Join-Path $PSScriptRoot 'trace.ps1'
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-runtime-test-{0}" -f [guid]::NewGuid().ToString('N'))
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

function Invoke-TraceAction {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('status', 'stop')]
        [string]$Action
    )

    $stdoutPath = Join-Path $tempRoot "$Action.out.log"
    $stderrPath = Join-Path $tempRoot "$Action.err.log"
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

    $process = Start-Process -FilePath $pwsh -ArgumentList @(
        '-NoLogo',
        '-NoProfile',
        '-NonInteractive',
        '-File',
        $runtimeScript,
        '-Action',
        $Action,
        '-DataDirectory',
        $tempRoot,
        '-SkipInstall'
    ) -WorkingDirectory ([System.IO.Path]::GetTempPath()) -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -Wait

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
}

try {
    Invoke-TraceAction -Action status
    Invoke-TraceAction -Action stop

    if (-not (Test-Path (Join-Path $repoRoot 'backend'))) {
        throw 'Runtime manager did not resolve the repository from its own location.'
    }
    Write-Host 'TRACE runtime manager smoke test passed.'
}
finally {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
