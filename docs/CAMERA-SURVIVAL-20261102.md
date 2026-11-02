# After the symmetric overwrite: surviving point found, culling still held

`82F46BAC` is immediately after the symmetric builder's final camera write and
before its register/stack epilogue. A later asymmetric update survives the
subsequent native lazy-cache rebuild in the offline fixture. **This is not yet
a usable renderer hook:** all12 tested asymmetric cases have a projected
interior point rejected by the native plane test. The tool reports
`hold-culling-contract` and exits2. It does not convert that failure to green.

## Exact overwrite and later consumer

The previously traced8262CC40 camera feed calls receiver virtual80 with the
flag, then virtual44 with mode0. For the known deferred class, virtual44 is
82F44CC0; copied-mode callback82F44CA8 tail-calls the concrete receiver's slot44.
If that receiver is the base camera, its slot44 target is82F46988.

| Point | Concrete evidence | Future use / limit |
| --- | --- | --- |
|82F46BA8 | Last symmetric builder write: `stb r10,480(r31)`; matrix+80 and kind0/mode+12 already stored | Symmetric output is committed at this point |
|82F46BAC | Next instruction restores SP by256; remaining instructions restore LR/vector/FP/GPR state and return | Candidate observer/correction point after the last write; receiver stillr31, mode stillr30 |
|823F5920 | Calls82408998 then returns receiver+288 | Actual lazy derived-data getter used in the fixture |
|82408998 | Reads dirty480; on a miss clears96 bytes at+384, selects kind+8 and builds data at+288, then clears dirty | A correction must establish coherent kind/parameters/dirty before this consumer |

The lazy rebuild selects823FB1B0 for kind0 (FOV/aspect/clips),82E431E0 for
kind1 (stored extents/clips), and82E43690 for kind2. The fixture tests only
kinds0/1; the orthographic branch is linked for closure, not qualified.
Neither mode+12 nor flag272 is read by this cache dispatcher.

Static render-side examples call this helper on the view's configured pointer
at+400:8245E918,82457338 and82F5AC78. Some subsequently use+288 in plane/sphere
tests. These traces identify real consumers, not a complete main-scene culling
cut or proof that view+400 is the same runtime object as feed-context+40.

Returning from8262CC40 alone is not a universal post-write boundary. Dispatcher
824051A0 reaches82404CE8, which has both immediate-callback and queued-record
paths. The write may already have occurred or may still be pending. The
candidate above is inside the concrete writer, after its own write, irrespective
of that scheduling choice. Later independent writers can still overwrite it.

No hook is registered. A future native hook must first identify the actual
receiver/class/view, respect queue and object lifetime, preserve guest ABI/FP
state and establish the complete frame ordering. Using currentr3 as the camera
at this point is unsafe: the builder has used volatile registers; the verified
receiver witness here isr31. The fixture calls complete routines sequentially,
not an injected mid-assembly hook, so it does not qualify that hook's ABI.

## Offline survival checks

`windows/tools/fh2_camera_consumer_check.py` extracts a closed26-function set
from the qualified private generated source. It compiles actual symmetric and
asymmetric builders, extent/flag setters, cache getter/rebuilder, plane/sphere
test and their real math/memory/frame helpers. No guest callee is mocked.
Unreachable kind2 helpers are included only to link the complete consumer.

For each of12 cases (both FP policies, flags0/1 and3 clip/FOV/aspect tuples),
with a synthetic identity pose:

- **Early asymmetric -> symmetric -> consumer** matches the symmetric baseline:
  the overwrite is reproduced.
- **Symmetric -> asymmetric -> consumer** retains the asymmetric matrix/kind,
  clears dirty and produces a different derived cache: the late update survives.
- Repeating the clean getter leaves all512 camera bytes unchanged. Getter
  SP/LR/r31 and return pointer are checked; dirty rebuild only changes derived
  bytes288..479 and dirty480, preserving the matrix/pose/other camera bytes.
- A deliberately matrix-only synthetic patch leaves the clean symmetric cache
  and kind untouched. This reproduces stale derived data and is not a proposed
  guest-memory writer.

**360 ordering/cache/projection checks pass.** This is the highest passing
level. It does not imply geometrically consistent visibility.

## Containment finding and next work

The same executable runs actual824153F8 with radius0 on the rebuilt planes.
Each asymmetric case uses stored extentsl=.4n,r=1.6n,t=.6n,b=-.6n. A point
strictly inside the actual stored projection is selected by its measured
matrix convention (X sign changes with flag272). **All12 projected interior
points are rejected by the native derived-plane test.** Symmetric baseline
controls accept+Z interior and reject-Z in all12 cases, so the helper is not
simply returning false for every tested camera.

For the first identity/flag0 case, the recorded first two halfspaces require
approximatelyx<=.4z andx>=1.6z, with a positive-Z near/far interval. This explains
why the conventional asymmetric interior is rejected in this synthetic setup.
It does not establish whether the real API expects different extent ordering,
an additional coordinate transform, or contains a source defect.

The next useful offline task is to trace actual kind1 extent producers and
the82E431E0 parameter/coordinate contract against this negative control, then
prove projection/plane agreement before admitting a writer. Do not reverse
fields, negate planes or bypass the consumer merely to make the test green.
Actual receiver selection, GPU depth clear/compare, full visibility packet
ownership and scene replay remain separate runtime questions.

## Reproduce and retained evidence

Use a VS x64 developer shell and the qualified app734/SDKe223 generated source/
headers. The image hash is pinned; generated bodies/image stay private:

```powershell
python -I windows/tools/fh2_camera_consumer_check.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-project-output>
```

Expected current result: ordering passes, `CULLING HOLD`, exit2, with a complete
result.json containing all12 memberships and planes. A generic green-only
runner will mark the step failed; the retained owned receipt does so honestly.
Wrong-image control refuses before compilation/output creation.

- Final private `windows/.local/camera-consumer/runtime03/result.json` SHA256
  `B6D14E6B06FADB55CC9677B2B3CD5F89C49197EBDFF3A8A2AAE596E84A8BFC76`.
  Includes26 function hashes, SDK context/intrinsics/macros/script/executable
  hashes, selected actual image words and all numeric plane observations.
- Static consumer/source summary: same evidence root/static-summary.json,
  SHA256 `7536794492484498007F470298D8AD6CF41808BB845DC36AD31D5EF2FDDA4546`.
  Source-bearing extracts remain private alongside it.
- GO493601 first hypothesis run failed containment after ordering checks;
  GO493677 added exact plane/sample diagnostics. Both failures remain intact.
  Final GO493703 interval2026-11-02T13:18:44Z..13:18:51Z, jobs1, BelowNormal,
  retained owned03/result.json SHA256
  `4832D36158D6A0CC67357F2CFE912CC74F37A638CF92979765CF19F1FDF15FC7`.
  It remains **failed**, matching fixture exit2; it is not relabelled passing.
  All3 intervals have quiescent owned children, safe process census, released
  named leases and absent literal tokens. No vuro custody remains.
- Initial owned01/result SHA D5ECDAAF...EC1E, owned02/result SHA13A5F426...C9F5.
  Compile vectorization warnings, failed assertions and full logs retained.

No SDK DLL or native app rebuild, queue/scene traversal, game/window/GPU/audio/
input/physical device initialization, installation, owner-state or display change.
Native734/e223/private payload and managed adapter remain unchanged. Physical
and rendered acceptance stay held.
