Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$exportScript = Join-Path $PSScriptRoot 'export_portable_review.ps1'
$tempRoot = [System.IO.Path]::GetFullPath((Join-Path ([System.IO.Path]::GetTempPath()) ("trace-portable-review-test-{0}" -f [guid]::NewGuid().ToString('N'))))
$outputName = 'TRACE_PORTABLE_REVIEW_TEST.zip'
$zipPath = [System.IO.Path]::GetFullPath((Join-Path $tempRoot $outputName))
$extractRoot = Join-Path $tempRoot 'extracted'

function Test-SamePath {
    param([Parameter(Mandatory)][string]$Left, [Parameter(Mandatory)][string]$Right)
    return [string]::Equals(
        [System.IO.Path]::GetFullPath($Left).TrimEnd('\', '/'),
        [System.IO.Path]::GetFullPath($Right).TrimEnd('\', '/'),
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Test-PortableReviewArchive {
    param([Parameter(Mandatory)][string]$ArchivePath)

    Write-Host 'Portable stage: expand archive'
    if (Test-Path $extractRoot) { Remove-Item $extractRoot -Recurse -Force }
    Expand-Archive -Path $ArchivePath -DestinationPath $extractRoot -Force
    $packageRoot = Join-Path $extractRoot 'TRACE_PORTABLE_REVIEW'

    Write-Host 'Portable stage: required content'
    foreach ($required in @(
        'REVIEW_INSTRUCTIONS.md',
        'proof\SOURCE_METADATA.json',
        'proof\PACKAGE_DIAGNOSTICS.json',
        'proof\RELEASE_EVIDENCE.json',
        'proof\SHA256SUMS.txt',
        'source\README.md',
        'source\scripts\trace.ps1'
    )) {
        if (-not (Test-Path (Join-Path $packageRoot $required))) { throw "Portable review package is missing: $required" }
    }

    Write-Host 'Portable stage: exclusion scan'
    $forbiddenPatterns = @(
        '\\.git(?:\\|$)', '\\node_modules(?:\\|$)', '\\.trace-runtime(?:\\|$)',
        '\\runtime(?:\\|$)', '\\state(?:\\|$)', '\\logs(?:\\|$)', '\\backups(?:\\|$)',
        '\.db$', '\.sqlite3?$', '\.env(?:\.|$)', '\.(?:pem|key|pfx|p12)$'
    )
    Get-ChildItem $packageRoot -Recurse | ForEach-Object {
        foreach ($pattern in $forbiddenPatterns) {
            if ($_.FullName -match $pattern) { throw "Forbidden path included in portable review package: $($_.FullName)" }
        }
    }

    Write-Host 'Portable stage: metadata and diagnostics'
    $metadata = Get-Content (Join-Path $packageRoot 'proof\SOURCE_METADATA.json') -Raw | ConvertFrom-Json
    if ($metadata.runtime_data_included -ne $false) { throw 'Metadata does not declare runtime data exclusion.' }
    if ($metadata.secrets_included -ne $false) { throw 'Metadata does not declare secret exclusion.' }

    $diagnostics = Get-Content (Join-Path $packageRoot 'proof\PACKAGE_DIAGNOSTICS.json') -Raw | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$diagnostics.operating_system)) { throw 'Package diagnostics do not identify the operating system.' }
    if ([string]::IsNullOrWhiteSpace([string]$diagnostics.powershell_version)) { throw 'Package diagnostics do not identify PowerShell.' }
    if ([int]$diagnostics.source_file_count -lt 1) { throw 'Package diagnostics report no source files.' }
    if ($diagnostics.runtime_state_collected -ne $false) { throw 'Package diagnostics do not confirm runtime-state exclusion.' }
    if ($diagnostics.credentials_collected -ne $false) { throw 'Package diagnostics do not confirm credential exclusion.' }
    if ($diagnostics.local_evidence_collected -ne $false) { throw 'Package diagnostics do not confirm local-evidence exclusion.' }

    Write-Host 'Portable stage: release evidence'
    $releaseEvidence = Get-Content (Join-Path $packageRoot 'proof\RELEASE_EVIDENCE.json') -Raw | ConvertFrom-Json
    if (@($releaseEvidence.scenario_files).Count -lt 1) { throw 'Portable review package contains no public-safe scenario evidence.' }
    if (@($releaseEvidence.workflow_files).Count -lt 1) { throw 'Portable review package contains no release workflow evidence.' }
    if ($releaseEvidence.generated_reports_included -ne $false) { throw 'Release evidence metadata incorrectly claims generated reports are included.' }

    Write-Host 'Portable stage: SHA-256 manifest'
    $manifestPath = Join-Path $packageRoot 'proof\SHA256SUMS.txt'
    $manifestLines = @(Get-Content $manifestPath | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($manifestLines.Count -lt 8) { throw 'Integrity manifest is unexpectedly small.' }
    foreach ($line in $manifestLines) {
        if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { throw "Invalid manifest line: $line" }
        $expected = $Matches[1]
        $relative = $Matches[2].Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $filePath = Join-Path $packageRoot $relative
        if (-not (Test-Path $filePath -PathType Leaf)) { throw "Manifest path is missing: $relative" }
        $actual = (Get-FileHash $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { throw "Manifest hash mismatch: $relative" }
    }
}

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    foreach ($attempt in 1..2) {
        Write-Host "Portable stage: export attempt $attempt"
        $createdPath = [string](& $exportScript -DestinationDirectory $tempRoot -OutputName $outputName | Select-Object -Last 1)
        if ([string]::IsNullOrWhiteSpace($createdPath)) { throw "Portable review exporter returned no path on attempt $attempt." }
        if (-not (Test-SamePath $createdPath $zipPath)) { throw "Unexpected ZIP path on attempt $attempt: $createdPath" }
        if (-not (Test-Path $zipPath -PathType Leaf)) { throw "Portable review ZIP was not created on attempt $attempt: $zipPath" }
        Test-PortableReviewArchive -ArchivePath $zipPath
    }
    Write-Host 'TRACE portable review ZIP safety, integrity and repeatability test passed.'
}
catch {
    Write-Error "TRACE portable review acceptance failed: $($_.Exception.Message)"
    throw
}
finally {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
