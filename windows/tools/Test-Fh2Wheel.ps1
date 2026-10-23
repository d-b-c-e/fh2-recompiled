#Requires -Version 7.0
<#
.SYNOPSIS
    Offline check of Set-Fh2Wheel.ps1 on a scratch fh2.toml (no game, no wheel).

.DESCRIPTION
    Only the passed settings change; comments, other keys and tables are kept, line endings
    too; new keys go above the first table; strings are escaped; '' removes a setting; a
    run with no settings writes nothing.

.EXAMPLE
    pwsh -File windows\tools\Test-Fh2Wheel.ps1
#>
$ErrorActionPreference = 'Stop'
$set = Join-Path $PSScriptRoot 'Set-Fh2Wheel.ps1'
$dir = Join-Path ([IO.Path]::GetTempPath()) "fh2-wheel-test-$PID"
$config = Join-Path $dir 'fh2.toml'
function Check([string]$label, [string]$expected) {
    $actual = [IO.File]::ReadAllText($config)
    if ($actual -cne $expected) { throw "$label`n--- expected`n$expected--- actual`n$actual" }
    Write-Host "ok   $label"
}
New-Item -ItemType Directory -Force $dir | Out-Null
try {
    $n = "`r`n"
    [IO.File]::WriteAllText($config, "# Auto-generated cvar configuration${n}launcher_schema = 3${n}wheel_ffb_strength = 40${n}${n}[gpu]${n}wheel_ffb_strength = 7${n}")

    & $set -Config $config -Enabled on -Strength 15 -Throttle '+axis2' -Device 'path:\\?\HID#a"b' | Out-Null
    Check 'set: replaced, added above the table, others kept' ("# Auto-generated cvar configuration${n}launcher_schema = 3${n}" +
        "wheel_enabled = true${n}wheel_device = `"path:\\\\?\\HID#a\`"b`"${n}wheel_throttle = `"+axis2`"${n}wheel_ffb_strength = 15${n}" +
        "${n}[gpu]${n}wheel_ffb_strength = 7${n}")
    if (@(Get-ChildItem $dir -Filter 'fh2.toml.wheel-backup-*').Count -ne 1) { throw 'expected one backup' }
    Write-Host 'ok   backup written'

    & $set -Config $config -Throttle '' -SteeringAxis 0 -Invert off | Out-Null
    Check "'' removes, 0 and off are written" ("# Auto-generated cvar configuration${n}launcher_schema = 3${n}" +
        "wheel_enabled = true${n}wheel_device = `"path:\\\\?\\HID#a\`"b`"${n}wheel_ffb_strength = 15${n}" +
        "wheel_steering_axis = 0${n}wheel_ffb_invert = false${n}${n}[gpu]${n}wheel_ffb_strength = 7${n}")

    $before = [IO.File]::ReadAllText($config)
    $backups = @(Get-ChildItem $dir -Filter 'fh2.toml.wheel-backup-*').Count
    & $set -Config $config | Out-Null
    Check 'show only: unchanged' $before
    if (@(Get-ChildItem $dir -Filter 'fh2.toml.wheel-backup-*').Count -ne $backups) { throw 'show only wrote a backup' }

    Remove-Item $config
    & $set -Config $config -Enabled on | Out-Null
    Check 'new file' "wheel_enabled = true`n"
    Write-Host 'PASS'
} finally {
    Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
}
