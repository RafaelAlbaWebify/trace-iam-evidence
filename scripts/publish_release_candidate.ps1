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

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is not installed or is not available in PATH.'
}

# Every repository script must resolve paths from its own file location, never from the caller's current directory.
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if (-not (Test-Path (Join-Path $script:RepoRoot '.git'))) {
    throw "Repository metadata was not found at '$script:RepoRoot'."
}

$remoteUrl = (& git -C $script:RepoRoot remote get-url $Remote 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($remoteUrl)) {
    throw "Git remote '$Remote' is not configured for '$script:RepoRoot'."
}

Write-Host "Repository: $script:RepoRoot"
Write-Host "Remote:     $Remote ($remoteUrl)"
Write-Host "Tag:        $Tag"
Write-Host "Commit:     $Commit"

Invoke-Git -Arguments @('fetch', '--prune', '--tags', $Remote)

$workingTree = (& git -C $script:RepoRoot status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect the working tree.'
}
if ($workingTree) {
    throw 'The repository has uncommitted changes. Commit or stash them before publishing a release tag.'
}

Invoke-Git -Arguments @('checkout', 'main')
Invoke-Git -Arguments @('pull', '--ff-only', $Remote, 'main')

$resolvedCommit = (& git -C $script:RepoRoot rev-parse --verify "$Commit^{commit}").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($resolvedCommit)) {
    throw "Release commit '$Commit' does not exist in the local repository."
}

& git -C $script:RepoRoot merge-base --is-ancestor $resolvedCommit "$Remote/main"
if ($LASTEXITCODE -ne 0) {
    throw "Release commit '$resolvedCommit' is not an ancestor of '$Remote/main'. Refusing to publish an unrelated tag."
}

$localTag = (& git -C $script:RepoRoot tag --list $Tag).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect local tag '$Tag'."
}
if ($localTag) {
    $localTarget = (& git -C $script:RepoRoot rev-list -n 1 $Tag).Trim()
    if ($localTarget -ne $resolvedCommit) {
        throw "Local tag '$Tag' already points to '$localTarget', not '$resolvedCommit'."
    }
    Write-Host "Local tag '$Tag' already points to the expected commit."
}

$remoteLines = @(& git -C $script:RepoRoot ls-remote --tags $Remote "refs/tags/$Tag" "refs/tags/$Tag^{}")
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect remote tag '$Tag'."
}
if ($remoteLines.Count -gt 0) {
    $peeledLine = $remoteLines | Where-Object { $_ -match "refs/tags/$([regex]::Escape($Tag))\^\{\}$" } | Select-Object -First 1
    $selectedLine = if ($peeledLine) { $peeledLine } else { $remoteLines | Select-Object -First 1 }
    $remoteTarget = ($selectedLine -split '\s+')[0]
    if ($remoteTarget -ne $resolvedCommit) {
        throw "Remote tag '$Tag' already points to '$remoteTarget', not '$resolvedCommit'."
    }
    Write-Host "Remote tag '$Tag' already exists at the expected commit. Nothing to publish."
    exit 0
}

if (-not $localTag) {
    if ($PSCmdlet.ShouldProcess($resolvedCommit, "Create annotated tag $Tag")) {
        Invoke-Git -Arguments @('tag', '-a', $Tag, $resolvedCommit, '-m', "TRACE IAM Evidence $Tag")
    }
}

if ($PSCmdlet.ShouldProcess($Remote, "Push tag $Tag")) {
    Invoke-Git -Arguments @('push', $Remote, "refs/tags/$Tag")
}

Write-Host "Published '$Tag' at '$resolvedCommit'."
Write-Host 'GitHub Actions tag workflows should now start automatically.'
