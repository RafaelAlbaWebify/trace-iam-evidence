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

# The script lives in <repo>/scripts, so its parent directory is always the repository root.
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

Invoke-Git -Arguments @('fetch', '--prune', $Remote)

$workingTree = (& git -C $script:RepoRoot status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect the working tree.'
}
if ($workingTree) {
    throw 'The repository has uncommitted changes. Commit or stash them before publishing a release tag.'
}

Invoke-Git -Arguments @('checkout', 'main')
Invoke-Git -Arguments @('pull', '--ff-only', $Remote, 'main')
Invoke-Git -Arguments @('rev-parse', '--verify', "$Commit^{commit}")

$mainCommit = (& git -C $script:RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to resolve the current main commit.'
}
if ($mainCommit -ne $Commit) {
    throw "Main is at '$mainCommit', not the expected release commit '$Commit'. Refusing to tag a different commit."
}

$localTag = (& git -C $script:RepoRoot tag --list $Tag).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect local tag '$Tag'."
}
if ($localTag) {
    $localTarget = (& git -C $script:RepoRoot rev-list -n 1 $Tag).Trim()
    if ($localTarget -ne $Commit) {
        throw "Local tag '$Tag' already points to '$localTarget', not '$Commit'."
    }
    Write-Host "Local tag '$Tag' already points to the expected commit."
}

$remoteTag = (& git -C $script:RepoRoot ls-remote --tags $Remote "refs/tags/$Tag").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect remote tag '$Tag'."
}
if ($remoteTag) {
    $remoteTarget = ($remoteTag -split '\s+')[0]
    if ($remoteTarget -ne $Commit) {
        throw "Remote tag '$Tag' already points to '$remoteTarget', not '$Commit'."
    }
    Write-Host "Remote tag '$Tag' already exists at the expected commit. Nothing to publish."
    exit 0
}

if (-not $localTag) {
    if ($PSCmdlet.ShouldProcess("$Commit", "Create annotated tag $Tag")) {
        Invoke-Git -Arguments @('tag', '-a', $Tag, $Commit, '-m', "TRACE IAM Evidence $Tag")
    }
}

if ($PSCmdlet.ShouldProcess("$Remote", "Push tag $Tag")) {
    Invoke-Git -Arguments @('push', $Remote, "refs/tags/$Tag")
}

Write-Host "Published '$Tag' at '$Commit'."
Write-Host 'GitHub Actions tag workflows should now start automatically.'
