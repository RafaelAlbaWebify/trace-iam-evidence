[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('start', 'stop', 'status', 'diagnostics', 'backup', 'restore')]
    [string]$Action,

    [Parameter()]
    [string]$DataDirectory,

    [Parameter()]
    [string]$BackupPath,

    [Parameter()]
    [string]$RestorePath,

    [Parameter()]
    [switch]$NoBrowser,

    [Parameter()]
    [switch]$SkipInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackendRoot = Join-Path $RepoRoot 'backend'
$FrontendRoot = Join-Path $RepoRoot 'frontend'
$RuntimeRoot = if ($DataDirectory) {
    [System.IO.Path]::GetFullPath($DataDirectory)
}
elseif ($env:TRACE_DATA_DIR) {
    [System.IO.Path]::GetFullPath($env:TRACE_DATA_DIR)
}
else {
    Join-Path $env:LOCALAPPDATA 'TRACE-IAM-Evidence'
}
$StateDirectory = Join-Path $RuntimeRoot 'state'
$LogDirectory = Join-Path $RuntimeRoot 'logs'
$BackupDirectory = Join-Path $RuntimeRoot 'backups'
$DatabasePath = Join-Path $RuntimeRoot 'trace_iam.db'
$StatePath = Join-Path $StateDirectory 'runtime.json'
$VenvRoot = Join-Path $RepoRoot '.trace-runtime\venv'
$VenvPython = Join-Path $VenvRoot 'Scripts\python.exe'
$DatabaseUtility = Join-Path $PSScriptRoot 'trace_database.py'
$ViteEntryPoint = Join-Path $FrontendRoot 'node_modules\vite\bin\vite.js'

function Ensure-Directory {
    param([Parameter(Mandatory)][string]$Path)
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Get-CommandPath {
    param([Parameter(Mandatory)][string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) { return $null }
    return $command.Source
}

function Get-PythonLauncher {
    $py = Get-CommandPath 'py'
    if ($py) {
        & $py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{ File = $py; Prefix = @('-3.12') }
        }
    }
    $python = Get-CommandPath 'python'
    if ($python) {
        & $python -c "import sys; assert sys.version_info[:2] == (3, 12)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{ File = $python; Prefix = @() }
        }
    }
    return $null
}

function Invoke-External {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter()][string]$WorkingDirectory = $RepoRoot
    )
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Ensure-Dependencies {
    $launcher = Get-PythonLauncher
    if (-not (Test-Path $VenvPython)) {
        if ($SkipInstall) { throw "TRACE virtual environment is missing: $VenvRoot" }
        if ($null -eq $launcher) { throw 'Python 3.12 is required.' }
        Ensure-Directory (Split-Path $VenvRoot -Parent)
        Invoke-External -FilePath $launcher.File -Arguments @($launcher.Prefix + @('-m', 'venv', $VenvRoot))
    }
    if (-not $SkipInstall) {
        Invoke-External -FilePath $VenvPython -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '-e', $BackendRoot)
    }

    $node = Get-CommandPath 'node'
    $npm = Get-CommandPath 'npm.cmd'
    if (-not $npm) { $npm = Get-CommandPath 'npm' }
    if (-not $node -or -not $npm) { throw 'Node.js and npm are required.' }
    if (-not (Test-Path $ViteEntryPoint)) {
        if ($SkipInstall) { throw 'Frontend dependencies are missing.' }
        $lockFile = Join-Path $FrontendRoot 'package-lock.json'
        $installArguments = if (Test-Path $lockFile) {
            @('ci', '--ignore-scripts', '--no-audit', '--no-fund')
        }
        else {
            @('install', '--ignore-scripts', '--no-audit', '--no-fund')
        }
        Invoke-External -FilePath $npm -Arguments $installArguments -WorkingDirectory $FrontendRoot
    }
    if (-not (Test-Path $ViteEntryPoint)) { throw "Vite entry point is missing: $ViteEntryPoint" }
    return [pscustomobject]@{ Node = $node; Npm = $npm }
}

function Read-State {
    if (-not (Test-Path $StatePath)) { return $null }
    return Get-Content $StatePath -Raw | ConvertFrom-Json
}

function Test-ProcessAlive {
    param([Parameter()][object]$ProcessId)
    if ($null -eq $ProcessId) { return $false }
    return $null -ne (Get-Process -Id ([int]$ProcessId) -ErrorAction SilentlyContinue)
}

function Stop-ProcessTree {
    param([Parameter()][object]$ProcessId)
    if (-not (Test-ProcessAlive $ProcessId)) { return }
    & taskkill.exe /PID ([int]$ProcessId) /T /F | Out-Null
}

function Wait-ForHealth {
    param([int]$Attempts = 40)
    for ($index = 0; $index -lt $Attempts; $index++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
            if ($health.status -eq 'ok') { return }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "TRACE backend did not become healthy. Review $LogDirectory."
}

function Start-Trace {
    $existing = Read-State
    if ($existing -and (Test-ProcessAlive $existing.backend_pid) -and (Test-ProcessAlive $existing.frontend_pid)) {
        Write-Host 'TRACE is already running at http://127.0.0.1:5173'
        return
    }

    Ensure-Directory $RuntimeRoot
    Ensure-Directory $StateDirectory
    Ensure-Directory $LogDirectory
    Ensure-Directory $BackupDirectory
    $dependencies = Ensure-Dependencies
    $env:TRACE_DB_PATH = $DatabasePath

    $backendOut = Join-Path $LogDirectory 'backend.out.log'
    $backendErr = Join-Path $LogDirectory 'backend.err.log'
    $frontendOut = Join-Path $LogDirectory 'frontend.out.log'
    $frontendErr = Join-Path $LogDirectory 'frontend.err.log'

    $backend = Start-Process -FilePath $VenvPython -ArgumentList @(
        '-m', 'uvicorn', 'trace_iam.main:app', '--host', '127.0.0.1', '--port', '8000'
    ) -WorkingDirectory $BackendRoot -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
    $frontend = Start-Process -FilePath $dependencies.Node -ArgumentList @(
        $ViteEntryPoint, '--host', '127.0.0.1', '--port', '5173'
    ) -WorkingDirectory $FrontendRoot -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru

    [pscustomobject]@{
        backend_pid = $backend.Id
        frontend_pid = $frontend.Id
        started_at = [DateTimeOffset]::UtcNow.ToString('o')
        repo_root = $RepoRoot
        runtime_root = $RuntimeRoot
        database_path = $DatabasePath
        url = 'http://127.0.0.1:5173'
    } | ConvertTo-Json | Set-Content -Path $StatePath -Encoding UTF8

    try {
        Wait-ForHealth
    }
    catch {
        Stop-ProcessTree $frontend.Id
        Stop-ProcessTree $backend.Id
        throw
    }

    Write-Host 'TRACE IAM Evidence is running.'
    Write-Host 'UI:       http://127.0.0.1:5173'
    Write-Host "Database: $DatabasePath"
    Write-Host "Logs:     $LogDirectory"
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173' | Out-Null }
}

function Stop-Trace {
    $state = Read-State
    if ($null -eq $state) {
        Write-Host 'No TRACE runtime state was found.'
        return
    }
    Stop-ProcessTree $state.frontend_pid
    Stop-ProcessTree $state.backend_pid
    Remove-Item $StatePath -Force -ErrorAction SilentlyContinue
    Write-Host 'TRACE IAM Evidence stopped.'
}

function Show-Status {
    $state = Read-State
    $backendAlive = $false
    $frontendAlive = $false
    if ($state) {
        $backendAlive = Test-ProcessAlive $state.backend_pid
        $frontendAlive = Test-ProcessAlive $state.frontend_pid
    }
    [pscustomobject]@{
        runtime_root = $RuntimeRoot
        database_path = $DatabasePath
        state_file = $StatePath
        backend_running = $backendAlive
        frontend_running = $frontendAlive
        url = 'http://127.0.0.1:5173'
    } | Format-List
}

function Show-Diagnostics {
    $launcher = Get-PythonLauncher
    $node = Get-CommandPath 'node'
    $npm = Get-CommandPath 'npm.cmd'
    if (-not $npm) { $npm = Get-CommandPath 'npm' }
    $state = Read-State
    [pscustomobject]@{
        repository = $RepoRoot
        runtime_root = $RuntimeRoot
        python_3_12 = $null -ne $launcher
        virtual_environment = Test-Path $VenvPython
        node = $node
        npm = $npm
        backend_process = if ($state) { Test-ProcessAlive $state.backend_pid } else { $false }
        frontend_process = if ($state) { Test-ProcessAlive $state.frontend_pid } else { $false }
        database_exists = Test-Path $DatabasePath
        logs = $LogDirectory
    } | Format-List
    if (Test-Path $DatabasePath) {
        $python = if (Test-Path $VenvPython) { $VenvPython } elseif ($launcher) { $launcher.File } else { $null }
        if ($python) {
            $arguments = if ($launcher -and $python -eq $launcher.File) { @($launcher.Prefix + @($DatabaseUtility, 'verify', $DatabasePath)) } else { @($DatabaseUtility, 'verify', $DatabasePath) }
            Invoke-External -FilePath $python -Arguments $arguments
        }
    }
}

function Backup-Trace {
    if (-not (Test-Path $DatabasePath)) { throw "TRACE database does not exist: $DatabasePath" }
    Ensure-Directory $BackupDirectory
    if (-not (Test-Path $VenvPython)) { Ensure-Dependencies | Out-Null }
    $destination = if ($BackupPath) {
        [System.IO.Path]::GetFullPath($BackupPath)
    }
    else {
        Join-Path $BackupDirectory ("trace-iam-evidence-{0}.db" -f ([DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssZ')))
    }
    Invoke-External -FilePath $VenvPython -Arguments @($DatabaseUtility, 'backup', $DatabasePath, $destination)
    Write-Host "Backup created: $destination"
}

function Restore-Trace {
    if (-not $RestorePath) { throw '-RestorePath is required for restore.' }
    $state = Read-State
    if ($state -and ((Test-ProcessAlive $state.backend_pid) -or (Test-ProcessAlive $state.frontend_pid))) {
        throw 'Stop TRACE before restoring a database.'
    }
    if (-not (Test-Path $VenvPython)) { Ensure-Dependencies | Out-Null }
    $source = [System.IO.Path]::GetFullPath($RestorePath)
    Invoke-External -FilePath $VenvPython -Arguments @($DatabaseUtility, 'restore', $source, $DatabasePath)
    Write-Host "Database restored: $DatabasePath"
}

switch ($Action) {
    'start' { Start-Trace }
    'stop' { Stop-Trace }
    'status' { Show-Status }
    'diagnostics' { Show-Diagnostics }
    'backup' { Backup-Trace }
    'restore' { Restore-Trace }
}
