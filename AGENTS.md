# Forza Horizon 2 — agent guide

Portfolio rules: `E:\Source\dbce-project-mgmt\HOW-WE-WORK.md` (read first; it replaces older process, lease, review and testing instructions). Current focus: `E:\Source\dbce-project-mgmt\NOW.md`. Feature status lives in the portfolio grid (`python E:\Source\dbce-project-mgmt\tools\portfolio_grid.py plan fh2`), not in this file. Grid id: `fh2`.

## Project

FH2 Recompiled: static recompilation of the Xbox 360 Forza Horizon 2 (ReXGlue SDK). Upstream targets Android and Linux (`app/`); the `windows/` folder builds a Windows x64 version on the ShiftGlue SDK (`thirdparty/shiftglue-sdk` submodule) with the FH1 Vulkan renderer. Remote `d-b-c-e/fh2-recompiled` (visibility unconfirmed, so do not push). GPL-3.0; `sdk/` is BSD-3-Clause. No game files in the repo.

## Build

- Windows: `windows/build.ps1` (PowerShell 7; `-SdkRoot` can use a reconstructed SDK tree, see `docs/SDK-SOURCE-20261102.md`). Output in `windows/out/build/win-amd64-release`. Needs the game extracted from your own disc (see README and `docs/`).
- Linux/Android: `build_pc.sh` / `build_android.sh` (Clang 20, CMake 3.25+, Ninja).

## Test

Unit and offline checks: unknown — check `windows/README.md` and `docs/`. Back up and restore the game's saves and config around a run (location: unknown — check `docs/CONFIG-PRESERVATION-20261102.md`).

## Install / run on the rig

`windows/run.ps1` (forces the Vulkan FH1 renderer, `--gpu_plugin=fh1`; Direct3D 12 shows a white window). Supported disc is the USA title `4D530AA4`; the rig's disc is media `15E4FA3D`, version 0.0.0.6 (`docs/disc-revision-check.md`).

## Shared code

Shared with the Linux/Android tree: `app/overrides*.toml`, `app/src/fh2_correcoes.cpp` and related files. Wheel setup helper: `docs/WHEEL-SETUP-20261102.md`. Change shared code in the toolkit and re-sync; never edit the vendored copy.

## Project-specific rules

- The `windows/thirdparty/shiftglue-sdk` submodule is dirty locally; do not commit it by accident.
- SDK patches live in `windows/patches/`; no SDK upstream push.
- Do not commit assets, extracted images, generated guest code or native binaries.

## Key docs

- `README.md`, `windows/README.md`
- `docs/WHEEL-SETUP-20261102.md`, `docs/TELEMETRY-SENDER-20261102.md`
- `docs/disc-revision-check.md`
- `TOOLKIT-ADOPTION.md`


<!-- BEGIN project-file-location -->
## Project files and temporary work

Keep project-related research, evidence, scripts, packages, and other working files inside the relevant project folder whenever practical. Keep disposable or machine-specific outputs git-ignored when they do not belong in version control; never ignore files that should be committed merely to hide them. When a project folder is unsuitable, use `E:\Source\temp\<project>` instead of creating scattered drive-root folders. Record the location of material needed by later work and update references when relocating it.

Clean up temporary files and disposable copies promptly once they are no longer useful. Preserve active work, user data, settings, saves, required evidence, backups, rollback artifacts, and worktrees until their retention or replacement is established. Follow existing project, rig, and data-loss safeguards; do not remove files merely because they are old or untracked.
<!-- END project-file-location -->
