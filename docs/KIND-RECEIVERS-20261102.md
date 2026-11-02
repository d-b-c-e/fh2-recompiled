# Constant-1 slot-32 receiver identities

The two named targets are **not camera kind selectors**: `8293D7F0` operates
on UI container items, and `83237BD8` releases a reference-counted small-string
object. The next offline candidate, `82D4CB20`, resolves to audio emissions.
The extended static trace passes **71 checks**. Actual kind-1 camera selection
and culling remain unresolved; no native change is proposed from these calls.

## Scrolling-list item call: 8293D7F0

RTTI for table `82086724`, COL `82312A58`, names
`ForzaUI::CAnimatedScrollingListCtrl` with subobject offset 108. Its slot 40
points to `8293D7F0`. Constructor `8293F718` installs that table at owner+108
and initializes the pointer vector at owner+304/+308/+312.

The target receives the +108 subobject. Its vector at +196/+200 is therefore
the same owner+304/+308 vector, not a camera list inferred from slot numbers.
Initializer `82931940` obtains `GROUP_ITEMS` (`8203A06C`) and populates that
vector through `8292F400`:

- Source RTTI descriptor `8337D1EC`: `CUI4Control`.
- Target RTTI descriptor `8337D488`: `CUIContainerItemCtrl`.
- Runtime cast helper `823F4828` receives source pointer, zero vfptr delta,
  those source/target descriptors, and a false reference flag. This matches
  Microsoft's documented [__RTDynamicCast argument contract](https://learn.microsoft.com/en-us/cpp/c-runtime-library/rtdynamiccast?view=msvc-170).
- Only a non-null cast result is appended through `82735E38`. The call at
  `8293D7F0` instruction 155 indexes that vector and invokes its slot 32.

This establishes the UI-container interface for the traced population/call
path. It does not identify every concrete UI item subclass or execute the UI.
The constant 1 is not evidence of a presentation-camera kind update.

## Reference release: 83237BD8

This function atomically decrements receiver+40. If the resulting count is
zero, it calls receiver slot 32 with r4=1. Its paired method `83237BB0`
atomically increments the same field.

| Primary table | Slot 0 | Slot 4 | Slot 32 |
| --- | --- | --- | --- |
| 822C5B60 | 83237BB0, increment | 83237BD8, release | 83237C40, deleting destructor |
| 822C5B84 | 83237BB0, increment | 83237BD8, release | 83237DA0, deleting destructor |

Constructor `83237D50` installs `822C5B84` at receiver+0, the companion
interface at +4, and initializes reference count +40 to zero. Both deleting
destructors inspect the small-string capacity at +28, use inline storage at
+8 or free the heap buffer, and honor the low delete flag in r4.

This identifies a reference-counted small-string lifecycle. An exact C++ class
name is not established, but the concrete slot-32 targets and receiver layout
rule out the presentation-camera setter `82F435E8` for this path.

## Next offline item: owner+4024 audio emission

Following the additional candidate in `82D4CB20`, assignment function
`82D48C60` loads the manager at `83588C0C`, invokes its slot 32, and stores the
returned smart pointer into owner+4024. The complete static chain is:

1. `82D3BF80` constructs `82D3B430` and stores the manager at `83588C0C`.
2. The constructor installs table `82149134`, RTTI `CAudioEngine`.
3. That table's slot 32 is factory `82D371F0`.
4. Its normal allocation installs table `821486DC`, RTTI
   `TRefCountedObject<CAudioEmission>`. Its fallback installs `821489C4`, RTTI
   `TRefCountedObject<CDummyAudioEmission>`.
5. The result reaches owner+4024, whose slot 32 is called with constant 1 in
   `82D4CB20`.

The receiver is an audio-emission interface on these paths, not a camera.
No audio engine or emission was initialized or executed during this trace.

## Remaining scope

The original seven constant-1 sites in six functions now have three identified
non-camera receivers. Four sites in three functions remain unclassified:
`831CA938` (two sites), `831CB410`, and `831349B8`.

The next source task is to trace the shared owner+256 receiver used by
`831CA938`/`831CB410` and owner+56 used by `831349B8` through their creation and
assignment paths. Extra pointer arguments and checked return values suggest
different interfaces, but those hints alone do not prove their identity.
Variable-kind calls, aliases, other writers and object-copy paths remain
outside this bounded search. Do not infer that kind 1 is unused.

## Reproduce and evidence

```powershell
python -I windows/tools/fh2_extent_trace.py --generated <generated/default> --image <expanded-image.bin> --out <fresh-private-output>
```

The pinned-image trace scans 85,237 generated functions, verifies the selected
source sequences, RTTI names and vtable identities, and emits hashes/derived
metadata only. Wrong-image input refuses before output creation.

Private root: `windows/.local/kind-receivers/`, including `static01/result.json`,
source-bearing extracts and the control result. No guest body/image is public.
Static result SHA256:
`18E0150BBA169011490AD29A76891EADCF2231BA4D30738603886A4DF719DDF1`.
This increment is read-only source/image analysis: no compilation, guest
execution, CPU lease, SDK DLL, game/window/device initialization, installation
or owner-state writes. Existing 368 fixture assertions and 960 VMX comparisons
are retained prior evidence and were not rerun. Native 734fff4 / SDK e223de8d
remain frozen; culling stays HOLD.
