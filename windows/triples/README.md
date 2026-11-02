# FH2 offline triple planner

This is the first renderer-independent projection/config consumer for the
[single-window scene design](../../docs/TRIPLE-SCENE-DESIGN-20261102.md).
It is not linked into fh2.exe and cannot enable triples, create a window,
initialize a game/device, or write game settings. No runtime CLR dependency has
been introduced into the native app. Native scene/culling hooks, matrix/clip
conversion, resource partitioning, compositor and window placement remain open.

## Canonical geometry

The consumer calls `Dbce.TripleScreen.RigDefinition`, `RigPlanner.Plan`,
`ProjectionCalculator.Calculate` and `CurvedPanelWarp.WithSourceOn` directly.
`vendor/Dbce.TripleScreen.Core` is the complete unmodified14-file component from
toolkit `149cc66ff34feb773afc66c615f3bcddb2dac406`, with source hashes in
PROVENANCE.json. Every vendored Git blob was compared to that pin; LF attributes
keep source reproducible on Windows. No mandatory private Git checkout/package
or new NuGet test dependency is required. Toolkit worktree was not modified.

Physical coordinates are right-handed (+X right, +Y up, panels toward -Z), in
millimeters. Eye distance is to the center panel's edge plane, without sagitta
subtraction. Matrix rows apply as M*v with clip depth[-1,1]; near/far are mm here.
An explicit offline guest-camera matrix adapter is now checked against the pure
stock builder; see [projection oracle](../../docs/PROJECTION-ORACLE-20261102.md).
The existing [native asymmetric API](../../docs/OFFAXIS-API-20261102.md) has a
different depth contract and unresolved flag behavior; it is not substituted.
Runtime unit/mode selection, culling and GPU integration are not admitted. Game vertical FOV
must eventually be supplied by the resolved native camera path, not inferred
from a prior-frame WVP heuristic.

`ProjectionPlan.Build` returns one window rectangle and each canonical slice's
pixel rectangle, off-axis projection and warp. Curved or N-display rigs use the
same planner. Physical slice identities/warp are retained when translating the
source onto a virtual Game-FOV rig. The real eye still computes the warp; using
the virtual eye for it would bow straight edges. Output plans are transient,
not serialized back over raw physical measurements.

## Configuration and camera policy

`TripleConfig.Parse` accepts a bounded UTF-8 JSON document, optionally with BOM.
It rejects unknown versions/properties, duplicate properties/IDs, wrong types,
invalid geometry/nonfinite values, pixel overflow and unsupported enum values.
The prototype bounds input to64KiB and1-16 displays; panels share pixel height.
`fixtures/three-flat.json` is synthetic test data, not an owner-profile export or
a game config that FH2 currently loads. `enabled` defaults false when absent.

Starting sets: cockpit Realistic, bonnet Game, bumper Realistic, chase Game.
`CameraState` keeps each camera's selection and each set's FOV offset independent
in memory. Reset affects only the selected camera/set. There is no native F7,
stage-start detection or persistence yet. Realistic uses measured seat geometry;
Game starts from the supplied game vertical FOV. Wider than seat-true stretches
the side screens even with continuous seams. Invalid resulting FOV is refused,
not silently clamped. Disabled/one-display configs return pass-through with no
replacement views, preserving single-screen game framing.

No writer was added: settings-byte preservation and atomic per-key persistence
remain a later native integration task. This JSON is an offline prototype input,
not an extra player setup surface. The existing wheel TOML helper is unchanged.

## Focused check

With installed .NET8 SDK/runtime or later, from the source root:

```powershell
dotnet run --project windows/triples/tests/Fh2.Triples.Tests.csproj -c Release -p:UseSharedCompilation=false -p:BuildInParallel=false
```

The default console fixture passes **828 checks** against the production consumer and pinned toolkit
(retaining the original534). The optional stock-oracle route passes5,726.
It checks
actual projected corners/depth, seam rays, asymmetric folds, flat/curved source
warps with a wrong-eye negative control, slice coverage, unequal pixel widths,
five displays, edge-plane distance, per-camera starts/toggles/offsets, reset,
pass-through and strict malformed config. It performs no game/device/window or
owner-file writes. Build outputs stay under ignored bin/obj and retained logs
under windows/.local/triples.

Context7 did not resolve the framework JSON library; unknown-member behavior
was checked against [Microsoft's .NET8 documentation](https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/missing-members)
and the installed framework, then exercised in the fixture. A passing math/config
fixture is not three distinct rendered views or physical seam acceptance.
