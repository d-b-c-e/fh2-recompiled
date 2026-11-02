# View getter and native mirror-matrix consumer

The view's slot-32 getter returns an acquired reference to its registered
camera. The traced `82F4F1D0 -> 82F46060` path builds a native mirror-camera
transform, rather than establishing a main-projection upload. Four destination
cameras are initialized symmetrically. The sibling packet path independently
builds symmetric frustums from snapshots. **CULLING HOLD remains.**

**142 static checks pass** over the pinned source/image; no guest code ran.

## View getter ownership and source inputs

`CPresentationView` table `8200243C`, slot 32, targets `824517D0`. Its ABI uses
r3 as output-reference storage and r4 as the view receiver. It forwards
view+400 to copy helper `82DE9AF0`, which acquires a non-null object's reference
through slot 8, stores the pointer in the output wrapper, and returns that
wrapper. The getter returns the output-storage pointer, not a raw camera.

`82F4F1D0` obtains that reference, resolves it against the presentation camera
registry using `82473418`, and calls `82408998` on the resolved camera. It then
loads the derived vector at camera+448. This caller does not directly load the
resolved camera's stored projection at +80.

Associated-provider lookup `82456A90` follows presentation slot 88 (field
10120), the view camera getter, and camera slot 92 (field 500). The provider's
concrete runtime class is not identified here. Its slot 48 supplies a matrix;
slot 480 supplies selector-dependent data. These are source contracts, not a
live receiver observation or qualification of every indirect callee.

## What 82F46060 reads and writes

Let S be the caller's stack pointer. The callee allocates 304 bytes, so its
loads at offsets 452/460/484 correspond to caller offsets 148/156/180:

| Input | Source in 82F4F1D0 |
| --- | --- |
| r3..r10 | Eight 64-bit chunks of the provider-supplied matrix |
| Caller S+80..143 | Composite matrix calculated from provider data |
| v1 | Resolved source camera's derived vector at +448 |
| Caller S+148 | Pointer to the 64-byte output at S+272 |
| Caller S+156 | Selector |
| Caller S+180 | Optional plane/transform record pointer |

The helper normalizes direction inputs, derives a point/direction, invokes
`82E41AA0` and look-at-style builder `82478900`, then stores four vectors
through the output pointer. It does not perform a GPU upload.

The reflection algebra is specifically a reflected **ray target**, not the
usual mirrored-eye point. For input P, origin O and unit normal n,
`82E41AA0` computes:

```text
T = P - 2 * ((P - O) - n * dot(n, P - O))
d = O - P
T - O = d - 2 * n * dot(n, d)
```

For example, P=(2,3,4), O=(0,0,0), n=(0,0,1) gives T=(-2,-3,4).
The caller uses origin O and direction T-O in the look-at builder. This
explains the reflected-view construction without claiming a mirrored-eye
position or a newly executed numerical test. Selector 0 follows a separate
fallback branch. Matrix space, exceptional inputs and full ABI behavior are
not independently qualified by this static trace.

## Destination cameras and mirror evidence

`82F4EE70` uses literal `mirrorL*` for selector 2 and `mirrorR*` for selector 3
(image addresses `82250CC0` and `82250CB4`). Selector 1 obtains provider data
through slot 484. The selector labels and reflected-ray/look-at operations
establish this path's native mirror role; the concrete provider remains opaque.

`82F59FB8` creates four destination cameras using the typed presentation
factory, stores them at presentation+9196+4*selector, sets their FOV/aspect/
clips, and calls symmetric slot 44 with mode 0. Thus their setup kind is 0.
`82F4F1D0` writes the resulting matrix to the selected camera through slot 168,
target `823FBA80`. That setter writes the camera matrix at +16 and dirties 480;
it does not write the projection at +80 or select kind 1.

This is camera-transform work, not proof of a safe insertion point for an
asymmetric main-camera projection or a reusable scene-render pass.

## Next offline item: sibling packet path

The only other direct caller of `82F46060` found is packet builder `82F4D818`.
It invokes the same helper, then calls symmetric frustum constructor
`823FB1B0` using copied matrix and FOV/aspect/clip values. A separate branch
uses packet fields 9152..9208 and 9280..9292 for another symmetric rebuild.
These branches build packet-local derived data independently of the camera
object cache tested earlier.

Consequently, surviving the object-level symmetric overwrite and lazy getter
does not establish packet projection/culling consistency. The packet branches
must be traced before admitting a correction. This is not an original-game
regression finding: the four traced mirror cameras are initialized symmetrically.
Branch execution, main-view roles and rendered visibility remain unproved.

Next useful source work is snapshot producers `82F46458`/`82F47188` and packet
helper `82F42C50`: determine which stored projection or FOV data reaches each
packet record, preserving the existing negative kind-1 cases. No guessed
field swap, plane negation, bypass or renderer hook is added.

## Reproduce and retained evidence

```powershell
python -I windows/tools/fh2_extent_trace.py --generated <generated/default> --image <expanded-image.bin> --out <fresh-private-output>
```

Private root `windows/.local/view-consumer/` retains selected source extracts,
getter/helper records, mirror setup, sibling callers, controls and final
`static01/result.json`. The result contains 142 checks, 55 selected function
hashes and the two direct mirror-helper callers; all 85,237 functions were
scanned. Wrong-image input refuses before output creation. No image or
generated body is published.
Static result SHA256:
`AFA99BD8E775976CCDBB47AAC3AFE7285C46199AB56A47834B400BAE50B9E327`.

No build, guest execution, CPU lease, SDK DLL, game/window, graphics/audio/
input/device initialization, installation or owner-state writes occurred.
Prior 368 fixture assertions and 960 VMX comparisons are retained, not rerun.
Native 734fff4 / SDK e223de8d remain frozen. Static mirror interpretation is
not live mirror, gameplay, main-projection, culling or physical acceptance.
