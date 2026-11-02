#Requires -Version 7.0
<# Offline reconstruction/refusal fixtures. Source repository is read-only. #>
param(
    [Parameter(Mandatory)][string]$SourceRepository,
    [Parameter(Mandatory)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$restore = Join-Path $PSScriptRoot 'Restore-Fh2SdkSource.ps1'
$outputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
if (Test-Path -LiteralPath $outputPath) { throw 'Choose a new fixture output directory.' }
[IO.Directory]::CreateDirectory($outputPath) | Out-Null
$checks = 0
function Check([bool]$Ok, [string]$Label) {
    if (-not $Ok) { throw "FAIL: $Label" }
    $script:checks++
}
$destination = Join-Path $outputPath 'qualified-sdk'
$result = & $restore -SourceRepository $SourceRepository -Destination $destination
Check ($result.qualifiedTree -ceq 'ebabad40108102589970cd1eedf7daa17366930c') 'exact qualified source tree'
$head = & git -C $destination rev-parse HEAD
if ($LASTEXITCODE) { throw 'Cannot query reconstructed HEAD.' }
Check ($head -ceq $result.baseCommit) 'public base HEAD retained'
Check (-not $result.headIsQualifiedCommit -and $result.changesAreStaged -and -not $result.nativeBuildPerformed) 'honest source-only identity'
$paths = @(& git -C $destination diff --cached --name-only)
if ($LASTEXITCODE) { throw 'Cannot query staged paths.' }
Check ($paths.Count -eq 15) 'all fifteen changed paths staged'
$null = & git -C $destination cat-file -e $result.qualifiedCommit 2>&1
Check ($LASTEXITCODE -ne 0) 'qualified tree reconstructed without private commit object'
Check (-not (Test-Path (Join-Path $destination 'thirdparty/tomlplusplus/include/toml++/toml.h'))) 'dependencies not initialized'
$sentinel = Join-Path $destination 'owner-sentinel.txt'
[IO.File]::WriteAllText($sentinel, 'keep exact bytes')
$before = [IO.File]::ReadAllText($sentinel)
$errorText = ''
try { & $restore -SourceRepository $SourceRepository -Destination $destination } catch { $errorText = $_.Exception.Message }
Check ($errorText.Contains('Destination already exists')) 'existing checkout refused'
Check ([IO.File]::ReadAllText($sentinel) -ceq $before) 'existing content retained'
$missing = Join-Path $outputPath 'missing-source'
$errorText = ''
try { & $restore -SourceRepository $missing -Destination (Join-Path $outputPath 'no-output') } catch { $errorText = $_.Exception.Message }
Check ($errorText.Length -gt 0 -and -not (Test-Path (Join-Path $outputPath 'no-output'))) 'missing source refused before destination'
$emptyRepository = Join-Path $outputPath 'empty.git'
$null = & git init --bare $emptyRepository 2>&1
if ($LASTEXITCODE) { throw 'Cannot initialize wrong-base fixture.' }
$errorText = ''
try { & $restore -SourceRepository $emptyRepository -Destination (Join-Path $outputPath 'wrong-base-output') } catch { $errorText = $_.Exception.Message }
Check ($errorText.Length -gt 0 -and -not (Test-Path (Join-Path $outputPath 'wrong-base-output'))) 'missing base object refused before destination'
# A private copy exercises the real helper's hash refusal without modifying its
# published patch or adding a product parameter used only by tests.
$copy = Join-Path $outputPath 'tampered'
[IO.Directory]::CreateDirectory((Join-Path $copy 'tools')) | Out-Null
[IO.Directory]::CreateDirectory((Join-Path $copy 'patches')) | Out-Null
Copy-Item -LiteralPath $restore -Destination (Join-Path $copy 'tools/Restore-Fh2SdkSource.ps1')
[IO.File]::WriteAllText((Join-Path $copy 'patches/shiftglue-sdk-fh2-e223.patch'), 'damaged patch')
$errorText = ''
try { & (Join-Path $copy 'tools/Restore-Fh2SdkSource.ps1') -SourceRepository $SourceRepository -Destination (Join-Path $outputPath 'tampered-output') } catch { $errorText = $_.Exception.Message }
Check ($errorText.Contains('hash mismatch') -and -not (Test-Path (Join-Path $outputPath 'tampered-output'))) 'tampered patch refused before destination'
$report = [ordered]@{checks=$checks; result=$result; observedUtc=[DateTime]::UtcNow.ToString('o'); nativeBuildPerformed=$false}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputPath 'result.json') -Encoding utf8NoBOM
Write-Host "PASS: $checks source reconstruction/refusal checks; retained $outputPath"
