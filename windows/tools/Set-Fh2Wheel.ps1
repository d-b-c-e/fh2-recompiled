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
    An empty string ('') removes a string setting, so it goes back to its default.
    Editing supports the SDK's scalar, unquoted top-level keys. Ambiguous root
    syntax is refused without writing. UTF-8 BOM, comments and line endings are kept.
    To find axis and button numbers: -Enabled on -LogInputs on, start the game, move each
    control, and read the wheel lines under logs beside fh2.exe (unless log_file is set).

.EXAMPLE
    pwsh -File windows\tools\Set-Fh2Wheel.ps1
    Shows the current wheel settings.
.EXAMPLE
    pwsh -File windows\tools\Set-Fh2Wheel.ps1 -Enabled on -Throttle axis2 -Brake axis3 -Strength 15
.EXAMPLE
    pwsh -File windows\tools\Set-Fh2Wheel.ps1 -Buttons 'GEAR1=<shifter>|0,GEAR2=<shifter>|1,REVERSE=<shifter>|7'
    An H-shifter on its own device (<shifter> = its vvvv:pppp USB IDs or part of its name).
.EXAMPLE
    pwsh -File windows\tools\Set-Fh2Wheel.ps1 -SteeringScale 150 -BrakeDeadzoneBottom 5 -BrakeDeadzoneTop 10
    Sets raw-wheel sensitivity and brake travel; other settings are preserved.
    A per-pedal bottom value of -1 inherits PedalDeadzone.
#>
param(
    [string]$Config = (Join-Path $PSScriptRoot '..\out\build\win-amd64-release\fh2.toml'),
    [ValidateSet('on', 'off')][string]$Enabled,
    [string]$Device,
    [ValidateRange(0, 15)][int]$SteeringAxis,
    [ValidateSet('on', 'off')][string]$SteeringInvert,
    [ValidateRange(10, 1000)][int]$SteeringScale,
    [ValidateRange(0, 50)][int]$SteeringDeadzone,
    [ValidateRange(0, 50)][int]$PedalDeadzone,
    [string]$Throttle,
    [ValidateRange(-1, 50)][int]$ThrottleDeadzoneBottom,
    [ValidateRange(0, 50)][int]$ThrottleDeadzoneTop,
    [string]$Brake,
    [ValidateRange(-1, 50)][int]$BrakeDeadzoneBottom,
    [ValidateRange(0, 50)][int]$BrakeDeadzoneTop,
    [string]$Clutch,
    [ValidateRange(-1, 50)][int]$ClutchDeadzoneBottom,
    [ValidateRange(0, 50)][int]$ClutchDeadzoneTop,
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
    SteeringInvert = 'wheel_steering_invert'; SteeringScale = 'wheel_steering_scale'
    SteeringDeadzone = 'wheel_steering_deadzone'; PedalDeadzone = 'wheel_pedal_deadzone'
    Throttle = 'wheel_throttle'; ThrottleDeadzoneBottom = 'wheel_throttle_deadzone_bottom'; ThrottleDeadzoneTop = 'wheel_throttle_deadzone_top'
    Brake = 'wheel_brake'; BrakeDeadzoneBottom = 'wheel_brake_deadzone_bottom'; BrakeDeadzoneTop = 'wheel_brake_deadzone_top'
    Clutch = 'wheel_clutch'; ClutchDeadzoneBottom = 'wheel_clutch_deadzone_bottom'; ClutchDeadzoneTop = 'wheel_clutch_deadzone_top'
    Buttons = 'wheel_buttons'; FfbDevice = 'wheel_ffb_device'
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
        else {
            if ($value -match '[\x00-\x1F\x7F]') { throw "Control characters are not allowed in $name." }
            '"' + $value.Replace('\', '\\').Replace('"', '\"') + '"'
        }
}

if ($changes.Count -gt 0) {
    if (Get-Process -Name fh2 -ErrorAction SilentlyContinue) {
        throw 'Close FH2 first: it writes its settings back over this file.'
    }
    $Config = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Config)
    $exists = [IO.File]::Exists($Config)
    $bytes = [byte[]]::new(0)
    if ($exists) { $bytes = [IO.File]::ReadAllBytes($Config) }
    $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191
    $encoding = [Text.UTF8Encoding]::new($bom, $true)
    $offset = if ($bom) { 3 } else { 0 }
    $text = $encoding.GetString($bytes, $offset, $bytes.Length - $offset)
    if ($text -match '[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]|\r(?!\n)') {
        throw 'Expected a UTF-8 TOML file with LF or CRLF line endings.'
    }
    $newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = [Collections.Generic.List[string]]::new()
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $table = $false
    $insertAt = -1
    # shortcut: scalar root keys only; use a TOML parser if broader editing is needed.
    $scalar = '^(?<prefix>\s*(?<key>[A-Za-z0-9_-]+)\s*=\s*)(?<value>"(?:[^"\\]|\\.)*"|''[^'']*''|[^\s#"''\[\]{}]+)(?<tail>\s*(?:#.*)?)$'
    foreach ($part in [regex]::Matches($text, '(?m)^(?<body>[^\r\n]*)(?<end>\r?\n|$)')) {
        if ($part.Length -eq 0) { continue }
        $line = $part.Groups['body'].Value
        $ending = $part.Groups['end'].Value
        if (-not $table -and $line.TrimStart().StartsWith('[')) {
            $table = $true
            $insertAt = $lines.Count
        }
        if (-not $table -and $line -notmatch '^\s*(#.*)?$') {
            if ($line -notmatch $scalar) { throw 'Unsupported root TOML syntax; no changes written.' }
            $key = $Matches['key']
            if (-not $seen.Add($key)) { throw "Duplicate root key: $key. No changes written." }
            if ($key -cin $changes.Keys) {
                $line = if ($null -ne $changes[$key]) { $Matches['prefix'] + $changes[$key] + $Matches['tail'] }
                    else { $Matches['tail'].TrimStart() }
                $changes.Remove($key)
            }
        }
        $lines.Add($line + $ending)
    }
    if ($insertAt -lt 0) { $insertAt = $lines.Count }
    foreach ($key in $changes.Keys) {
        if ($null -eq $changes[$key]) { continue }
        if ($insertAt -gt 0 -and -not $lines[$insertAt - 1].EndsWith("`n")) {
            $lines[$insertAt - 1] += $newline
        }
        $lines.Insert($insertAt, "$key = $($changes[$key])$newline")
        $insertAt++
    }
    $updated = $lines -join ''
    if ($updated -ceq $text) { Write-Host 'No changes needed.'; return }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Config)) | Out-Null
    $suffix = [guid]::NewGuid().ToString('N')
    $temporary = "$Config.wheel-tmp-$suffix"
    try {
        [IO.File]::WriteAllText($temporary, $updated, $encoding)
        if ($exists) {
            $backup = "$Config.wheel-backup-$(Get-Date -Format yyyyMMdd-HHmmss)-$suffix"
            [IO.File]::Replace($temporary, $Config, $backup)
            Write-Host "Backup: $backup"
        } else { [IO.File]::Move($temporary, $Config) }
    } finally {
        if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
    }
    Write-Host "Updated $Config"
}

Write-Host "Wheel settings in $Config (missing ones use SDK defaults; wheel_enabled defaults to false):"
if (Test-Path $Config) {
    foreach ($line in [IO.File]::ReadAllLines($Config)) {
        if ($line.TrimStart().StartsWith('[')) { break }
        if ($line -match '^\s*wheel_[a-z0-9_]+\s*=') { Write-Host "  $line" }
    }
}
