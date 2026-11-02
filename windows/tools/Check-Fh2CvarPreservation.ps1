#Requires -Version 7.0
<#
.SYNOPSIS
  Tests an isolated SDK cvar.cpp with actual parser/backend code and inert files.
.DESCRIPTION
  Run from an x64 Visual Studio developer shell. BuiltSdk supplies dependencies
  and an already-qualified runtime DLL. SourceSdk supplies the candidate cvar.cpp.
  No SDK/app rebuild, game, graphics, input/device initialization or owner writes.
#>
param(
    [Parameter(Mandatory)][string]$BuiltSdk,
    [Parameter(Mandatory)][string]$SourceSdk,
    [Parameter(Mandatory)][string]$Out,
    [string]$Compiler = 'clang++.exe'
)
$ErrorActionPreference = 'Stop'
$BuiltSdk = (Resolve-Path -LiteralPath $BuiltSdk).Path
$SourceSdk = (Resolve-Path -LiteralPath $SourceSdk).Path
$Out = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)
if (Test-Path -LiteralPath $Out) { throw 'Preserve existing evidence; choose a fresh output directory.' }
$compilerPath = (Get-Command $Compiler -CommandType Application).Source
$llvm = Split-Path $compilerPath -Parent
$source = Join-Path $SourceSdk 'src/core/cvar.cpp'
$runtime = Join-Path $BuiltSdk 'out/win-amd64/rexruntime.dll'
foreach ($path in @($source, $runtime, (Join-Path $llvm 'llvm-readobj.exe'), (Join-Path $llvm 'llvm-dlltool.exe'))) {
    if (-not [IO.File]::Exists($path)) { throw "Required input missing: $path" }
}
[IO.Directory]::CreateDirectory($Out) | Out-Null
$receipt = [ordered]@{
    status = 'fail'; startedUtc = [DateTime]::UtcNow.ToString('O'); steps = @()
    gameExecuted = $false; graphicsInitialized = $false; physicalDeviceInitialized = $false
    ownerStateWritten = $false; productionCvarSha256 = (Get-FileHash -LiteralPath $source).Hash
    backendRuntimeSha256 = (Get-FileHash -LiteralPath $runtime).Hash
    compiler = $compilerPath; fixtureSha256 = [ordered]@{}
}
function Step([string]$name, [string]$program, [string[]]$arguments) {
    & $program @arguments *> (Join-Path $Out "$name.log")
    $code = $LASTEXITCODE
    $receipt.steps += [ordered]@{ name = $name; executable = $program; arguments = $arguments; exitCode = $code }
    if ($code) { throw "$name failed with $code; inspect its log." }
}
try {
    Step 'exports' (Join-Path $llvm 'llvm-readobj.exe') @('--coff-exports', $runtime)
    # Keep backend imports only: every cvar function comes from the candidate source.
    $exports = @(Get-Content -LiteralPath (Join-Path $Out 'exports.log') | ForEach-Object {
        if ($_ -match '^\s+Name: (.+)$') { $Matches[1] }
    } | Where-Object { $_ -notmatch '@cvar@rex@@' })
    if ($exports.Count -lt 100) { throw 'Unexpected runtime export map.' }
    $definition = Join-Path $Out 'backends.def'
    $imports = Join-Path $Out 'backends.lib'
    [IO.File]::WriteAllLines($definition, @('LIBRARY rexruntime.dll', 'EXPORTS') + $exports)
    Step 'imports' (Join-Path $llvm 'llvm-dlltool.exe') @('-m', 'i386:x86-64', '-d', $definition, '-l', $imports)
    Copy-Item -LiteralPath $runtime -Destination $Out
    $common = @('-std=c++23', '-O1', '-fuse-ld=lld', '-D_DLL', '-D_MT', '-Xclang', '--dependent-lib=msvcrt',
        '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN', '-DREX_PLATFORM_WINDOWS=1', '-DSPDLOG_COMPILED_LIB', '-DSPDLOG_FMT_EXTERNAL',
        "-I$SourceSdk/include", "-I$BuiltSdk/thirdparty/cli11/include", "-I$BuiltSdk/thirdparty/fmt/include",
        "-I$BuiltSdk/thirdparty/spdlog/include", "-I$BuiltSdk/thirdparty/tomlplusplus/include", $imports,
        "$BuiltSdk/out/win-amd64/fmt.lib", "$BuiltSdk/out/win-amd64/spdlog.lib")
    foreach ($name in 'fh2_cvar_preserve_fixture', 'fh2_cvar_strings_fixture') {
        $fixture = Join-Path $PSScriptRoot "$name.cpp"
        $receipt.fixtureSha256[$name] = (Get-FileHash -LiteralPath $fixture).Hash
        $exe = Join-Path $Out "$name.exe"
        Step "$name.compile" $compilerPath @($common + @($fixture, $source, '-o', $exe))
        $data = Join-Path $Out "$name-data"
        [IO.Directory]::CreateDirectory($data) | Out-Null
        Step "$name.run" $exe @($data)
        Get-Content -LiteralPath (Join-Path $Out "$name.run.log")
    }
    $receipt.status = 'pass'
} finally {
    $receipt.finishedUtc = [DateTime]::UtcNow.ToString('O')
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Out 'result.json') -Encoding utf8
}
