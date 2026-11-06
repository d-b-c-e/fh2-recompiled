# FH2 force/motion mute and private smoke - November 5, 2026 (vibe)

Kole539149. Offline work only: no game, device, rig, lease or owner write. Tool:
[`windows/tools/fh2_force_mute.py`](../windows/tools/fh2_force_mute.py) (stdlib Python, run with `python -I`).
Revision 2 addresses pali540713 (the first revision, `b2000f2`, was NEEDS CHANGES).

## Target

The installed owner copy is napo's file-only deploy `fh2-041811100`: app `734fff4`, SDK `e223de8d`,
`fh2.exe` `A4E3BC4F...`. All five installed bin hashes are pinned in the tool (`BIN`). It has never
been launched; `logs/fh2.log` was last written Oct 25 and there is no `fh2.toml`. Nothing is rebuilt.

## Mechanism: launch-time only

The static check pins the reviewed mechanisms in the exact source. It is not an exhaustive output proof
and not a physical measurement.

**B. Physical isolation, the SDL environment of the fh2 process.**
- The launch environment is the inherited one with **every `SDL_*` variable removed**. This drops, for
  example, an inherited `SDL_GAMECONTROLLERCONFIG` mapping or a per-driver enable.
- It then sets to `0`:
  - the DirectInput, RawInput, WGI, GameInput and XInput backends, and the generic HIDAPI hint;
  - all 27 HIDAPI driver-enable hints. An enabled per-driver hint overrides `SDL_JOYSTICK_HIDAPI=0`;
    for example, `SDL_hidapi_ps5.c` `HIDAPI_DriverPS5_IsEnabled` lets `SDL_JOYSTICK_HIDAPI_PS5=1` win.
- The check derives the hint set each `*_IsEnabled` reads from the exact SDL tree (`8bf3b72`, clean) and
  requires it to be covered. It also confirms the HIDAPI haptic (lg4ff) code reads no hint of its own.
- Why this layer is necessary: SDL 3.5's DirectInput open sends `DISFFC_RESET` and sets
  `DIPROP_AUTOCENTER` **on** for any force-capable device, before any game force.
- Environment hints outrank the SDK's `SDL_SetHint` calls, which never use `SDL_HINT_OVERRIDE` or touch
  these names. The DirectInput hint also gates the DirectInput haptic backend.

**A. Defence in depth, SDK cvars on the command line.** The private `fh2.toml` repeats them. A alone is
not sufficient.
- **Wheel:** `--no-wheel_enabled`, so `IsWheelPart` returns false and no wheel joystick or haptic device
  is opened. Every wheel force is also off or zero.
- **Rumble:** `--pad_rumble_strength=0` at the single vibration scaling point.
- **Other outputs:** DualSense triggers off, `input_backend=sdl` (no SDK XInput driver) and Data Out
  port 0.
- **Menus:** the controller chords to the settings and debug menus are empty, and `--no-mnk_mode`.
- **Not used:** `pad_ds_trigger_strength`, because its range is 25-100.

**Restore.** Nothing on the MOZA, Pit House or SimHub is touched. The proof covers the owner `bin/`,
`logs/`, `user/`, `game/` (all of it, including 7.4 GB of game data), the absent owner `fh2.toml` and
`Documents/fh2`. It uses a **full SHA-256** plus size, mtime and attributes for every file, taken before
and after, together with an exact PID, birth time and image closure census.

**Physical preconditions software cannot set.** Pit House closed (the FH2-only rule), SimHub closed
(Nov 2 clearance), ButtKicker amplifier off and no wind devices. The tool only reads the process list,
refuses if Pit House, SimHub or fh2 is running, and never starts or stops them. **On 2026-11-05 SimHub was
running**, so the run refuses until the owner closes it or kole and the owner change that condition.

## Lifecycle (pali findings 2-5)

**`prepare` refuses before any write unless all of these hold:**
- The root is a new direct child of `E:/Source/_work`, canonical, with no reparse point on its path and no
  overlap with the owner install.
- Every installed bin hash matches.
- The census is clear.

Then it takes the owner baseline, copies and re-verifies the binaries, and writes `plan.json`. It prints
both SHA-256 values.

**`run` revalidates before launch:**
- It requires `--plan-sha256` and `--baseline-sha256` and checks the schema, `BIN`, root and the
  regenerated profile.
- It checks the tool hash.
- It checks the **named lease**: `claude-lease-vibe.json` must be the current slot owner and its purpose
  must name `GO<event>`.
- It checks the owner bytes and the census.

**Owned process:**
- The tool records the PID, birth time and image through its own process handle and writes
  `out/process-receipt.json`.
- WM_CLOSE goes only to visible windows of that verified identity.
- If the game is still running after 30 s, it calls `TerminateProcess` on the same handle. It never
  reopens a PID.
- Every Win32 call has pointer-width `argtypes` and `restype` declared.

**Cleanup always runs** in a `finally` block. Even if observation fails, the tool closes the game, takes
a census of the private image and its child processes, verifies the postflight and writes `result.json`.

**Releasing the lease.** The tool never releases the lease. Run `Rig-Lease.ps1 -Exit -Name vibe` only if
`result.json` reports `custody_clear: true`. Otherwise keep the lease and report.

**Owner activity** is recorded as input events plus idle at start and end, and is not a gate
(kole538387). The owner or kole stops a run by creating `<root>/STOP`. Keys go to no window; only the
in-process scripted pad acts.

## Inert qualification (no game, device or build)

| Check | Result |
| --- | --- |
| `check --tree .worktrees/vuro-fh2-s4` | **PASS, 82 checks**: app `734fff4`/SDK `e223de8d`/SDL `8bf3b72` clean, 33 file pins, 33 anchors, output-site inventory, runtime-writer and hint-override scans, 29 HIDAPI `IsEnabled` functions all fenced, HIDAPI haptic reads no hint, profile names/types/ranges valid |
| Negative control in `check` | The pinned copy passes; removing the `wheel_enabled` guard is refused |
| `selftest` | **PASS, 30**: full-hash change detection including same size and mtime in `game/`; CLI over a loud config; missing mutes refused; inherited `SDL_JOYSTICK_HIDAPI_PS5=1`/`LG4FF=1`/DirectInput=1 and a MOZA mapping neutralised; a tampered profile fence refused; root outside `_work`, inside the owner, already existing or a reparse point refused; a lease for another GO refused; HWND signatures; own-handle identity |

Evidence (ignored): `windows/.local/force-mute-20261105/`. The source tree `vuro-fh2-s4` is a clean
detached worktree. If the janitor removes it, the check needs a tree that matches the same pins.

## Smoke plan (after a hash-bound kole GO)

Routes: R0 for logs and files, R1 for the game's scripted pad (`fh2_teste_botoes`, buttons only, no
steering) and in-process PNG captures (every 15 s, max 40). No OS input and no desktop provider are used.

1. `pwsh E:/Source/dbce-project-mgmt/tools/Rig-Lease.ps1 -Enter -Name vibe -Purpose 'FH2 muted smoke GO<event>'`
2. `python -I windows/tools/fh2_force_mute.py prepare --root E:/Source/_work/vibe-fh2-smoke-<event>`
   and record both printed hashes.
3. `python -I windows/tools/fh2_force_mute.py run --root E:/Source/_work/vibe-fh2-smoke-<event> --go <event> --plan-sha256 <P> --baseline-sha256 <B> --seconds 600`
   (hard cap 780 s). The game runs windowed at 1280x720, reading game data from the owner `game/` and
   writing only to the private root.
4. If `custody_clear` is true, run `Rig-Lease.ps1 -Exit -Name vibe`. Then report to kole with
   `result.json` and its SHA.

Gates, reported separately:
- **M_runtime:** the log exists with SDL input initialized and the telemetry sender started at port 0;
  captures exist, which only the command line requests, so they prove it was applied; and there is no
  `SDL wheel` or `OnControllerDeviceAdded` line. This is runtime negative evidence. Physical isolation
  rests on the static check, not on a measurement.
- **G1:** at least 60 s alive with no crash line.
- **G2:** at least 3 captures.
- **G3:** a menu or prompt is reached, judged from the captures.
- **R:** zero owner changes by full hash, and no refused process.

Driving, reverse, physical-wheel bindings, forces, telemetry packets, F4 config save and owner acceptance
remain separate gates.
