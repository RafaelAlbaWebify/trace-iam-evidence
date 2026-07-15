[CmdletBinding()]
param(
    [Parameter()]
    [string]$DestinationDirectory = (Join-Path $HOME 'Downloads'),

    [Parameter()]
    [string]$OutputName,

    [Parameter()]
    [switch]$KeepStaging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$timestamp = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssZ')
if ([string]::IsNullOrWhiteSpace($OutputName)) {
    $OutputName = "TRACE_PORTABLE_REVIEW_$timestamp.zip"
}
if (-not $OutputName.EndsWith('.zip', [System.StringComparison]::OrdinalIgnoreCase)) {
    $OutputName = "$OutputName.zip"
}

$destination = [System.IO.Path]::GetFullPath($DestinationDirectory)
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-portable-review-{0}" -f [guid]::NewGuid().ToString('N'))
$packageRoot = Join-Path $stagingRoot 'TRACE_PORTABLE_REVIEW'
$sourceRoot = Join-Path $packageRoot 'source'
$proofRoot = Join-Path $packageRoot 'proof'
$zipPath = Join-Path $destination $OutputName

$includePaths = @(
    '.github/workflows',
    'backend',
    'docs',
    'examples',
    'frontend',
    'scripts',
    '.gitignore',
    'CHANGELOG.md',
    'LICENSE',
    'README.md'
)
$excludedDirectoryNames = @(
    '.git', '.trace-runtime', '.venv', 'venv', 'node_modules', '__pycache__',
    '.pytest_cache', '.mypy_cache', '.ruff_cache', 'dist', 'build', 'coverage',
    'runtime', 'state', 'logs', 'backups', 'e2e-artifacts', 'playwright-report', 'test-results'
)
$excludedExtensions = @('.db', '.sqlite', '.sqlite3', '.pem', '.key', '.pfx', '.p12')
$excludedNames = @('.env', '.env.local', '.env.production', 'runtime.json')

function Test-SafeRelativePath {
    param([Parameter(Mandatory)][string]$RelativePath)

    $segments = $RelativePath -split '[\\/]'
    foreach ($segment in $segments) {
        if ($excludedDirectoryNames -contains $segment) { return $false }
    }
    $name = [System.IO.Path]::GetFileName($RelativePath)
    if ($excludedNames -contains $name) { return $false }
    $extension = [System.IO.Path]::GetExtension($RelativePath)
    if ($excludedExtensions -contains $extension.ToLowerInvariant()) { return $false }
    return $true
}

function Copy-PublicSafePath {
    param([Parameter(Mandatory)][string]$RelativePath)

    $source = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path $source)) { return }
    $destinationPath = Join-Path $sourceRoot $RelativePath
    if ((Get-Item $source).PSIsContainer) {
        Get-ChildItem $source -File -Recurse | ForEach-Object {
            $relativeFile = [System.IO.Path]::GetRelativePath($repoRoot, $_.FullName)
            if (-not (Test-SafeRelativePath $relativeFile)) { return }
            $target = Join-Path $sourceRoot $relativeFile
            New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
            Copy-Item $_.FullName $target -Force
        }
    }
    elseif (Test-SafeRelativePath $RelativePath) {
        New-Item -ItemType Directory -Path (Split-Path $destinationPath -Parent) -Force | Out-Null
        Copy-Item $source $destinationPath -Force
    }
}

function Invoke-CommandText {
    param(
        [Parameter(Mandatory)][string]$Command,
        [Parameter()][string[]]$Arguments = @()
    )

    $resolved = Get-Command $Command -ErrorAction SilentlyContinue
    if ($null -eq $resolved) { return 'unavailable' }
    try {
        $result = & $resolved.Source @Arguments 2>$null
        if ($LASTEXITCODE -ne 0) { return 'unavailable' }
        return (($result | Out-String).Trim())
    }
    catch {
        return 'unavailable'
    }
}

function Invoke-GitText {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $result = & git -C $repoRoot @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) { return 'unavailable' }
    return (($result | Out-String).Trim())
}

try {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    New-Item -ItemType Directory -Path $sourceRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $proofRoot -Force | Out-Null

    foreach ($relativePath in $includePaths) {
        Copy-PublicSafePath -RelativePath $relativePath
    }

    $metadata = [ordered]@{
        product = 'TRACE IAM Evidence'
        generated_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        source_commit = Invoke-GitText @('rev-parse', 'HEAD')
        source_branch = Invoke-GitText @('branch', '--show-current')
        repository = Invoke-GitText @('remote', 'get-url', 'origin')
        package_type = 'public-safe portable review'
        runtime_data_included = $false
        secrets_included = $false
    }
    $metadata | ConvertTo-Json | Set-Content (Join-Path $proofRoot 'SOURCE_METADATA.json') -Encoding UTF8

    $diagnostics = [ordered]@{
        generated_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        operating_system = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
        operating_system_architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        process_architecture = [System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString()
        powershell_version = $PSVersionTable.PSVersion.ToString()
        git_version = Invoke-CommandText -Command 'git' -Arguments @('--version')
        python_version = Invoke-CommandText -Command 'python' -Arguments @('--version')
        node_version = Invoke-CommandText -Command 'node' -Arguments @('--version')
        npm_version = Invoke-CommandText -Command 'npm' -Arguments @('--version')
        source_file_count = @(Get-ChildItem $sourceRoot -File -Recurse).Count
        package_destination = $zipPath
        runtime_state_collected = $false
        credentials_collected = $false
        local_evidence_collected = $false
    }
    $diagnostics | ConvertTo-Json | Set-Content (Join-Path $proofRoot 'PACKAGE_DIAGNOSTICS.json') -Encoding UTF8

    $scenarioFiles = @(
        Get-ChildItem (Join-Path $sourceRoot 'examples') -File -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object { [System.IO.Path]::GetRelativePath($packageRoot, $_.FullName).Replace('\\', '/') }
    )
    $workflowFiles = @(
        Get-ChildItem (Join-Path $sourceRoot '.github\workflows') -File -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object { [System.IO.Path]::GetRelativePath($packageRoot, $_.FullName).Replace('\\', '/') }
    )
    $releaseEvidence = [ordered]@{
        evidence_type = 'public-safe source and release-proof inputs'
        scenario_files = $scenarioFiles
        workflow_files = $workflowFiles
        generated_reports_included = $false
        explanation = 'The package contains public-safe scenario inputs, release builders, tests and workflow definitions. Live workspace data and generated local reports are deliberately excluded.'
    }
    $releaseEvidence | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $proofRoot 'RELEASE_EVIDENCE.json') -Encoding UTF8

    @'
# TRACE Portable Review

This archive is a public-safe review package generated from the TRACE IAM Evidence repository.

## Review order

1. Read `source/README.md` for scope and safety boundaries.
2. Read `source/docs/architecture-diagram.md`, `source/docs/setup-and-demo.md`, and `source/docs/known-limitations.md`.
3. Inspect `proof/SOURCE_METADATA.json`, `proof/PACKAGE_DIAGNOSTICS.json`, `proof/RELEASE_EVIDENCE.json`, and `proof/SHA256SUMS.txt`.
4. Review the implementation and tests under `source/backend`, `source/frontend`, and `source/scripts`.

## Deliberate exclusions

The package excludes Git metadata, virtual environments, dependency directories, build outputs, runtime state, logs, backups, SQLite databases, environment files, private keys, certificates, and local evidence.

The archive is for code and architecture review. It is not a backup of a live TRACE workspace.
'@ | Set-Content (Join-Path $packageRoot 'REVIEW_INSTRUCTIONS.md') -Encoding UTF8

    $manifestPath = Join-Path $proofRoot 'SHA256SUMS.txt'
    Get-ChildItem $packageRoot -File -Recurse |
        Where-Object { $_.FullName -ne $manifestPath } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = [System.IO.Path]::GetRelativePath($packageRoot, $_.FullName).Replace('\\', '/')
            $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            "$hash  $relative"
        } | Set-Content $manifestPath -Encoding ascii

    Compress-Archive -Path $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Host "Portable review ZIP created: $zipPath"
    Write-Output $zipPath
}
finally {
    if (-not $KeepStaging) {
        Remove-Item $stagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
