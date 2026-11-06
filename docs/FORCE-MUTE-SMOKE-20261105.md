# FH2 force/motion mute and private smoke - November 5, 2026 (vibe)

Kole539149. Offline work only: no game, device, rig, lease or owner write. Tool:
[`windows/tools/fh2_force_mute.py`](../windows/tools/fh2_force_mute.py) (stdlib Python, run with `python -I`).

## Target

The installed owner copy is napo's file-only deploy `fh2-041811100`: app `734fff4`, SDK `e223de8d`,
`fh2.exe` `A4E3BC4F...`. All five installed bin hashes are pinned in the tool (`BIN`). It has never
been launched; `logs/fh2.log` was last written Oct 25 and there is no `fh2.toml`. Nothing is rebuilt.

## Mechanism: two independent layers, both launch-time only

Every physical output in the exact source was inventoried (49 call sites): SDL rumble/haptic/trigger/LED
calls in `sdl_input_driver.cpp`, the SDK XInput driver, the guest socket `sendto` and Forza Data Out.

**A. SDK cvars on the command line.** The command line outranks the config file
(`Source::kConfig < kCommandLine`). The private `fh2.toml` repeats the same values in case a CLI11 parse
error drops the arguments.
- `--no-wheel_enabled`: `IsWheelPart` returns false. No SDL joystick, haptic device or wheel force object
  is ever opened; every wheel-force site needs `wheel_`, which only that path creates.
- Wheel forces also off or zero: `wheel_ffb_effects`, mode `off`, strength, centering, spring, damper,
  friction, inertia, engine/road rumble, and an empty `wheel_ffb_device`.
- `--pad_rumble_strength=0`: the single scaling point in `InputSystem::SetVibration` that every guest
  vibration passes through before any driver.
- `pad_ds_triggers=off` and no gear click. `pad_ds_trigger_strength` is not used because its range is
  25-100, so 0 would be rejected.
- `--input_backend=sdl`: the SDK XInput driver is not created.
- `--fh2_telemetry_port=0`: the sender loop `continue`s before `sendto`.
- Empty `pad_chord_game_menu` and `pad_chord_debug_overlay`, and `--no-mnk_mode`: the scripted pad
  cannot open the settings menu.

**B. SDL environment hints on the fh2 process only.** `SDL_JOYSTICK_DIRECTINPUT`, `RAWINPUT`, `WGI`,
`GAMEINPUT`, `HIDAPI` and `SDL_XINPUT_ENABLED` are all set to `0`, so SDL can enumerate no physical
controller.
- This layer is required: SDL 3.5's DirectInput open (`SDL_dinputjoystick.c`) sends `DISFFC_RESET` and
  sets `DIPROP_AUTOCENTER` **on** for any force-capable device, before any game force.
- Environment hints outrank the SDK's own `SDL_SetHint` (below `SDL_HINT_OVERRIDE`). The SDK never
  overrides these hints.
- The DirectInput hint also disables the DirectInput haptic backend.
- SDL has no built-in MOZA gamepad mapping, and the SDK's SDL virtual joystick has no users.

The only runtime writers that outrank the command line are the settings overlay and console. The run
never opens them, and layer B still holds if one were opened. Layer A still holds if layer B failed.

**Restore.** No device, Pit House or SimHub setting is touched, so there is nothing to restore. The proof
is a byte-exact before/after snapshot of the owner `bin/`, `logs/`, `user/`, `game/` (size, mtime and
attributes for files over 64 MiB), the absent owner `fh2.toml` and `Documents/fh2`, plus a closed-process
census.

**Physical preconditions software cannot set.** Pit House closed (the FH2-only rule), SimHub closed,
ButtKicker amplifier off and no wind devices. These come from the owner's Nov 2 clearance. The tool only
reads the process list and refuses if Pit House, SimHub or fh2 is running; it never starts or stops
them. **On 2026-11-05 SimHub was running** (`census.json`), so a run would refuse until the owner
closes it.

## Inert qualification (no game, device or build)

| Check | Result |
| --- | --- |
| `check --tree .worktrees/vuro-fh2-s4` | **PASS, 77 checks**: app HEAD `734fff4`/SDK `e223de8d` clean, 33 file pins, 33 anchors, output-site inventory, runtime-writer and hint-override scans, profile names/types/ranges/allowed values |
| Negative control in `check` | The pinned copy passes; removing the `wheel_enabled` guard is refused |
| `selftest` | **PASS, 20**: byte, size and added-file changes caught (including same size and mtime); CLI outranks a loud config; a missing rumble, wheel or DirectInput mute refused; write root inside owner refused; out-of-range, unknown and disallowed values refused; Pit House, SimHub and fh2 refused |
| `census` | Refuses on the SimHub processes |

Evidence (ignored): `windows/.local/force-mute-20261105/{check,selftest,census}.json`.
The source tree `vuro-fh2-s4` is a clean detached worktree. If the janitor removes it, the check needs a
tree that matches the same pins.

## Smoke plan (after a kole GO and lease)

Routes: R0 for logs and files, R1 for the game's scripted pad (`fh2_teste_botoes`) and in-process PNG
captures (`fh2_captura_cada_s=15`, max 40). No OS input, foreground input, desktop provider or stick
steering is used.

1. `Rig-Lease.ps1 -Enter -Name vibe -Purpose 'FH2 muted smoke <GO>'`.
2. `prepare --root E:/Source/_work/vibe-fh2-smoke-<GO>`. It refuses unless every installed bin hash
   matches, the census is clear and the root is new. It copies the five binaries privately and
   re-verifies them, writes the private `fh2.toml`, and records `plan.json` and the owner `baseline.json`.
3. `run --root ... --go <GO> --seconds 600` (hard cap 780 s). It:
   - re-verifies the tool hash, owner bytes and census, and requires the owner idle for at least 180 s;
   - records the foreground window, then launches 1280x720 windowed with the game data read from the
     owner `game/` and every write going to the private root;
   - aborts on any OS input, since the run sends none;
   - sends WM_CLOSE at the end, then force-kills its own process handle after 30 s;
   - records the foreground window again, analyzes the evidence and runs postflight verification.
4. `Rig-Lease.ps1 -Exit -Name vibe`, then report to kole.

Pass gates, reported separately:
- **M (mute):** no `SDL wheel` and no `OnControllerDeviceAdded` log line, and the postflight passes.
- **G1 (boot):** at least 60 s alive with no crash in the log.
- **G2 (frames):** at least 3 captures.
- **G3 (menu or prompt reached):** review of the captures.
- **R (restore):** zero owner changes and no refused process.

Driving, reverse, bindings on the physical wheel, forces, telemetry packets, F4 config save and owner
acceptance remain separate gates.
