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
index*5648` (`index` from `r3+48`). The branch labels in the generated code give the
mapping (`loc_8255C478` takes `r28`, `loc_8255C470` takes `r27`):

| Byte | Class (string) | Table |
|---|---|---|
| 1 | `Wheel` (`0x820167F8`) | `WheelLayouts` |
| 2 | `Bristol` (`0x82016800`) | `BristolLayouts`: no sticks or shoulders |
| other | `Controller` (`0x82016808`) | `ControllerLayouts` |

(An earlier version of this table swapped 1 and 2.)

### Who writes the class (`sub_82D82EF0`)

The input manager is the record base: the global `0x835890D0`, passed by `sub_823FDB68`
(`lis r21,-31911`, then `lwz r3,-28464(r21)`) into `sub_82D843C0`. That function walks
four devices with stride 5648. It starts its pointer at `manager+22` (`addi r30,r3,22`),
so the device object is at `manager + 16 + i*5648`, and the device's `+6` is the
record's `+22`. `sub_82D82EF0(device)` polls one device:

1. Calls `XInputGetCapabilities(user = device+0, flags = 1)` into `r1+96` (XDK wrapper
   `sub_831D59E0`). If that succeeds, sets `device+6 = 0`.
2. If the device description query `sub_831F6428` succeeds, reads two properties with
   `sub_831F6740`. If they are **1118 (0x045E) and 690 (0x02B2)**, sets `device+6 = 2`
   (**Bristol**).
3. Otherwise (`loc_82D8303C`), if the capabilities **SubType** (`r1+97`) **== 2**, sets
   `device+6 = 1` (**Wheel**). No flags are checked on this path.
4. Anything else leaves 0, which is **Controller**.

So a device that reports XInput subtype 2 selects `WheelLayouts`, unless its vendor and
product read back as 045E:02B2. ShiftGlue `59bc11f5` reports subtype 2 for its raw wheel
(`docs/RACING_WHEELS.md`). Its `X_INPUT_CAPABILITIES` has no vendor or product fields,
`XamInputGetCapabilitiesEx` fills only the standard capabilities, `XamInputRawState` is a
stub, and the SDK source has no 045E:02B2 constant. Statically, then, the SDK's wheel
selects **WheelLayouts**. This is not yet observed at run time.

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

## Profile options: defaults and who reads them

**Defaults** come from `gamedb.slt`: `GameOptions` joined to `GameOptionCategoryMap`
(group 4 `ProfileOptions`; category 6 `WheelLayout`, 8 `WheelAdvancedOptions`), and
`DefValue` resolved through `GameOptionMap`/`GameOptionValues`. `--check` asserts all of these.

| Option | Default |
|---|---|
| `WheelLayout` | `DefaultLayout` = 0 (also Alt2 = 1, Alt3 = 2, Alt4 = 3; `WheelLayouts` has rows 0-2 only) |
| `InvertGearUpDownWheel` | Off = 0 |
| `InvertHandbrakeClutchWheel` | 0 |
| `InvertCameraLookBackWheel` | 0 |
| `RumbleSettingWheel` | On = 1 |
| `Use900DegreeSettings` | 1 |
| `ForceFeedbackScale` | 1 |

The wheel has no `RewindOnBack` or `ActivateOnBack` option in the database. Those profile
keys exist only in the registry below.

**Code, in the order it runs:**

- `sub_825698C8` registers each profile key with its settings page: `ControllerOptions/*`
  page 2, `WheelOptions/*` 4, `WheelAdvancedOptions/*` 5, `BristolOptions/*` 6.
- `sub_8256EA78` is the profile key list that loads and saves. It carries
  `WheelOptions/Layout`, `InvertGearUpDown`, `InvertHandbrakeClutch`,
  `InvertCameraLookBack`, `RewindOnBack` and `RumbleSetting`, plus
  `WheelAdvancedOptions/ForceFeedbackScale`.
- `sub_82576B78` applies a player's settings:
  - reads `<Class>Options/RumbleSetting`, `<Class>AdvancedOptions/ForceFeedbackScale`
    (float), `InvertGearUpDown` (into `r1+80`) and `InvertCameraLookBack` (into `r1+82`);
  - writes rumble and force feedback scale into the player's input record (`+16`,
    through `sub_82D82D50` and `sub_82D80358`);
  - then rebuilds the layout with `sub_8255C410`.
- `sub_8255C410` builds the layout:
  - builds `<Class>Options/Layout` from `Options/` (`0x82019CDC`) and `Layout`
    (`0x82019CC0`), reads it from the profile (`sub_825451D0`, then `sub_82649760`) and
    passes the integer **unchanged** as `LayoutId`, so the default wheel layout is row 0;
  - reads `<Class>Options/InvertHandbrakeClutch` (`0x82019CA8`) as a boolean, along
    with the ten advanced deadzones.
- `sub_82558410(player, row, column, invert)` turns each cell into an action:
  - columns come from the table at `0x82021D20` (21 entries of name and pad code);
  - action names come from the table at `0x82021DC8` (20 entries of name and ID: Gas
    0, Brake 1, Handbrake 3, ShiftUp 4, ShiftDown 5, Clutch 6, …, Rewind 20, Map 21,
    Activate 25, CarChallengeInfo 26);
  - when `invert` is set, `sub_82597158(&id, 3, 6)` swaps **Handbrake and Clutch**.

## Menus, Rewind and the per-player options (audit, 2026-10-23)

Static audit for the actions the Wheelkit route leaves out. The game data here is on the
disc, not in the fork, so it is the same for every fork commit built from this `default.xex`
(including `23118b7`):
- `gamedb.slt`, SHA-256 prefix `fd439c50d9ca2148`;
- `media/profileschema/ForzaProfile.sch`, SHA-256 prefix `6e8b506e3dc5c90b`.

**Per-player wheel options.** `ForzaProfile.sch` (lines 262-269) defines `WheelOptions` as
seven Int32 values. A new profile starts with `Layout` 0, `RumbleSetting` 1, and 0 for
`InvertGearUpDown`, `InvertHandbrakeClutch`, `InvertCameraLookBack`, `RewindOnBack` and
`ActivateOnBack`. `fh2_layouts.py --check` asserts these. A player's saved profile can change
every one of them:
- `Layout` picks the `WheelLayouts` row (`sub_8255C410`).
- `InvertHandbrakeClutch` swaps the Handbrake and Clutch actions (`sub_82597158`).
- `InvertGearUpDown`, `InvertCameraLookBack`, `RewindOnBack` and `ActivateOnBack` are read
  into a flags block by `sub_82576B78`, but where they take effect was not traced. By their
  names, the last two put Rewind or Activate on Back.

So a pad input's action is fixed only together with these options. The inputs that are the
same in every row (A, the shoulders, Back, d-pad down, the pedals and the clutch) still
assume the options keep their defaults.

**Where the profile lives.** The SDK keeps saves and the profile under `--user_data_root`
(the LaunchBox install's `user\`). That folder has only `cache\` so far, because the game
has not got past its title screen there. The saved profile's format is not established, so
nothing outside the game can read a player's `Layout` or options yet.

**Rewind.** It is Y in rows 0 and 1 and X in row 2. With the defaults (row 0, `RewindOnBack`
0) it is Y. That mapping can be proved only for an unchanged profile.

**Menus.** No menu input table exists in `gamedb.slt`. The UI definitions are in
`media/UI.zip`: scene files (`.bgf`/`.bsg`/`.fbf`) stored with a compression method a
standard zip reader does not support. The code around the `Accept`/`Cancel` strings showed no
pad-button masks. Confirm/back/start therefore stay unmapped. The SDK's default
`wheel_buttons` keeps d-pad navigation on hat 0.

**What would settle it.** Either decode the saved profile once the game has written one, and
read `WheelOptions` from it; or run the game once with `wheel_log_inputs` and note what A, B,
Start and the face buttons do in the menus and in a race.

## Not established

- **The class at run time.** The static chain above says the SDK's subtype-2 wheel is
  class 1 (Wheel). One run with the wheel enabled would confirm it. (The `+1212` buffer
  in `sub_82D81888` belongs to the vibration path, not to the class.)
- **Where gear and look-back inversion take effect.** `InvertGearUpDown` and
  `InvertCameraLookBack` are read into a local block in `sub_82576B78` and passed on;
  the code that applies them was not traced. A saved profile can also override every
  default above.
- **Steering and menus.** The tables leave out steering and menu navigation, and their
  read paths were not traced.
