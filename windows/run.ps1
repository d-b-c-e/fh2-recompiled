#Requires -Version 7.0
<#
.SYNOPSIS
    Starts the Windows FH2 build against ..\assets\game_root.

.DESCRIPTION
    Same arguments as upstream's tools/rodar_pc.sh, but with the ShiftGlue FH1 renderer
    (--gpu_plugin=fh1), which the comparacao/shiftglue prototype validated on FH2.
    Saves and settings go to windows\.local\user; the log to windows\.local\logs\fh2.log.
    Extra arguments are passed to the game (for example --audio_mute=true).
#>
param([string]$BuildDir = (Join-Path $PSScriptRoot 'out\build\win-amd64-release'),
      [Parameter(ValueFromRemainingArguments)][string[]]$GameArgs)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$exe = Join-Path $BuildDir 'fh2.exe'
if (-not (Test-Path $exe)) { throw "Not built: $exe (run build.ps1)" }
$user = Join-Path $PSScriptRoot '.local\user'
$logs = Join-Path $PSScriptRoot '.local\logs'
New-Item -ItemType Directory -Force $user, $logs | Out-Null
$arguments = @(
    "--game_data_root=$(Join-Path $repo 'assets\game_root')",
    "--user_data_root=$user",
    "--log_file=$(Join-Path $logs 'fh2.log')",
    '--gpu_plugin=fh1',
    # The FH1 native executor is Vulkan-only. On Windows the SDK otherwise picks
    # Direct3D 12, every draw "Failed in backend" and the window stays white
    # (first run, 2026-10-16). Upstream's prototype ran on Linux, Vulkan by default.
    '--gpu_backend=vulkan',
    '--gpu_allow_invalid_fetch_constants=true',
    '--log_max_file_size_mb=200') + $GameArgs
Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $BuildDir
