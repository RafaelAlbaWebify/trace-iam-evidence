Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Native {
    param([string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory)
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FilePath
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.WorkingDirectory = $WorkingDirectory
    foreach ($argument in $Arguments) { [void]$psi.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::Start($psi)
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    $exitCode = $process.ExitCode
    $process.Dispose()
    if ($exitCode -ne 0) { throw "$FilePath $($Arguments -join ' ') failed:`n$stderr`n$stdout" }
    return $stdout.Trim()
}

$sourceScript = Join-Path $PSScriptRoot 'publish_release_candidate.ps1'
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trace-release-script-" + [guid]::NewGuid())
$remote = Join-Path $tempRoot 'remote.git'
$repo = Join-Path $tempRoot 'repo'

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    Invoke-Native git @('init', '--bare', $remote) $tempRoot | Out-Null
    Invoke-Native git @('init', '-b', 'main', $repo) $tempRoot | Out-Null
    Invoke-Native git @('config', 'user.name', 'TRACE CI') $repo | Out-Null
    Invoke-Native git @('config', 'user.email', 'trace@example.invalid') $repo | Out-Null
    Set-Content -Path (Join-Path $repo 'README.md') -Value 'release proof' -NoNewline
    Invoke-Native git @('add', 'README.md') $repo | Out-Null
    Invoke-Native git @('commit', '-m', 'Release commit') $repo | Out-Null
    $releaseCommit = Invoke-Native git @('rev-parse', 'HEAD') $repo
    Invoke-Native git @('remote', 'add', 'origin', $remote) $repo | Out-Null
    Invoke-Native git @('push', '-u', 'origin', 'main') $repo | Out-Null

    $scriptsDir = Join-Path $repo 'scripts'
    New-Item -ItemType Directory -Path $scriptsDir | Out-Null
    Copy-Item $sourceScript (Join-Path $scriptsDir 'publish_release_candidate.ps1')
    Invoke-Native git @('add', 'scripts/publish_release_candidate.ps1') $repo | Out-Null
    Invoke-Native git @('commit', '-m', 'Add publisher') $repo | Out-Null
    Invoke-Native git @('push', 'origin', 'main') $repo | Out-Null

    Push-Location $tempRoot
    try {
        & (Join-Path $scriptsDir 'publish_release_candidate.ps1') -Tag 'v9.9.9-rc.1' -Commit $releaseCommit
    }
    finally {
        Pop-Location
    }

    $remoteTarget = Invoke-Native git @('--git-dir', $remote, 'rev-list', '-n', '1', 'v9.9.9-rc.1') $tempRoot
    if ($remoteTarget -ne $releaseCommit) { throw 'Published tag points to the wrong commit.' }

    & (Join-Path $scriptsDir 'publish_release_candidate.ps1') -Tag 'v9.9.9-rc.1' -Commit $releaseCommit

    Add-Content -Path (Join-Path $repo 'README.md') -Value 'dirty'
    $failedAsExpected = $false
    try {
        & (Join-Path $scriptsDir 'publish_release_candidate.ps1') -Tag 'v9.9.9-rc.2' -Commit $releaseCommit
    }
    catch {
        $failedAsExpected = $_.Exception.Message -match 'uncommitted changes'
    }
    if (-not $failedAsExpected) { throw 'Dirty working tree was not rejected.' }

    Write-Host 'Release publisher integration tests passed.'
}
finally {
    if (Test-Path $tempRoot) { Remove-Item -Recurse -Force $tempRoot }
}
