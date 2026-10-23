#Requires -Version 7.0
<#
.SYNOPSIS
    Builds the Windows FH2 executable (FH2 Recompiled on the ShiftGlue SDK).

.DESCRIPTION
    1. Extracts your own Forza Horizon 2 (Xbox 360) disc image into ..\assets\game_root
       with upstream's tools\fase1_extraer.py (skipped when default.xex is already there),
       and applies patches\sdk\*.patch to the ShiftGlue submodule (skipped when applied).
    2. Gets the toolchain Pinyon Shift pins (LLVM 20.1.8, CMake 3.31.10, Ninja 1.13.2):
       reused from -ToolchainRoot when present, otherwise downloaded and SHA-256 checked
       into windows\.local\toolchain.
    3. Enters the Visual Studio x64 build environment (Windows SDK headers and libraries).
    4. Configures, runs codegen (fh2_codegen), rewrites the ~470,000-call registrar as a
       table (tools\tabela_registro.py; one giant function stalls the compiler) and builds.

    Output: windows\out\build\win-amd64-release\fh2.exe plus its DLLs (rexruntime,
    rexgpu-fh1, ...). Run it with run.ps1.

.EXAMPLE
    pwsh -File windows\build.ps1 -IsoPath "E:\...\FH2.iso"
#>
param(
    [string]$IsoPath,
    [int]$Jobs = 8,
    [string]$ToolchainRoot = (Join-Path $PSScriptRoot '..\..\dbce-mods-forza-horizon\.local\toolchain'),
    [switch]$ConfigureOnly
)
$ErrorActionPreference = 'Stop'
$windows = $PSScriptRoot
$repo = (Resolve-Path (Join-Path $windows '..')).Path
$gameRoot = Join-Path $repo 'assets\game_root'
$logs = Join-Path $windows '.local\logs'
New-Item -ItemType Directory -Force $logs | Out-Null

function Step([string]$text) { Write-Host "`n=== $text" -ForegroundColor Cyan }

# --- 1. Game files -----------------------------------------------------------------
if (-not (Test-Path (Join-Path $gameRoot 'default.xex'))) {
    if (-not $IsoPath) { throw "No game files at $gameRoot. Pass -IsoPath <your FH2 Xbox 360 ISO>." }
    Step "Extracting $IsoPath -> $gameRoot"
    & python -I (Join-Path $repo 'tools\fase1_extraer.py') $IsoPath -o $gameRoot
    if ($LASTEXITCODE) { throw "fase1_extraer.py failed ($LASTEXITCODE)" }
}

# --- 1b. SDK patches (patches\sdk, in name order; the submodule stays on its upstream commit) ---
$sdk = Join-Path $windows 'thirdparty\shiftglue-sdk'
foreach ($patch in Get-ChildItem (Join-Path $windows 'patches\sdk') -Filter '*.patch' | Sort-Object Name) {
    & git -C $sdk apply --reverse --check $patch.FullName 2>$null
    if (-not $LASTEXITCODE) { continue }  # already applied
    Step "SDK patch $($patch.Name)"
    & git -C $sdk apply $patch.FullName
    if ($LASTEXITCODE) { throw "$($patch.Name) does not apply to $sdk (git submodule update resets it)" }
}

# --- 2. Toolchain (same pins as Pinyon Shift config/release-toolchain.json) ----------
$pins = @(
    @{ name = 'llvm-20.1.8'; exe = 'bin\clang.exe'; kind = 'tar.xz'
       url = 'https://github.com/llvm/llvm-project/releases/download/llvmorg-20.1.8/clang%2Bllvm-20.1.8-x86_64-pc-windows-msvc.tar.xz'
       sha256 = 'F229769F11D6A6EDC8ADA599C0CDA964B7DEE6AB1A08C6CF9DD7F513E85B107F' },
    @{ name = 'cmake-3.31.10-windows-x86_64'; exe = 'bin\cmake.exe'; kind = 'zip'
       url = 'https://github.com/Kitware/CMake/releases/download/v3.31.10/cmake-3.31.10-windows-x86_64.zip'
       sha256 = '13D1A463D7130DF5339BAEDD63D8AE990AAF385062B2F42F372796143AE94086' },
    @{ name = 'ninja-1.13.2'; exe = 'ninja.exe'; kind = 'zip'
       url = 'https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip'
       sha256 = '07FC8261B42B20E71D1720B39068C2E14FFCEE6396B76FB7A795FB460B78DC65' }
)
$localTools = Join-Path $windows '.local\toolchain'
$toolDirs = @{}
foreach ($pin in $pins) {
    $found = $null
    foreach ($root in @($ToolchainRoot, $localTools)) {
        if (-not $root) { continue }
        $dir = Join-Path $root $pin.name
        if (Test-Path (Join-Path $dir $pin.exe)) { $found = $dir; break }
    }
    if (-not $found) {
        Step "Downloading $($pin.name)"
        New-Item -ItemType Directory -Force $localTools | Out-Null
        $archive = Join-Path $localTools ($pin.name + '.' + $pin.kind)
        Invoke-WebRequest -Uri $pin.url -OutFile $archive -UseBasicParsing
        $hash = (Get-FileHash $archive -Algorithm SHA256).Hash
        if ($hash -ne $pin.sha256) { Remove-Item $archive; throw "$($pin.name): SHA-256 $hash does not match the pin" }
        $found = Join-Path $localTools $pin.name
        New-Item -ItemType Directory -Force $found | Out-Null
        if ($pin.kind -eq 'zip') { Expand-Archive $archive -DestinationPath $found -Force }
        else { tar -xf $archive -C $found --strip-components=1; if ($LASTEXITCODE) { throw "tar failed for $archive" } }
        # Zips that hold one top-level folder (CMake) are flattened so exe paths match the pin.
        if (-not (Test-Path (Join-Path $found $pin.exe))) {
            $inner = Get-ChildItem $found -Directory | Select-Object -First 1
            if ($inner -and (Test-Path (Join-Path $inner.FullName $pin.exe))) { $found = $inner.FullName }
        }
        Remove-Item $archive
        if (-not (Test-Path (Join-Path $found $pin.exe))) { throw "$($pin.name): $($pin.exe) missing after extraction" }
    }
    $toolDirs[$pin.name] = $found
}

# --- 3. Visual Studio x64 environment ----------------------------------------------
Step 'Entering the Visual Studio x64 build environment'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vsRoot = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsRoot) { throw 'Visual Studio 2022 / Build Tools with the C++ workload not found.' }
$devCmd = Join-Path $vsRoot 'Common7\Tools\VsDevCmd.bat'
$marker = '::fh2-environment::'
$envLines = & $env:ComSpec /d /s /c "`"$devCmd`" -arch=x64 -host_arch=x64 >nul && echo $marker&& set"
$seen = $false
foreach ($line in $envLines) {
    if ($line.Trim() -eq $marker) { $seen = $true; continue }
    if (-not $seen) { continue }
    $i = $line.IndexOf('=')
    if ($i -gt 0) { [Environment]::SetEnvironmentVariable($line.Substring(0, $i), $line.Substring($i + 1), 'Process') }
}
if (-not $seen) { throw "VsDevCmd failed: $devCmd" }
$env:PATH = (@(
    (Join-Path $toolDirs['llvm-20.1.8'] 'bin'),
    (Join-Path $toolDirs['cmake-3.31.10-windows-x86_64'] 'bin'),
    $toolDirs['ninja-1.13.2']) -join ';') + ';' + $env:PATH
$env:CMAKE_BUILD_PARALLEL_LEVEL = "$Jobs"
& clang --version | Select-Object -First 1
& cmake --version | Select-Object -First 1

# --- 4. Configure, codegen, registrar table, build ---------------------------------
Push-Location $windows
try {
    Step 'Configure (win-amd64-release)'
    & cmake --preset win-amd64-release 2>&1 | Tee-Object (Join-Path $logs 'configure.log')
    if ($LASTEXITCODE) { throw "configure failed ($LASTEXITCODE), see $logs\configure.log" }
    if ($ConfigureOnly) { return }

    Step 'Code generation (fh2_codegen)'
    & cmake --build --preset win-amd64-release --target fh2_codegen 2>&1 | Tee-Object (Join-Path $logs 'codegen.log')
    if ($LASTEXITCODE) { throw "codegen failed ($LASTEXITCODE), see $logs\codegen.log" }

    # Codegen wrote sources.cmake on its first run; configure again so the recompiled
    # sources become part of the build.
    & cmake --preset win-amd64-release | Out-Null
    if ($LASTEXITCODE) { throw "reconfigure failed ($LASTEXITCODE)" }

    $register = Join-Path $windows 'generated\default\fh2_register.cpp'
    if (Test-Path $register) {
        Step 'Registrar as a table (tabela_registro.py)'
        & python -I (Join-Path $windows 'tools\tabela_registro.py') $register
        # Exit 1 with "already a table?" is the normal result on a rebuild.
        $LASTEXITCODE = 0
    }

    Step "Build (ninja -j$Jobs)"
    & cmake --build --preset win-amd64-release 2>&1 | Tee-Object (Join-Path $logs 'build.log')
    if ($LASTEXITCODE) { throw "build failed ($LASTEXITCODE), see $logs\build.log" }
    $exe = Join-Path $windows 'out\build\win-amd64-release\fh2.exe'
    Step "Built $exe"
    Get-Item $exe | Select-Object FullName, Length, LastWriteTime
}
finally { Pop-Location }
