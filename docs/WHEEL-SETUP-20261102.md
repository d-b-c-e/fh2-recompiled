# FH2 wheel settings helper - November 2, 2026

Main integration note: this helper is present in main for configuring the
separately qualified SDK499e0579/bddeb167 candidates. Main's older SDK1e8968f
has no `wheel_*` consumer; no SDK pin or installed executable changes with this
helper-only integration. Pass the matching executable's config path explicitly.

The PowerShell helper is ported from `ec3e04d` (published sync branch tip
`e60e457`) onto app `6c49f9cdf1bebc188740fe47bf95ee4aabc735de`, whose SDK gitlink
is `499e0579b2e8a52f68b99748198816be7217ecee`. All 15 existing options match that
SDK's names, types and numeric bounds. This is a source and inert-file check;
it does not qualify an installed executable, wheel, pedals, shifter or forces.

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
| Throttle | wheel_throttle | string |
| Brake | wheel_brake | string |
| Clutch | wheel_clutch | string |
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
bindings use `GEAR1` through `GEAR7` and `REVERSE`. Syntax and actual device
availability are interpreted by the SDK, not validated by this text editor.
Other SDK wheel options remain available through the existing config/overlay;
this port deliberately retains the earlier helper's option surface.

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
- SDK `src/input/sdl/sdl_input_driver.cpp` defines the first 14 options;
  `src/input/ffb_trace.cpp` defines `wheel_ffb_trace`. The numeric ranges above
  match their `.range(...)` declarations. SDK `src/ui/rex_app.cpp` loads config
  beside the executable and defaults logs to its `logs` folder; the old helper's
  fixed `windows/.local/logs` instruction was inaccurate and is corrected.
- SDK `src/core/cvar.cpp::MergeIntoTOML`, used by `SaveConfig`, still surrounds
  string values with quotes without escaping their contents at this exact pin.
  The helper correctly escapes backslashes and quotes, but a later SDK save may
  invalidate such strings. Prefer USB IDs or simple name fragments for now.
  No SDK patch or runtime round-trip claim is included here.

## Verification and remaining gates

`pwsh -NoProfile -File windows/tools/Test-Fh2Wheel.ps1` passes **42 checks** on
PowerShell 7.6.8 on Windows. Fixtures cover exact backup bytes, rapid successive writes,
comments/tables/newlines/BOM/Unicode, string escaping and removal, zero/false,
all 15 option mappings, read-only/no-op behavior, rejected inputs, new relative
files, and refusal while a mocked FH2 process exists. Temporary files stay under
the worktree's ignored `.local` and are removed after testing. The retained run
log is `.local/wheel-helper-check.log` in the isolated helper worktree.

No native build, game/process launch, device access, real profile/config write,
installation or runtime test was performed. Vuro owns the separate native build
and subsequent integration; this helper branch does not move app main or alter
the SDK gitlink. README linkage is deferred to that integration. Runtime config
loading/saving, physical bindings/force direction and safe force/focus-loss
behavior remain separate gates.
