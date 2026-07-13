[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter()]
    [ValidatePattern('^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Tag = 'v0.1.0-rc.1',

    [Parameter()]
    [ValidatePattern('^[0-9a-fA-F]{7,40}$')]
    [string]$Commit = 'c343ce8f60748bb994b1ddf0114527621b9ad1cc',

    [Parameter()]
    [string]$Remote = 'origin'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Git {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    & git -C $script:RepoRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git -C `"$script:RepoRoot`" $($Arguments -join ' ')"
    }
}

function Get-GitText {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [Parameter()]
        [switch]$AllowEmpty
    )

    $outputLines = @(& git -C $script:RepoRoot @Arguments 2>$null) |
        Where-Object { $null -ne $_ }
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw "Git command failed: git -C `"$script:RepoRoot`" $($Arguments -join ' ')"
    }

    $text = [string]::Join("`n", [string[]]$outputLines).Trim()
    if (-not $AllowEmpty -and [string]::IsNullOrWhiteSpace($text)) {
        throw "Git command returned no output: git -C `"$script:RepoRoot`" $($Arguments -join ' ')"
    }

    return $text
}

function Get-GitLines {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    $outputLines = @(& git -C $script:RepoRoot @Arguments 2>$null) |
        Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw "Git command failed: git -C `"$script:RepoRoot`" $($Arguments -join ' ')"
    }

    return [string[]]$outputLines
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is not installed or is not available in PATH.'
}

# Every repository script must resolve paths from its own file location, never from the caller's current directory.
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if (-not (Test-Path (Join-Path $script:RepoRoot '.git'))) {
    throw "Repository metadata was not found at '$script:RepoRoot'."
}

$remoteUrl = Get-GitText -Arguments @('remote', 'get-url', $Remote)

Write-Host "Repository: $script:RepoRoot"
Write-Host "Remote:     $Remote ($remoteUrl)"
Write-Host "Tag:        $Tag"
Write-Host "Commit:     $Commit"

Invoke-Git -Arguments @('fetch', '--prune', '--tags', $Remote)

$workingTree = Get-GitText -Arguments @('status', '--porcelain') -AllowEmpty
if (-not [string]::IsNullOrWhiteSpace($workingTree)) {
    throw 'The repository has uncommitted changes. Commit or stash them before publishing a release tag.'
}

Invoke-Git -Arguments @('checkout', 'main')
Invoke-Git -Arguments @('pull', '--ff-only', $Remote, 'main')

$resolvedCommit = Get-GitText -Arguments @('rev-parse', '--verify', "$Commit^{commit}")

& git -C $script:RepoRoot merge-base --is-ancestor $resolvedCommit "$Remote/main"
if ($LASTEXITCODE -ne 0) {
    throw "Release commit '$resolvedCommit' is not an ancestor of '$Remote/main'. Refusing to publish an unrelated tag."
}

$localTag = Get-GitText -Arguments @('tag', '--list', $Tag) -AllowEmpty
if (-not [string]::IsNullOrWhiteSpace($localTag)) {
    $localTarget = Get-GitText -Arguments @('rev-list', '-n', '1', $Tag)
    if ($localTarget -ne $resolvedCommit) {
        throw "Local tag '$Tag' already points to '$localTarget', not '$resolvedCommit'."
    }
    Write-Host "Local tag '$Tag' already points to the expected commit."
}

$remoteLines = @(Get-GitLines -Arguments @(
    'ls-remote',
    '--tags',
    $Remote,
    "refs/tags/$Tag",
    "refs/tags/$Tag^{}"
))
if ($remoteLines.Count -gt 0) {
    $escapedTag = [regex]::Escape($Tag)
    $peeledLine = $remoteLines |
        Where-Object { $_ -match "refs/tags/$escapedTag\^\{\}$" } |
        Select-Object -First 1
    $selectedLine = if ($peeledLine) {
        $peeledLine
    }
    else {
        $remoteLines | Select-Object -First 1
    }
    $remoteTarget = ([string]$selectedLine -split '\s+')[0]
    if ($remoteTarget -ne $resolvedCommit) {
        throw "Remote tag '$Tag' already points to '$remoteTarget', not '$resolvedCommit'."
    }
    Write-Host "Remote tag '$Tag' already exists at the expected commit. Nothing to publish."
    exit 0
}

if ([string]::IsNullOrWhiteSpace($localTag)) {
    if ($PSCmdlet.ShouldProcess($resolvedCommit, "Create annotated tag $Tag")) {
        Invoke-Git -Arguments @('tag', '-a', $Tag, $resolvedCommit, '-m', "TRACE IAM Evidence $Tag")
    }
}

if ($PSCmdlet.ShouldProcess($Remote, "Push tag $Tag")) {
    Invoke-Git -Arguments @('push', $Remote, "refs/tags/$Tag")
}

Write-Host "Published '$Tag' at '$resolvedCommit'."
Write-Host 'GitHub Actions tag workflows should now start automatically.'
