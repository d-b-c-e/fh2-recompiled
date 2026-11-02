# FH2 Recompiled — Windows build (ShiftGlue SDK)

The November 2 combined candidate passes the native Windows build and offline
gear/reverse/telemetry checks. See the [current handoff](../docs/HANDOFF-WINDOWS-20261102.md)
for its exact app/SDK pair, private payload and remaining runtime gates.
The [wheel settings helper](../docs/WHEEL-SETUP-20261102.md) edits only supplied
options with backups; its file checks do not qualify physical inputs or forces.
The app7ce460f/SDKbddeb167 candidate includes the string-save fix and passes the
native build, generated checks and 200 save/load checks through its built DLL.
The earlier app6c49/SDK499 binary pair is retained separately.
Agent game/device testing remains held pending the physical output safety route.

Later source follow-up: [Data Out sender live configuration](../docs/TELEMETRY-SENDER-20261102.md)
passes real production loopback checks with the qualified SDK DLL. It is not yet
included in the app7ce460f native executable/private payload above.

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
| `thirdparty/shiftglue-sdk` (submodule, local candidate `bddeb167` based on Pinyon Shift 0.6.1's `59bc11f5`; see current handoff for source availability) | |

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
