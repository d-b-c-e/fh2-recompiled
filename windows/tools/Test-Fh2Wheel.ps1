#Requires -Version 7.0
<#
.SYNOPSIS
    Offline fixtures for Set-Fh2Wheel.ps1. No game, device or owner config access.
#>
$ErrorActionPreference = 'Stop'
$set = Join-Path $PSScriptRoot 'Set-Fh2Wheel.ps1'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\.local'))
$dir = Join-Path $root "fh2-wheel-test-$([guid]::NewGuid().ToString('N'))"
$config = Join-Path $dir 'fh2.toml'
$script:running = $false
$script:checks = 0
# Shadow only the script's process query; never create a fake game process.
function Get-Process {
    param($Name, $ErrorAction)
    if ($Name -cne 'fh2' -or $ErrorAction -ne 'SilentlyContinue') { throw 'Unexpected process query' }
    if ($running) { [pscustomobject]@{ ProcessName = 'fh2' } }
}
function Check([string]$label, [bool]$condition) {
    if (-not $condition) { throw "FAIL: $label" }
    $script:checks++
    Write-Host "ok   $label"
}
function Write-Fixture([string]$text, [bool]$bom = $false) {
    [IO.File]::WriteAllText($config, $text, [Text.UTF8Encoding]::new($bom))
}
function Read-Fixture { [IO.File]::ReadAllText($config) }
function Bytes { [Convert]::ToBase64String([IO.File]::ReadAllBytes($config)) }
function Backups { @(Get-ChildItem -LiteralPath $dir -Filter 'fh2.toml.wheel-backup-*') }
function Refuses([string]$label, [scriptblock]$action, [string]$message) {
    $before = Bytes
    $count = @(Backups).Count
    $errorText = ''
    try { & $action } catch { $errorText = $_.Exception.Message }
    Check "$label throws" ($errorText -like "*$message*")
    Check "$label preserves bytes and backups" (($before -ceq (Bytes)) -and $count -eq @(Backups).Count)
}
[IO.Directory]::CreateDirectory($dir) | Out-Null
try {
    $n = "`r`n"
    $original = "# owner comment${n}launcher_schema = 3${n}wheel_ffb_strength = 40 # tune${n}${n}[gpu]${n}wheel_ffb_strength = 7${n}${n}"
    Write-Fixture $original $true
    $originalBytes = Bytes
    & $set -Config $config -Enabled on -Strength 15 -Throttle '+axis2' -Device 'path:\\?\HID#a"b'
    $expected = "# owner comment${n}launcher_schema = 3${n}wheel_ffb_strength = 15 # tune${n}${n}" +
        "wheel_enabled = true${n}wheel_device = `"path:\\\\?\\HID#a\`"b`"${n}wheel_throttle = `"+axis2`"${n}" +
        "[gpu]${n}wheel_ffb_strength = 7${n}${n}"
    Check 'replace in place, escape string, preserve comments/tables/trailing CRLF' ((Read-Fixture) -ceq $expected)
    Check 'UTF-8 BOM retained' ([IO.File]::ReadAllBytes($config)[0] -eq 239)
    Check 'backup contains exact original bytes' (@(Backups).Count -eq 1 -and [Convert]::ToBase64String([IO.File]::ReadAllBytes((Backups)[0].FullName)) -ceq $originalBytes)
    $beforeSecond = Bytes
    & $set -Config $config -Throttle '' -SteeringAxis 0 -Invert off
    Check 'empty removes; zero and false retained' ((Read-Fixture) -cnotmatch 'wheel_throttle' -and (Read-Fixture).Contains('wheel_steering_axis = 0') -and (Read-Fixture).Contains('wheel_ffb_invert = false'))
    Check 'rapid edits retain distinct exact backups' (@(Backups).Count -eq 2 -and @((Backups) | Where-Object { [Convert]::ToBase64String([IO.File]::ReadAllBytes($_.FullName)) -ceq $beforeSecond }).Count -eq 1)
    $beforeShow = Bytes
    $count = @(Backups).Count
    $script:running = $true
    & $set -Config $config
    Check 'show-only while game running writes nothing' ($beforeShow -ceq (Bytes) -and $count -eq @(Backups).Count)
    Refuses 'running game' { & $set -Config $config -Strength 16 } 'Close FH2 first'
    $script:running = $false
    Write-Fixture "Wheel_enabled = false`nwheel_enabled = false # retain`nunknown = 'café'"
    & $set -Config $config -Enabled on
    Check 'case-sensitive keys, Unicode and no final newline preserved' ((Read-Fixture) -ceq "Wheel_enabled = false`nwheel_enabled = true # retain`nunknown = 'café'")
    $count = @(Backups).Count
    & $set -Config $config -Enabled on
    Check 'unchanged setting creates no backup' ($count -eq @(Backups).Count)
    foreach ($bad in @('"wheel_enabled" = false', "wheel_enabled = false`nwheel_enabled = true", 'notes = """text', "notes = [`n  1,`n  2`n]")) {
        Write-Fixture $bad
        Refuses 'ambiguous root syntax' { & $set -Config $config -Enabled on } 'No changes written'
    }
    Write-Fixture 'wheel_enabled = false'
    Refuses 'control characters' { & $set -Config $config -Device "name`nwheel_enabled = true" } 'Control characters'
    Refuses 'out of range strength' { & $set -Config $config -Strength 101 } 'greater than'
    [IO.File]::WriteAllBytes($config, [byte[]]@(255, 254, 97, 0))
    Refuses 'invalid UTF-8' { & $set -Config $config -Enabled on } 'Unable to translate'
    [IO.File]::Delete($config)
    Push-Location $dir
    try { & $set -Config 'fh2.toml' -Enabled off } finally { Pop-Location }
    Check 'new relative file without parent component' ((Read-Fixture) -ceq "wheel_enabled = false`n")
    Check 'new file is BOM-free UTF-8' ([IO.File]::ReadAllBytes($config)[0] -eq 119)
    Write-Fixture ''
    & $set -Config $config -Enabled off -Device '0eb7:0004' -SteeringAxis 15 -SteeringInvert on `
        -Throttle '+axis2' -Brake 'Pedals|-axis1' -Clutch 'axis3' -Buttons 'GEAR1=0079:0006|0,REVERSE=0079:0006|7' `
        -FfbDevice 'Wheel' -Strength 0 -Invert on -Rumble 100 -Scale 1000000 -LogInputs on -Trace off
    $expectedValues = [ordered]@{
        wheel_enabled='false'; wheel_device='"0eb7:0004"'; wheel_steering_axis='15'; wheel_steering_invert='true'
        wheel_throttle='"+axis2"'; wheel_brake='"Pedals|-axis1"'; wheel_clutch='"axis3"'
        wheel_buttons='"GEAR1=0079:0006|0,REVERSE=0079:0006|7"'; wheel_ffb_device='"Wheel"'
        wheel_ffb_strength='0'; wheel_ffb_invert='true'; wheel_ffb_rumble='100'; wheel_ffb_magnitude_max='1000000'
        wheel_log_inputs='true'; wheel_ffb_trace='false'
    }
    foreach ($key in $expectedValues.Keys) {
        Check "SDK option $key" ((Read-Fixture).Contains("$key = $($expectedValues[$key])`n"))
    }
    Check 'no staging files remain' (@(Get-ChildItem -LiteralPath $dir -Filter '*.wheel-tmp-*').Count -eq 0)
    Write-Host "PASS: $script:checks checks; inert TOML fixtures only."
} finally {
    $resolved = [IO.Path]::GetFullPath($dir)
    if (-not $resolved.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Scratch cleanup target escaped .local'
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
