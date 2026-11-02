# Extent producers and the unresolved kind-1 plane contract

The traced extent setter and its deferred wrapper preserve all four arguments.
The concrete producer found sets `(-4, +4, +4, -4)` and selects **orthographic
kind 2**. It does not establish a kind-1 calling convention. **CULLING HOLD
remains:** no field swap, plane negation, culling bypass or native hook is added.

## Field and constructor path

The image is pinned to SHA256
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`.
Base camera table `8224FBDC` and refcounted table `82002D44` agree at the
relevant slots:

| Slot | Target | Established behavior |
| --- | --- | --- |
| 44 | 82F46988 | Symmetric projection, kind 0 |
| 48 | 82F43678 | Asymmetric projection, kind 1 |
| 52 | 823F2568 | Orthographic projection, kind 2 |
| 76 | 823F2FF0 | f1/f2/f3/f4 -> fields 240/244/248/252; dirty 480 = 1 |
| 196 | 823F3068 | Clip setter used by the identified producer |

Deferred slot 76 (`82F44FB0`, table `8224FE8C`) copies the floats to payload
offsets 4/8/12/16. Callback `82F44F90` loads them back into f1/f2/f3/f4 and
tail-calls the concrete slot 76. There is no field reversal in either step.
These are static paths; no queue, allocator or callback is executed here.

Lazy dispatcher `82408998` passes fields 240/248/244/252 to kind-1 constructor
`82E431E0` as f1/f2/f3/f4, followed by near/far in f5/f6. Giving these neutral
names Xfirst/Xsecond/Yfirst/Ysecond, the constructor explicitly forms four
near-corner triples before its vector cross products and normalization:

| Stack offset | Triple |
| --- | --- |
| 160 | (Xfirst, Yfirst, near) |
| 112 | (Xfirst, Ysecond, near) |
| 144 | (Xsecond, Ysecond, near) |
| 128 | (Xsecond, Yfirst, near) |

It also derives pose data through matrix helper `82422D80`. The dispatcher
does not pass mode 12 or flag 272 to this constructor. Corner construction
alone does not prove which side of each plane is intended to be accepted by
every downstream consumer. The previous [actual plane-test result](CAMERA-SURVIVAL-20261102.md)
remains the negative control: conventional asymmetric limits produce
contradictory positive-Z side halfspaces in the identity-pose fixture.

The base constructor `82F46838` initializes extent fields to `(0,0,1,1)` and
**kind 3**, not kind 1. Its refcounted factory `82F5BE50` replaces the vtable
with `82002D44`. Those defaults cannot be cited as a kind-1 producer contract.

## Actual producer and orthographic control

`82F50780` obtains the owner's camera through virtual 56 and smart-pointer
extraction `82599210`. It sets aspect 1, clips 0.1/7.5, and extent arguments
`(-4,+4,+4,-4)`, then calls **slot 52 with mode 0**. The two extent constants
come from `8209282C` (-4) and `82004ABC` (+4); clip constants are at
`8224FA5C` and `8224FA60`. The base/refcounted slot identity makes this an
orthographic control, not evidence that it selects asymmetric perspective.

The extended closed-function fixture executes that setter/builder/cache path
on an identity pose, with flag 0, under both SDK FP policies. The real plane
helper accepts the center `(0,0,3.8)` and rejects points behind `(0,0,-1)` and
beyond `(0,0,8)`. It also accepts `(-5,0,3.8)` and `(5,0,3.8)`, despite supplied
extents +/-4. Consequently this control does not qualify projection/plane
agreement either. Accepting those orthographic samples and rejecting every
tested kind-1 interior are different observations; neither authorizes a fix.

The existing 12 kind-1 cases still reject their projection-interior points.
**368 ordering/cache/projection assertions pass**, including the original
360 plus orthographic commit/getter checks. Membership observations are
reported separately. Final status remains `hold-culling-contract`, exit 2;
the owned worker receipt remains failed. No assertion was weakened.

## Search limits and next step

`windows/tools/fh2_extent_trace.py` records a reproducible bounded static scan:
direct calls to the extent setter, asymmetric builder, kind-1 constructor and
base factory; direct multi-field float stores based on r3/r31; and candidate
virtual 48/76 sites. Candidate slot numbers are not camera identities. The
two intersecting slot candidates (`823F5A68`, `82D4B228`) do not establish a
camera: their argument paths include boolean/non-float slot-76 calls.
The broad store scan also finds unrelated objects with matching offsets.
The scan covers 85,237 generated functions: 40 static contract checks pass;
28 broad float-writer candidates, 73 slot-76 float candidates and 143 slot-48
mode candidates are retained as metadata. Wrong-image input refuses before
output creation.

No direct asymmetric-builder/extent-setter caller was found; the only direct
kind-1 constructor caller found is the lazy dispatcher. This is **not proof
that kind 1 is unused**. Indirect calls, variable slots, object copies, aliases
and alternative writers remain outside this bounded proof. There is no
source-backed kind-1 extent producer yet.

Next work should identify an actual kind-1 selection with a known camera
receiver, then follow its extent data and pose to the consuming view. An
independent check of the original vector corner/cross-product sequence would
also distinguish constructor semantics from generated SIMD semantics. Keep
the current negative cases intact. Runtime receiver/view correlation,
rendered depth/culling, scene replay and hardware remain separate held gates.

## Reproduce and private evidence

Read-only static trace, with no compiler or execution of guest code:

```powershell
python -I windows/tools/fh2_extent_trace.py --generated <generated/default> --image <expanded-image.bin> --out <fresh-private-output>
```

Run the extended consumer fixture using the command in
[CAMERA-SURVIVAL-20261102.md](CAMERA-SURVIVAL-20261102.md), under the existing CPU
GO/owned-process route. It now links 28 actual closed functions; no callee is
mocked, no SDK runtime DLL is loaded, and only synthetic guest memory is used.

Private root: `windows/.local/kind1-contract/`. Source-bearing JSON extracts,
generated harness, image and executable remain private; public tools contain
only the generator, assertions, derived metadata and this explanation.

- `runtime01/result.json` SHA256
  `0C826057A8FD1551CD64E597242748997A0C085448B9430361AC42C40205F8E5`.
- `static01/result.json` SHA256
  `E38A7337AE91D9FCCAA73BE752FE749ACB2E8000FE1902BA2E1B3C83EA97D5E3`.
- `owned01/result.json` SHA256
  `CC116E4F360A74570EC83DA4129C7207319457022B7995A571CE6843DFCBAA37`.
- GO493861 interval 2026-11-02T14:05:07Z..14:05:15Z, jobs 1, BelowNormal.
  Children quiescent, process census safe, lease released and literal absent.

No game, window, graphics/audio/input/device initialization, installation or
owner-file writes occurred. Compiled native 734fff4 / SDK e223de8d and the
private native payload remain unchanged.
