[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter()]
    [ValidatePattern('^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Tag = 'v0.1.0-rc.1',

    [Parameter()]
    [ValidatePattern('^[0-9a-fA-F]{7,40}$')]
    [string]$Commit = 'c343ce8f60748bb994b1ddf0114527621b9ad1cc',

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$Remote = 'origin'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-GitProcess {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [Parameter()]
        [switch]$AllowFailure
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = 'git'
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    $startInfo.WorkingDirectory = $script:RepoRoot

    foreach ($argument in $Arguments) {
        [void]$startInfo.ArgumentList.Add($argument)
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo

    try {
        if (-not $process.Start()) {
            throw 'Git process could not be started.'
        }
        $standardOutput = $process.StandardOutput.ReadToEnd()
        $standardError = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
    }
    finally {
        $process.Dispose()
    }

    $result = [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut   = if ($null -eq $standardOutput) { '' } else { $standardOutput.Trim() }
        StdErr   = if ($null -eq $standardError) { '' } else { $standardError.Trim() }
        Command  = "git $($Arguments -join ' ')"
    }

    if (-not $AllowFailure -and $result.ExitCode -ne 0) {
        $detail = if ([string]::IsNullOrWhiteSpace($result.StdErr)) {
            "exit code $($result.ExitCode)"
        }
        else {
            $result.StdErr
        }
        throw "Git command failed: $($result.Command)`n$detail"
    }

    return $result
}

function Write-GitOutput {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Result
    )

    if (-not [string]::IsNullOrWhiteSpace($Result.StdOut)) {
        Write-Host $Result.StdOut
    }
    if (-not [string]::IsNullOrWhiteSpace($Result.StdErr)) {
        Write-Host $Result.StdErr
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is not installed or is not available in PATH.'
}

# Repository scripts resolve every path from their own location, never from the caller's current directory.
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if (-not (Test-Path (Join-Path $script:RepoRoot '.git'))) {
    throw "Repository metadata was not found at '$script:RepoRoot'."
}

$remoteResult = Invoke-GitProcess -Arguments @('remote', 'get-url', $Remote)
if ([string]::IsNullOrWhiteSpace($remoteResult.StdOut)) {
    throw "Git remote '$Remote' has no configured URL."
}

Write-Host "Repository: $script:RepoRoot"
Write-Host "Remote:     $Remote ($($remoteResult.StdOut))"
Write-Host "Tag:        $Tag"
Write-Host "Commit:     $Commit"

$fetchResult = Invoke-GitProcess -Arguments @('fetch', '--prune', '--tags', $Remote)
Write-GitOutput -Result $fetchResult

$statusResult = Invoke-GitProcess -Arguments @('status', '--porcelain')
if (-not [string]::IsNullOrWhiteSpace($statusResult.StdOut)) {
    throw 'The repository has uncommitted changes. Commit or stash them before publishing a release tag.'
}

$checkoutResult = Invoke-GitProcess -Arguments @('checkout', 'main')
Write-GitOutput -Result $checkoutResult

$pullResult = Invoke-GitProcess -Arguments @('pull', '--ff-only', $Remote, 'main')
Write-GitOutput -Result $pullResult

$commitResult = Invoke-GitProcess -Arguments @('rev-parse', '--verify', "$Commit^{commit}")
if ([string]::IsNullOrWhiteSpace($commitResult.StdOut)) {
    throw "Release commit '$Commit' could not be resolved."
}
$resolvedCommit = $commitResult.StdOut

$ancestorResult = Invoke-GitProcess -Arguments @(
    'merge-base',
    '--is-ancestor',
    $resolvedCommit,
    "$Remote/main"
) -AllowFailure
if ($ancestorResult.ExitCode -ne 0) {
    throw "Release commit '$resolvedCommit' is not an ancestor of '$Remote/main'."
}

$localTagResult = Invoke-GitProcess -Arguments @('tag', '--list', $Tag)
$localTagExists = -not [string]::IsNullOrWhiteSpace($localTagResult.StdOut)
if ($localTagExists) {
    $localTargetResult = Invoke-GitProcess -Arguments @('rev-list', '-n', '1', $Tag)
    if ($localTargetResult.StdOut -ne $resolvedCommit) {
        throw "Local tag '$Tag' points to '$($localTargetResult.StdOut)', not '$resolvedCommit'."
    }
    Write-Host "Local tag '$Tag' already points to the expected commit."
}

$remoteTagResult = Invoke-GitProcess -Arguments @(
    'ls-remote',
    '--tags',
    $Remote,
    "refs/tags/$Tag",
    "refs/tags/$Tag^{}"
)
$remoteTagLines = @(
    $remoteTagResult.StdOut -split "`r?`n" |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
)

if ($remoteTagLines.Count -gt 0) {
    $escapedTag = [regex]::Escape($Tag)
    $peeledLine = $remoteTagLines |
        Where-Object { $_ -match "refs/tags/$escapedTag\^\{\}$" } |
        Select-Object -First 1
    $selectedLine = if ($null -ne $peeledLine) {
        [string]$peeledLine
    }
    else {
        [string]$remoteTagLines[0]
    }
    $remoteTarget = ($selectedLine -split '\s+')[0]
    if ($remoteTarget -ne $resolvedCommit) {
        throw "Remote tag '$Tag' points to '$remoteTarget', not '$resolvedCommit'."
    }
    Write-Host "Remote tag '$Tag' already exists at the expected commit. Nothing to publish."
    return
}

if (-not $localTagExists) {
    if ($PSCmdlet.ShouldProcess($resolvedCommit, "Create annotated tag $Tag")) {
        $createResult = Invoke-GitProcess -Arguments @(
            'tag',
            '-a',
            $Tag,
            $resolvedCommit,
            '-m',
            "TRACE IAM Evidence $Tag"
        )
        Write-GitOutput -Result $createResult
    }
}

if ($PSCmdlet.ShouldProcess($Remote, "Push tag $Tag")) {
    $pushResult = Invoke-GitProcess -Arguments @('push', $Remote, "refs/tags/$Tag")
    Write-GitOutput -Result $pushResult
}

if ($WhatIfPreference) {
    Write-Host "WhatIf completed. Tag '$Tag' was not created or pushed."
}
else {
    Write-Host "Published '$Tag' at '$resolvedCommit'."
    Write-Host 'GitHub Actions tag workflows should now start automatically.'
}
