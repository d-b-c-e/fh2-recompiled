#Requires -Version 7.0
<#
.SYNOPSIS
    Reconstructs the qualified FH2 SDK source tree from a local public-base repository.
.DESCRIPTION
    Creates only a new destination. Does not change the input repository, commit,
    initialize dependencies, build, install or contact a remote server. The local
    repository must contain public base59bc11f5; the checked cumulative patch and
    resulting Git tree are pinned. HEAD remains at the public base, with the
    qualified changes staged. See docs/SDK-SOURCE-20261102.md before building.
#>
param(
    [Parameter(Mandatory)][string]$SourceRepository,
    [Parameter(Mandatory)][string]$Destination
)
$ErrorActionPreference = 'Stop'
$base = '59bc11f546a6ea67eefcad974d0c14041b2ab20d'
$baseTree = '66caf6a1cd2f2e58ec23975da68a13b6a2bce215'
$qualifiedCommit = 'e223de8d7aff090c0acc7a519582f35631e81b21'
$qualifiedTree = 'ebabad40108102589970cd1eedf7daa17366930c'
$patchHash = 'DA79C4D98ECBA6BE0BE107887878FB7433A19CBA43A9CCAD779BEE39D7A0D76C'
$patch = Join-Path $PSScriptRoot '..\patches\shiftglue-sdk-fh2-e223.patch'

function Invoke-SourceGit([string[]]$GitArguments) {
    $output = @(& git @GitArguments 2>&1)
    if ($LASTEXITCODE) { throw "Git failed ($LASTEXITCODE): $($output -join "`n")" }
    ($output | ForEach-Object { $_.ToString() }) -join "`n"
}

$sourceItem = Get-Item -LiteralPath $SourceRepository
if (-not $sourceItem.PSIsContainer -or $sourceItem.PSProvider.Name -ne 'FileSystem') {
    throw 'SourceRepository must be an existing local Git directory.'
}
$sourcePath = $sourceItem.FullName
$destinationPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Destination)
if (Get-Item -LiteralPath $destinationPath -Force -ErrorAction SilentlyContinue) {
    throw 'Destination already exists; choose a new directory. Nothing was changed.'
}
if ((Get-FileHash -LiteralPath $patch -Algorithm SHA256).Hash -cne $patchHash) {
    throw 'Cumulative SDK patch hash mismatch. Nothing was changed.'
}
$observedBaseTree = (Invoke-SourceGit -GitArguments @('-C', $sourcePath, 'rev-parse', "$base`^{tree}")).Trim()
if ($observedBaseTree -cne $baseTree) { throw 'Public SDK base tree mismatch. Nothing was changed.' }

# All mutations below are confined to the new destination. Retain a partial
# destination on failure for inspection; never clean/reset an existing checkout.
$null = Invoke-SourceGit -GitArguments @('init', $destinationPath)
$null = Invoke-SourceGit -GitArguments @('-C', $destinationPath, 'config', 'core.autocrlf', 'false')
$null = Invoke-SourceGit -GitArguments @('-C', $destinationPath, 'fetch', '--no-tags', '--no-recurse-submodules', '--depth=1', $sourcePath, $base)
$null = Invoke-SourceGit -GitArguments @('-C', $destinationPath, '-c', 'submodule.recurse=false', 'checkout', '--detach', $base)
$null = Invoke-SourceGit -GitArguments @('-C', $destinationPath, 'apply', '--check', '--index', '--whitespace=error-all', $patch)
$null = Invoke-SourceGit -GitArguments @('-C', $destinationPath, 'apply', '--index', '--whitespace=error-all', $patch)
$tree = (Invoke-SourceGit -GitArguments @('-C', $destinationPath, 'write-tree')).Trim()
if ($tree -cne $qualifiedTree) { throw "Reconstructed SDK tree mismatch: $tree. Retained $destinationPath for inspection." }
$null = Invoke-SourceGit -GitArguments @('-C', $destinationPath, 'diff', '--exit-code', '--')
[pscustomobject]@{
    destination = $destinationPath
    baseCommit = $base
    baseTree = $baseTree
    qualifiedCommit = $qualifiedCommit
    qualifiedTree = $tree
    patchSha256 = $patchHash
    headIsQualifiedCommit = $false
    changesAreStaged = $true
    dependenciesInitialized = $false
    nativeBuildPerformed = $false
}
