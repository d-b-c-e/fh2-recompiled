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
| `thirdparty/shiftglue-sdk` (submodule, same revision as Pinyon Shift: `1e8968f7`) | |

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
