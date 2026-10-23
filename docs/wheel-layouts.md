# FH2 (Xbox 360) pad action layouts

Static, 2026-10-23. Disc media `15E4FA3D` v0.0.0.6. Addresses are in the expanded image
(SHA-256 `3708A857…2244`, base `0x82000000`); code is from `windows/generated/default`.
`windows\tools\fh2_layouts.py <game_root>\media\db\gamedb.slt` prints every layout, and
`--check` asserts the wheel rows below.

## Where the layouts come from

FH2 does not hard-code its controls. `sub_8255C410` builds the query
`SELECT * FROM %s%s WHERE LayoutId=%d` (`0x82019B7C`) from a class name and `Layouts`
(`0x82019BA4`), and reads the row from `media/db/gamedb.slt`. That file is plain SQLite 3,
4,061,184 bytes, SHA-256 prefix `fd439c50d9ca2148`.

The class comes from byte `+22` of the player's input record, `*(0x835890D0) +
index*5648` (`index` from `r3+48`):

| Byte | Class (string) | Table |
|---|---|---|
| 1 | `Bristol` (`0x82016800`) | `BristolLayouts`: no sticks or shoulders |
| 2 | `Wheel` (`0x820167F8`) | `WheelLayouts` |
| other | `Controller` (`0x82016808`) | `ControllerLayouts` |

## WheelLayouts (3 rows)

All three rows share these:

| Pad input | Action |
|---|---|
| Right trigger / left trigger | Gas / Brake |
| Right shoulder / left shoulder | ShiftUp / ShiftDown |
| Left stick up and down | Handbrake (analog) |
| Right stick up and down | Clutch (analog) |
| A | Handbrake |
| D-pad up / down / left / right | CarChallengeInfo / LookStraightBack / RadioLeft / RadioRight |
| Back | SwitchCamera |

Only the face buttons differ:

| Layout | B | X | Y |
|---|---|---|---|
| 0 | Clutch | Activate | Rewind |
| 1 | Activate | Clutch | Rewind |
| 2 | Clutch | Rewind | Activate |

Not in any row: steering, Start, the right stick's horizontal axis (no H-shifter column)
and menu navigation.

`ControllerLayouts` (5 rows) adds the right-stick look (`LookForward`, `LookBack`,
`LookLeft`, `LookRight`, plus `LookStraightBack` on the click) and `Map` on Back.
`BristolLayouts` (3 rows) puts the shifts on face buttons.

## How it lines up with the SDK's wheel path

ShiftGlue's raw wheel path (`thirdparty/shiftglue-sdk/docs/RACING_WHEELS.md`) puts:
- steering on the left stick's X axis;
- throttle and brake on the right and left triggers;
- the clutch pedal on the right stick's vertical axis.

Pedals and the clutch therefore match every wheel row. A handbrake **lever** has no
analog route in the SDK (the left stick's vertical axis is not offered). It can still be
bound as button A, which is Handbrake in all three rows: `wheel_buttons` `A=<lever>|+axisN`.

## Not established

- **Which class the SDK's wheel gets.** The SDK presents XInput subtype 2 with the force
  feedback flag, but what writes byte `+22` from the capabilities was not found.
  `sub_82D81888` stores the capabilities at `+1212` of the controller object; a direct
  writer of `+22` next to the record base, or in the input and profile modules, did not
  turn up. So it is not proven that the SDK's wheel selects `WheelLayouts`.
- **Which row applies, and the per-device options.** The row comes from the profile
  (`WheelOptions/Layout`, `BristolOptions/Layout`). The options `InvertHandbrakeClutch`,
  `InvertGearUpDown`, `ActivateOnBack`, `RewindOnBack` and `InvertCameraLookBack` can
  change the result. They are read in `sub_825698C8` and `sub_8256EA78` (not traced), and
  their defaults are not known.
- **Steering and menus.** The tables leave out steering and menu navigation, and their
  read paths were not traced.
