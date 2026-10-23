# FH2 Recompiled — Windows build (ShiftGlue SDK)

Upstream FH2 Recompiled targets Android and Linux. This folder builds the same game for
**Windows x64** on the [ShiftGlue SDK](https://github.com/arcanite24/shiftglue-sdk), the
ReXGlue 0.10.0 fork behind [Pinyon Shift](https://github.com/arcanite24/pinyon-shift)
(Forza Horizon 1, the same engine), with its Vulkan FH1 renderer (`--gpu_plugin=fh1`).

Why ShiftGlue: upstream's own evaluation (branch `comparacao/shiftglue`,
`docs/comparacao_shiftglue.md`) built FH2 unchanged on it. On PC it rendered correctly the
first time, and cars no longer pass through other cars and walls, a known bug of the
upstream SDK. It was rejected for the phone build only for GPU cost on an S23, which does
not apply to a desktop GPU.

## What is shared with the Linux/Android tree

| Here | Shared from `../app` |
|---|---|
| `fh2_manifest.toml` (same inputs, `windows/generated` output) | `overrides*.toml` (function boundaries) |
| `src/main.cpp`, `fh2_toque.cpp`, `fh2_medidor.cpp` (from the prototype) | `src/fh2_correcoes.cpp`, `fh2_teste_entrada.cpp`, `fh2_captura.cpp` |
| `rexglue_proto.cmake`, `tools/tabela_registro.py` (from the prototype) | |
| `thirdparty/shiftglue-sdk` (submodule, same revision as Pinyon Shift 0.6.1: `59bc11f5`, with its wheel force feedback, `docs/RACING_WHEELS.md`) | |

## Supported disc

Upstream documents the USA disc, title `4D530AA4`, media `7C7779D1`, version 0.0.0.12.
The disc on this rig is media `15E4FA3D`, **version 0.0.0.6**, same title. Its
`default.xex` image is the same size (24,117,248 bytes) and entry point (`0x82BF2CD0`),
and every instruction-level check against the addresses annotated in `app/overrides.toml`
matches, relative branches included (2026-10-15, see `docs/disc-revision-check.md`).

## Build and run

Needs Visual Studio 2022 Build Tools (C++), Python 3, PowerShell 7 and about 30 GB free.
The first build runs codegen (about 8 minutes on upstream's PC) and compiles ~720
generated files: expect an hour or more at `-Jobs 8`. It is CPU-heavy; on the rig, take
the shared lease first.

```powershell
pwsh -File windows\build.ps1 -IsoPath "D:\path\to\FH2.iso"
pwsh -File windows\run.ps1
```

## Racing wheel

The SDK's raw wheel path (off by default) presents a wheel base, pedals, buttons and an
H-shifter, each from its own USB device if need be, as an Xbox 360 force feedback wheel,
and plays FH2's own wheel effects on the base. FH2 looks up the kernel's wheel force
feedback calls by ordinal at run time, as FH1 does. Settings and defaults:
`thirdparty\shiftglue-sdk\docs\RACING_WHEELS.md`. They live in `fh2.toml` beside `fh2.exe`
and can be changed in game (F4, Input) or, with the game closed, by script:

```powershell
pwsh -File windows\tools\Set-Fh2Wheel.ps1 -Enabled on -LogInputs on   # then read the wheel lines in .local\logs\fh2.log
pwsh -File windows\tools\Set-Fh2Wheel.ps1 -Throttle axis2 -Brake axis3 -Strength 15
pwsh -File windows\tools\Set-Fh2Wheel.ps1                              # show the current settings
```

Not yet tried on a wheel. Start with a low strength on a direct-drive base; the force
direction (`-Invert`) and FH2's effect scale (`-Scale`; FH1 needs 127) are still to be
checked with `-Trace on`. `pwsh -File windows\tools\Test-Fh2Wheel.ps1` checks the script
offline.
