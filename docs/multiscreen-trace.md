# FH2 (Xbox 360) multiscreen: where the side views are made

Static trace only, 2026-10-23, for a triple-screen route on the Windows build. Image:
`default.xex` media `15E4FA3D` v0.0.0.6 (expanded image SHA-256
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`, base `0x82000000`;
`windows\tools\Test-DiscRevision.ps1 -ImageOut`). Code is from `windows/generated/default`
(ShiftGlue `1e8968f7` codegen; function boundaries do not depend on the SDK revision).
FH1's equivalent trace is in Pinyon Shift's fork, `docs/dbce/MULTISCREEN.md`. The
shapes match, but the addresses and offsets below are FH2's own.

## The game's mode

FH2 keeps Forza's linked-console multiscreen: one server console and client consoles,
one view each. All of the following are in the image:
- the launch options;
- the classes `CMultiscreen@Network`, `CMultiscreenServer@Network`,
  `CMultiscreenClient@Network`, `CMultiscreenApplication` and `CMultiscreenPlayer@Forza2`;
- a client HUD (`CHudMultiscreenClient@ForzaUI`);
- a setup scene (`835_C_MULTISCREEN_SETUP`);
- menu strings (`IDS_OptionMultiscreen`, `IDS_OptionDegreesBetweenScreens`,
  `IDS_OptionDegreesHidden`);
- a settings block (`multiscreen`, `degreesbetween`, `degreeshidden`, serialised by
  `sub_82E7D950` / `sub_82E7F6A0`).

## Launch options

The visitor is `sub_825554D0`, with matchers `sub_82D90C90` (flag), `sub_82D90A18` (int)
and `sub_82D90BF8` (float). It fills the launch-options singleton (getter
`sub_824893E8`):

| Field | Option | Type |
|---|---|---|
| +4963 | `MultiscreenServer` | flag |
| +4964 | `MultiscreenClient` | flag |
| +4968 | `MultiscreenChannel` | int |
| +4972 | `MultiscreenView` | int |
| +4976 | `MultiscreenDegreesBetweenScreens` | float |
| +4980 | `MultiscreenDegreesHidden` | float |
| +4984 | `MultiscreenSpan321` | flag |
| +4985 | `UnsecureSockets` | flag |

Game init `sub_82493A58` copies server, client, channel, view and both angles to a
block at `r1+336`. It checks `hydraulicsip` (+4894) and `hydraulicsport` (+4928) on the
way, then calls the multiscreen setup `sub_82E81C20(unsecure, &block)`. The setup works
on the multiscreen singleton (`sub_82E79D70` returns `0x833F2D34`) and its settings
(`sub_82E7F6A0`). Retail does not parse a command line, so these options need a guest
write after the visitor.

## Per-view camera (proven)

- The camera update `sub_829C11C8` runs these steps in order:
  1. Takes the target's matrix into `camera+240` (target vtable +24) and the FOV into
     `camera+304` (target vtable +28).
  2. Applies the adjustments in `sub_829BFEC8`.
  3. Calls **`sub_829BE688`**.
  4. Copies the matrix rows to `+208`/`+224`.
  5. Hands the camera to the view manager `*(0x83598C0C)`, vtable +48.
- `sub_829BE688` (vtable slot at `0x8239B280`) runs only if:
  - `sub_825C96E0` is true (global `0x8343B5DC`, multiscreen vtable +84, `camera+16`);
  - the target's vtable +96 is true;
  - `camera+168` is 0.
- When it runs, `sub_829BE688`:
  1. Yaws the orientation in `camera+240` by **multiscreen vtable +108**, in degrees,
     times `0x82000B54` = 0.017453292 (π/180), through `sub_82E411F8`.
  2. Rebuilds the matrix with `sub_829B8C18`.
  3. Sets `camera+304` from **multiscreen vtable +96**.
- So each console turns its own camera before the view is submitted. Projection and
  culling follow from that view. No frame splitting is involved.
- `TripleScreenAdditionalZOffset` (global `0x8344D4C4`, registered by `sub_829B8720`) is
  added to `camera+216` by `sub_829B8A70` under the same `sub_825C96E0` gate.
- Other functions gated by `sub_825C96E0` (not traced): `sub_829B7FB0` returns
  multiscreen vtable +104, or 0.3 when multiscreen is off. Also `sub_829B8370`,
  `sub_829B9D08`, `sub_829BE430` (3 checks) and `sub_829C6DD0`.

## Not established

- **One process, three views.** The game renders one view per console. Drawing three
  views per frame needs the view submission (or the frame) to run three times with its
  own visibility each time. Nothing in the game or the SDK provides that.
- **Three linked instances.** This is the game's own path. The link transport is not
  visible statically: FH2 imports the whole Winsock/XNet set, but `socket`, `bind`,
  `sendto`, `XNetConnect` and the rest have no direct call sites in the generated code,
  so the game reaches them through pointers. `sub_82E81C20`'s direct call graph (309
  functions, depth 7) reaches no network import. Whether server and client find each
  other on loopback under ShiftGlue's `xam_net.cpp` (real Winsock; secure XNet
  calls stubbed) needs a runtime trace.
- Not traced: what multiscreen vtable +96/+104/+108 compute from the settings, and which
  HUD a client draws.

## Next source steps

1. Resolve the multiscreen singleton's vtable (written by its constructor into
   `0x833F2D34`). Read slots +84, +96, +104 and +108 to get the yaw and FOV formulas.
2. Write the launch options after `sub_825554D0` (`MultiscreenView`, role, channel and
   `UnsecureSockets` from default-off cvars). This only makes sense with a run
   planned: the first check is a single client with `View` = 1 and no server.
