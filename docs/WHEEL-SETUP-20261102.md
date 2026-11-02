# FH2 wheel settings helper - November 2, 2026

The PowerShell helper originated in `ec3e04d` (published sync branch tip
`e60e457`) and was ported onto app6c49/SDK499 with15 options. It now exposes24
explicit options against the qualified app734/SDKe223, adding raw steering and
pedal calibration with matching SDK names, types and numeric bounds.
This is a source and inert-file check;
it does not qualify an installed executable, wheel, pedals, shifter or forces.

The [combined native candidate](COMBINED-OFFLINE-20261102.md) includes the SDK
string/preservation/save-result fixes. Existing input/FFB suites also pass through
that built DLL; no game or device acceptance is implied. Calibration adds only
script parameters for existing SDK cvars, so no native rebuild is required.

## Use

PowerShell 7 or later is required. With no setting arguments, the helper only
shows existing root wheel keys. Specify the config beside the executable you
intend to configure; the default is the local `win-amd64-release` build directory.
Close FH2 before making edits. For example, from the source root:

```powershell
pwsh -NoProfile -File windows/tools/Set-Fh2Wheel.ps1 -Config 'C:\path\to\fh2.toml'
pwsh -NoProfile -File windows/tools/Set-Fh2Wheel.ps1 -Config 'C:\path\to\fh2.toml' -Enabled off
pwsh -NoProfile -File windows/tools/Test-Fh2Wheel.ps1
```

Only supplied options are changed. An empty string removes a string-valued
setting, restoring its SDK default. Numeric and boolean settings use explicit
values; they do not support removal through this interface. No device identity,
force direction or recommended strength is inferred.

| Option | SDK key | Type / accepted range |
| --- | --- | --- |
| Enabled | wheel_enabled | on/off -> boolean |
| Device | wheel_device | string |
| SteeringAxis | wheel_steering_axis | integer 0-15 |
| SteeringInvert | wheel_steering_invert | on/off -> boolean |
| SteeringScale | wheel_steering_scale | integer 10-1000 |
| SteeringDeadzone | wheel_steering_deadzone | integer 0-50 |
| PedalDeadzone | wheel_pedal_deadzone | integer 0-50 |
| Throttle | wheel_throttle | string |
| ThrottleDeadzoneBottom | wheel_throttle_deadzone_bottom | integer -1 to50; -1 inherits PedalDeadzone |
| ThrottleDeadzoneTop | wheel_throttle_deadzone_top | integer 0-50 |
| Brake | wheel_brake | string |
| BrakeDeadzoneBottom | wheel_brake_deadzone_bottom | integer -1 to50; -1 inherits PedalDeadzone |
| BrakeDeadzoneTop | wheel_brake_deadzone_top | integer 0-50 |
| Clutch | wheel_clutch | string |
| ClutchDeadzoneBottom | wheel_clutch_deadzone_bottom | integer -1 to50; -1 inherits PedalDeadzone |
| ClutchDeadzoneTop | wheel_clutch_deadzone_top | integer 0-50 |
| Buttons | wheel_buttons | string |
| FfbDevice | wheel_ffb_device | string |
| Strength | wheel_ffb_strength | integer 0-100 |
| Invert | wheel_ffb_invert | on/off -> boolean |
| Rumble | wheel_ffb_rumble | integer 0-100 |
| Scale | wheel_ffb_magnitude_max | integer 1-1000000 |
| LogInputs | wheel_log_inputs | on/off -> boolean |
| Trace | wheel_ffb_trace | on/off -> boolean |

Device selectors and bindings follow SDK `docs/RACING_WHEELS.md`: USB VID:PID,
name fragment or `path:` selector; pedals use `[device|][+|-]axisN`; H-pattern
bindings use `GEAR1` through `GEAR8` and `REVERSE` in the qualifiede223 SDK.
Syntax and actual device
availability are interpreted by the SDK, not validated by this text editor.
Other SDK wheel options remain available through the existing config/overlay;
the helper now exposes24 explicit options, including raw steering/pedal calibration.

## Raw-wheel calibration

These nine added calibration options use the SDK's `wheel_*` raw-wheel path
when wheel_enabled is true. They do not edit the separate `hid_wheel_*`
gamepad shaping path. Actual SDKe223 RefreshWheelStateLocked supplies steering
scale/deadzone to SteeringFromAxis, and each pedal's bottom/top values to
ReadWheelPedalLocked -> PedalFromAxis. A bottom value of-1 substitutes the shared
wheel_pedal_deadzone; a top value of0 means no full-travel dead zone.

Steering scale100 is the SDK start;200 reaches full lock with half the input
travel. Pedal bottom ignores noise at rest; top reaches fully pressed before
the end of travel. Example file edit while FH2 is closed:

```powershell
pwsh -File windows/tools/Set-Fh2Wheel.ps1 -Config <inert-or-selected-fh2.toml> -SteeringScale 150 -BrakeDeadzoneBottom 5 -BrakeDeadzoneTop 10
```

Use `-BrakeDeadzoneBottom -1` to restore shared inheritance explicitly. Numeric
zero and-1 are real values, not omission. The helper changes only supplied keys;
it does not choose measurements, change defaults, enable the wheel, or alter
force settings as a side effect. Existing game-running refusal and exact backup
behavior apply to calibration edits too. Physical calibration remains unverified.

## Preservation and audit findings

- Matching keys are updated in place, retaining inline comments. Other scalar
  root values, comments, table contents, Unicode, each existing line ending,
  trailing blank lines and UTF-8 BOM presence are retained. New keys go before
  the first table, using the existing newline style. Removal retains any comment.
- Edits refuse duplicate root keys, quoted/dotted root keys, root arrays/inline
  tables/multiline values, control characters and non-UTF-8 input. This is a
  deliberately limited editor for SDK scalar configs, not a general TOML parser;
  tables are copied verbatim and input files must otherwise be valid TOML.
- Each changed existing file is replaced from a sibling staging file using
  `File.Replace`, with an exact, uniquely named `.wheel-backup-<time>-<guid>`.
  Read-only and unchanged operations create no backup. Staging files are removed
  on failure. Restore the selected backup while the game is closed if needed.
- The original helper used second-resolution backup names and normalized the
  end of the file/BOM. Those preservation defects are corrected. Relative paths
  without a directory component also work. A running `fh2` process blocks edits.
- SDK `src/input/sdl/sdl_input_driver.cpp` defines23 options;
  `src/input/ffb_trace.cpp` defines `wheel_ffb_trace`. The numeric ranges above
  match their `.range(...)` declarations. SDK `src/ui/rex_app.cpp` loads config
  beside the executable and defaults logs to its `logs` folder; the old helper's
  fixed `windows/.local/logs` instruction was inaccurate and is corrected.
- SDK `src/core/cvar.cpp::MergeIntoTOML`, used by `SaveConfig`, still surrounds
  string values with quotes without escaping their contents at this exact pin.
  The helper correctly escapes backslashes and quotes, but a later SDK save may
  invalidate such strings. Prefer USB IDs or simple name fragments for now.
  This caveat applies to the earlier SDK499 binary pair.

A subsequent [source patch and offline round-trip fixture](../windows/patches/README.md)
fix this SDK serialization issue. It is included in the built SDKbddeb167 runtime
and passes 200 inert-file checks through that DLL. The caution above still
applies to the retained SDK499 candidate; a live game round trip remains unverified.

## Verification and remaining gates

`pwsh -NoProfile -File windows/tools/Test-Fh2Wheel.ps1` passes **69 checks** on
PowerShell 7.6.8 on Windows. Fixtures cover exact backup bytes, rapid successive writes,
comments/tables/newlines/BOM/Unicode, string escaping and removal, zero/false,
all24 option mappings, calibration limits/inheritance/selected-key preservation,
read-only/no-op behavior, rejected inputs, new relative
files, and refusal while a mocked FH2 process exists. Temporary files stay under
the worktree's ignored `.local` and are removed after testing. The retained
original42-check log is `.local/wheel-helper-check.log` in the isolated helper
worktree. Current69-check log is windows/.local/wheel-calibration/helper01.log
in the vuro triples worktree.
Current log SHA256 `2C91E3B0980C205698EA15C86D945B641B91102292B7ED76E6212361048C05D7`.
The source audit checks all9 new ranges and actual consumer keys against SDK
declarations/macros, including shared-deadzone inheritance. Private audit
windows/.local/wheel-calibration/source-audit.json SHA256
`C775EC56925280F2536A6DA42ED39C1B0EC2F5B02A1FF191A824234C391DA38F`.

This helper increment performs no native build, game/process launch, device
access, real profile/config write, installation or runtime test. The existing
native candidate and SDK gitlink remain unchanged. Runtime file use, physical
calibration/bindings/force direction and safe force/focus-loss behavior remain
separate gates.
