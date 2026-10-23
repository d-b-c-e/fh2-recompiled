#Requires -Version 7.0
<#
.SYNOPSIS
    Shows or changes the racing wheel settings in fh2.toml (close the game first).

.DESCRIPTION
    With wheel_enabled on, the ShiftGlue SDK reads a wheel base, pedals and buttons raw (each
    from its own USB device if need be), presents them to FH2 as an Xbox 360 force feedback
    wheel and plays the game's own wheel effects on the base. Every setting, its default and
    how devices and inputs are named are in thirdparty\shiftglue-sdk\docs\RACING_WHEELS.md.
    The same settings are in the game's F4 settings overlay (Input).

    The scripted route, after Pinyon Shift's tools/wheel-setup/scripts/ffb-tune.ps1: only the
    settings passed are written, every other line is kept, and the file is backed up first.
    An empty string ('') removes a setting, so it goes back to its default.
    To find axis and button numbers: -Enabled on -LogInputs on, start the game, move each
    control, and read the wheel lines in windows\.local\logs\fh2.log.

.EXAMPLE
    pwsh -File windows\tools\Set-Fh2Wheel.ps1
    Shows the current wheel settings.
.EXAMPLE
    pwsh -File windows\tools\Set-Fh2Wheel.ps1 -Enabled on -Throttle axis2 -Brake axis3 -Strength 15
.EXAMPLE
    pwsh -File windows\tools\Set-Fh2Wheel.ps1 -Buttons 'GEAR1=<shifter>|0,GEAR2=<shifter>|1,REVERSE=<shifter>|7'
    An H-shifter on its own device (<shifter> = its vvvv:pppp USB IDs or part of its name).
#>
param(
    [string]$Config = (Join-Path $PSScriptRoot '..\out\build\win-amd64-release\fh2.toml'),
    [ValidateSet('on', 'off')][string]$Enabled,
    [string]$Device,
    [ValidateRange(0, 15)][int]$SteeringAxis,
    [ValidateSet('on', 'off')][string]$SteeringInvert,
    [string]$Throttle,
    [string]$Brake,
    [string]$Clutch,
    [string]$Buttons,
    [string]$FfbDevice,
    [ValidateRange(0, 100)][int]$Strength,
    [ValidateSet('on', 'off')][string]$Invert,
    [ValidateRange(0, 100)][int]$Rumble,
    [ValidateRange(1, 1000000)][int]$Scale,
    [ValidateSet('on', 'off')][string]$LogInputs,
    [ValidateSet('on', 'off')][string]$Trace
)
$ErrorActionPreference = 'Stop'

$keys = [ordered]@{
    Enabled = 'wheel_enabled'; Device = 'wheel_device'; SteeringAxis = 'wheel_steering_axis'
    SteeringInvert = 'wheel_steering_invert'; Throttle = 'wheel_throttle'; Brake = 'wheel_brake'
    Clutch = 'wheel_clutch'; Buttons = 'wheel_buttons'; FfbDevice = 'wheel_ffb_device'
    Strength = 'wheel_ffb_strength'; Invert = 'wheel_ffb_invert'; Rumble = 'wheel_ffb_rumble'
    Scale = 'wheel_ffb_magnitude_max'; LogInputs = 'wheel_log_inputs'; Trace = 'wheel_ffb_trace'
}
$switches = 'Enabled', 'SteeringInvert', 'Invert', 'LogInputs', 'Trace'

# Setting name -> TOML value, or $null to remove it (back to the default).
$changes = [ordered]@{}
foreach ($name in $keys.Keys) {
    if (-not $PSBoundParameters.ContainsKey($name)) { continue }
    $value = $PSBoundParameters[$name]
    $changes[$keys[$name]] =
        if ($name -in $switches) { if ($value -eq 'on') { 'true' } else { 'false' } }
        elseif ($value -is [int]) { "$value" }
        elseif ($value -eq '') { $null }
        else { '"' + $value.Replace('\', '\\').Replace('"', '\"') + '"' }
}

if ($changes.Count -gt 0) {
    if (Get-Process -Name fh2 -ErrorAction SilentlyContinue) {
        throw 'Close FH2 first: it writes its settings back over this file.'
    }
    $text = ''
    if (Test-Path $Config) {
        $text = [IO.File]::ReadAllText($Config)
        Copy-Item $Config "$Config.wheel-backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
    }
    $newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = [Collections.Generic.List[string]]::new()
    $table = -1
    foreach ($line in ($text -split "`r?`n")) {
        if ($table -lt 0 -and $line.TrimStart().StartsWith('[')) { $table = $lines.Count }
        # Only top-level keys are these settings: the SDK prefixes a table's keys with its name.
        if ($table -lt 0 -and $line -match '^\s*([A-Za-z0-9_]+)\s*=' -and $changes.Contains($Matches[1])) { continue }
        $lines.Add($line)
    }
    while ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -eq '') { $lines.RemoveAt($lines.Count - 1) }
    $at = if ($table -ge 0) { $table } else { $lines.Count }
    while ($at -gt 0 -and $lines[$at - 1] -eq '') { $at-- }
    foreach ($key in $changes.Keys) {
        if ($null -ne $changes[$key]) { $lines.Insert($at, "$key = $($changes[$key])"); $at++ }
    }
    New-Item -ItemType Directory -Force (Split-Path $Config) | Out-Null
    [IO.File]::WriteAllText($Config, ($lines -join $newline) + $newline, [Text.UTF8Encoding]::new($false))
    Write-Host "Updated $Config"
}

Write-Host "Wheel settings in $Config (missing ones use the defaults in RACING_WHEELS.md; wheel_enabled is off):"
if (Test-Path $Config) {
    foreach ($line in [IO.File]::ReadAllLines($Config)) {
        if ($line.TrimStart().StartsWith('[')) { break }
        if ($line -match '^\s*wheel_[a-z0-9_]+\s*=') { Write-Host "  $line" }
    }
}
