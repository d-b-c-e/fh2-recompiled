# FH2 wheel steering with no force: route `wheel-wgi` - November 6, 2026 (vibe)

Kole548346 (source-first offline work while the rig is busy). This route lets the MOZA wheel steer the
installed FH2 build **with no force-feedback device opened at all**, using launch settings only. Nothing is
rebuilt. It extends [`windows/tools/fh2_force_mute.py`](../windows/tools/fh2_force_mute.py), the tool from
[FORCE-MUTE-SMOKE-20261105.md](FORCE-MUTE-SMOKE-20261105.md), with `prepare --route wheel-wgi`. The default
route `mute` is unchanged.

## Why this route

SDL 3.5's DirectInput open sends `DISFFC_RESET` and turns `DIPROP_AUTOCENTER` on for any force-capable
device, before any game force. That is why the mute route turns every SDL backend off and keeps the wheel
closed. To steer, the wheel must be read by some backend. Windows.Gaming.Input (WGI) is the only Windows
backend in this SDL that reads a non-XInput wheel without a force path:

- **Haptic devices.** SDL opens a haptic device only through `SDL_OpenHapticFromJoystick`, which requires
  `SDL_IsJoystickHaptic`. That is `SDL_SYS_JoystickIsHaptic || SDL_HIDAPI_JoystickIsHaptic`.
  - The Windows backend returns false unless the joystick belongs to the DirectInput/XInput driver.
  - The HIDAPI backend returns false unless it belongs to the HIDAPI driver.
  - So a WGI joystick never has a haptic device.
  - DirectInput haptic init is also skipped while `SDL_JOYSTICK_DIRECTINPUT=0`.
- **WGI's own output.** The WGI backend has no `ForceFeedback` reference. Its two `put_Vibration` calls
  run only when the device is an Xbox-class `Gamepad`. `SendEffect` returns unsupported.
- **SDK side.** `OpenWheelHapticLocked` logs `has no force feedback; rumble only.` and stops when the
  joystick is not haptic. The wheel rumble path returns before any call while `wheel_ffb_mode=off`.
- **Cvars.** Every force cvar keeps its mute value (strength, centering, spring, damper, friction,
  inertia, rumble 0; mode off; effects off; pad rumble 0; DualSense triggers off; Data Out port 0).

The route differs from `mute` in exactly three settings:
- `--wheel_enabled`;
- `--wheel_log_inputs`;
- `SDL_JOYSTICK_WGI=1`.

DirectInput, RawInput, GameInput, XInput, HIDAPI and all 27 HIDAPI driver hints stay `0`, and inherited
`SDL_*` variables are still removed. The MOZA is picked as the steering base by its vendor ID (`0x346E`),
or by SDL's wheel type. Pedals named "pedal" are not opened unless bound.

## Offline evidence

The evidence is in `windows/.local/wheel-wgi-20261106/` (git-ignored).

| Check | Result |
| --- | --- |
| `check --tree .worktrees/vuro-fh2-s4` | **PASS, 102 checks**. That is the 82 from the mute route, plus 3 new file pins (`SDL_haptic.c`, `SDL_hidapihaptic.c`, `wheel_mapping.cpp`) and 15 anchors for the haptic driver gates, WGI output paths, the SDK no-haptic path, the rumble-off return and the MOZA vendor ID. It also checks that the route differs from `mute` only by the three settings above. The negative control is still refused. |
| `selftest` | **PASS, 72**. That is the 57 from the mute route plus 15 new. The new checks cover the wheel-wgi profile and environment (WGI on, every other backend and every HIDAPI driver off, an inherited mapping removed). They refuse a force change, DirectInput on, a mismatched route and an unknown route. The `W_noforce` gate fails if a force device opened, if a force open was attempted, or if the no-force line is missing. |

## Assumptions (not provable from source)

- Windows enumerates the MOZA base as a WGI `RawGameController`, not as an Xbox-class `Gamepad`.
  - This matters because the pinned SDK's `StopWheelForcesLocked` always calls
    `SDL_RumbleJoystick(base, 0, 0, 0)`, whatever `wheel_ffb_mode` is. WGI drops that call only when the
    device is not a `Gamepad`. As a `Gamepad`, it would become one zero-intensity `put_Vibration`.
  - The runtime log cannot witness this. The logged SDL joystick type comes from SDL's vendor/product
    table first, and a missing `OnControllerDeviceAdded` line does not prove WGI's gamepad pointer is null.
- Reading the base through WGI sends no output report to it. That depends on Windows and the MOZA
  driver, not on SDL.

`W_noforce` therefore proves only the expected SDK no-haptic log pattern (pali549562 APPROVE, with this
limit). It is not a zero-output or physical-stillness proof. Whether the base physically stays still is
for the owner to observe; it is not measured.

## Live packet (needs a hash-bound kole GO, the same physical preconditions, and the census clear)

The same lifecycle as the mute smoke: private copy, job custody, byte-exact owner restore. Steps:

1. `pwsh E:/Source/dbce-project-mgmt/tools/Rig-Lease.ps1 -Enter -Name vibe -Purpose 'FH2 wheel-wgi GO<event>'`
2. `python -I windows/tools/fh2_force_mute.py prepare --route wheel-wgi --root E:/Source/_work/vibe-fh2-wgi-<event>`
3. `python -I windows/tools/fh2_force_mute.py run --root ... --go <event> --plan-sha256 <P> --baseline-sha256 <B> --seconds 600`
4. Release the lease only when `custody_clear` is true.

About 15 rig minutes. No OS keys; only the game's scripted pad (`fh2_teste_botoes`) and in-process captures.

Gates:
- **W_noforce:** the log shows `SDL wheel: opened` and `is the guest's racing wheel`. It also shows `has no
  force feedback; rumble only.`, and has no `force feedback on` or `could not open force feedback` line.
  There is no gamepad open.
- **G1/G2/G3/R:** as in the mute smoke.

It is recorded, not gated, whether the scripted pad still advances the menus while the wheel is the
guest's controller.

Still out of scope: pedal and button bindings (they need the owner to press them while
`wheel_log_inputs` prints the numbers), driving, forces and owner acceptance.
