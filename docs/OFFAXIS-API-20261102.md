# Existing native asymmetric camera API: different depth contract

The base camera already has an asymmetric perspective builder. Its tested
unflipped branch uses **near depth0 /far depth1**, whereas the earlier symmetric
builder uses **near1 /far0**. These APIs cannot be substituted blindly. This
finds a useful native integration candidate; it does not connect triples or
establish the live camera's shader/depth/culling contract.

## Verified interface and math

Actual CPresentationCamera vtable8224FBDC contains:

| Byte slot | Function | Observed behavior |
| --- | --- | --- |
|44 |82F46988 | Symmetric FOV projection, previously checked reversed depth |
|48 |82F43678 | Asymmetric perspective from stored extents;203 instructions, leaf |
|76 |823F2FF0 | Writes f1/f2/f3/f4 to240/244/248/252, dirty480=1;7 instructions, leaf |

For byte272=0 and valid conventional extents, the four setter values behave as
left,top,right,bottom at the near plane. With n=field208,f=field212 and q=+1
for mode r4=0 or q=-1 for mode1, the stored row-vector matrix at+80 is:

```text
[ 2n/(r-l)       0            0           0 ]
[    0       2n/(t-b)         0           0 ]
[ -q(r+l)/(r-l) -q(t+b)/(t-b) q*f/(f-n)   q ]
[    0           0          -n*f/(f-n)    0 ]
```

The actual setter and builder execute sequentially on synthetic camera memory.
The builder stores mode at+12, projection-kind value1 at+8 and dirty480=1.
The previous symmetric builder stores kind0; constructor starts at3. No enum
meaning beyond these observed paths is invented. Pose64bytes at+16 and SP
remain unchanged; this is not full camera/derived-state restoration proof.

The deferred camera has a corresponding slot48 wrapper82F44D48. It copies
mode into an8-byte queued payload and dispatches callback82F44D30, which reads
that mode and calls the receiver's virtual48. Symmetric wrapper82F44CC0 uses
callback82F44CA8/virtual44. These are static interface paths, not proof that
context+40 currently owns this class or that either call occurs on the main view.

## Numerical evidence

Use the qualified734/e223 private generated source and SDK headers, in a VS
x64 developer shell:

```powershell
python -I windows/tools/fh2_offaxis_oracle.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-project-output>
```

The script verifies image SHA256
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`, all3
base vtable words and the two unique leaf bodies. Generated code stays private;
actual SDK PPC context/intrinsics execute, without a mocked guest callee or SDK
DLL/runtime startup. Image pages are nonexecutable data. Fixture owns the FP
policy global and exercises false/true.

- **2,400 checks PASS** for60 byte272=0 cases:960 matrix coefficients plus
  1,440 projected corner/depth coordinates. Both modes and FP policies,3 clip
  ranges and5 conventional rectangles, including asymmetric and shifted ones.
  Every near/far frustum corner maps to the correct clip X/Y and depth0/1.
  Comparison tolerance3e-6 relative/absolute is explicit.
- **120 branch survey cases** including byte272=1, with setter/state/pose/SP
  assertions. Six mode1/flag1 cases with conventional symmetric top/bottom
  produce nonfinite values: that branch uses a different denominator. Numeric
  bit patterns and null classifications are retained. The nonzero-flag extent
  contract is unresolved; this is not a universal native API bug claim, a pass
  for those6 cases or a reason to normalize/clamp their output silently.
- Wrong image refuses before compilation/output creation. No existing managed
  adapter, toolkit or native game source is changed by this investigation.
- Private `windows/.local/offaxis-oracle/run02/oracle.json`, SHA256
  `1BDCF27663182F6A8C03BC422C4DBECCDEC15DA47F7BA234B828F8D7085DCFAA`.
  Function/context/intrinsics/macros/script/executable hashes and all120 cases
  retained. Initialrun01 retains the coefficient-only exploratory pass.

## Integration limit

GuestProjection.EncodeForMetres still targets the separately checked symmetric
builder's reverse-depth convention; do not change it to forward depth based on
the existence of slot48. Native unit scale, actual receiver/kind/mode/flag and
GPU depth clear/compare/shader use must be correlated. Future read-only camera
capture should include calls to44/48, kind+8/mode+12, byte272 and extents240..252
alongside the existing camera/packet identities and depth state.

The asymmetric setter/builder also does not prove side visibility: camera-derived
planes, scene packet/resource ownership, draw-list consumption and per-view
temporal/depth partition still require the [scene capture](SCENE-CUT-TRACE-20261102.md).
No guest writer/hook, camera replay, projection toggle or enabled renderer was
added. Native734/e223/payload remain unchanged. No game/window/GPU/input/device
initialization, install, owner-state write or rig lease occurred.
