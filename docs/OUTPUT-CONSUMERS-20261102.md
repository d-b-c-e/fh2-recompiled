# Visibility records reach bucket queries, ordering and submission consumers

The primary-resource helper `82451578` constructs the same 20-byte record
schema used by the ordinary instance path. Its consumers read the renderer's
bucket pool at owner+56888. Special AABB helper `8244FB10` returns the parent
frustum classification and separately writes a supplemental-plane tag. That
tag is forwarded into submission state; it is not a per-view visibility mask.
**CULLING HOLD remains; GPU projection delivery is unestablished.**

241 static checks pass across 85,237 functions, with 101 selected source hashes.
A closed 36-function fixture passes **1,479 new checks / 2,269 combined**,
retaining the original 12 projection/plane disagreements and 12 ordinary
kind-1 AABB rejections. The combined tool still exits 2. No production/native/
SDK changes, game launch, submission or GPU work are included.

## Primary output and shared record schema

`82451578` is called directly only by `824501A0`. Its arguments include the
bucket pool, view ID, category, primary resource pointer and tag. It returns
without appending if source+16 is zero. Otherwise it builds this stack record
and passes it to the existing `824515D8` vector append:

| Record offset | Primary helper value | Downstream use established |
| --- | --- | --- |
| 0 | Primary resource pointer | Primary-resource submission branch |
| 4 | Zero | Secondary/ordinary-instance branch when nonzero |
| 8 | Float zero | Updated by the metric pass, then used by ordering paths |
| 12 | Incoming tag | Forwarded into submission state |
| 16 | Byte zero | Secondary submission flag when populated by other producers |

The header address is `pool + 16*(5*viewId+category)`; record stride is 20.
The helper's ordinary source path can allocate through append capacity growth,
so neither append nor its allocator is executed by this fixture.

Publisher `82F5AF30` derives packet+13844 from `*(viewOwner+36)+56888`.
Matching readers use the same owner-relative pool and 16/20-byte structure.
Other generated routines also use offset +13844 for command-buffer state.
Those matches are excluded: an equal numeric offset does not establish a
shared receiver or an alias of this pool.

## Special AABB classification and tag

Both `8244ED60` (ordinary instance wrapper) and `8244FEC0` (primary resource
wrapper) call `8244FB10` for view ID 9 with at least one supplementary plane.
The primary wrapper loads its bounds from record+32/+44; the ordinary wrapper
retains its previously traced Z-negate/swap conversion. Both wrappers clear
the output tag before the conditional call. The helpers themselves are not
relabeled interchangeable object layouts.

The closed helper first performs the six-plane parent-frustum test. If that
rejects, it returns 0 immediately **without writing the tag pointer**. Otherwise
it computes parent result 1/2 and separately classifies one or two supplementary
planes. Qualified tags for inside/crossing/outside AABB relations are:

| First plane | One plane | Second inside | Second crossing | Second outside |
| --- | --- | --- | --- | --- |
| Inside | 8 | 32 | 40 | 8 |
| Crossing | 0 | 32 | 0 | 10 |
| Outside | 2 | 2 | 2 | 2 |

Supplemental rejection can produce tag 2 while the return value still reports
an accepted parent frustum. It is therefore not a combined boolean visibility
test. The two-crossing intermediate tag 42 is explicitly reduced to zero.
The table is qualified for counts 1 and 2; no arbitrary-count contract is added.
The product meanings of the tag bits remain unresolved.

## Actual output consumers

`82EE7A10` initializes 160 headers at the pool: three pointer words per 16-byte
header, leaving the fourth word untouched. It also initializes two groups of
four min/max pairs at +2560..2623 from title constants. It leaves pool+2624
untouched. `82EE8868` is the separate clearing path and writes +2624 after
processing the lists; it is source-traced, not executed here.

`82EDBE28(owner,view,category)` reads the selected begin/end pointers, divides
their difference by 20, and returns whether that record count is nonzero.
Its direct caller `82F587F0` scans category 0 for view IDs 0..5 after a larger
presentation update. The query alone does not submit or render those records.

`8244F570` loops categories for a selected view, accumulates a float into each
record+8, and calls ordering routines `82479DF0` or `824697C8`. Their leaf
helpers `82479CE8`/`82480298` compare the **unsigned word** at +8 in ascending/
descending order. This does not qualify arbitrary signed-float/NaN ordering.
Their recursion and 20-byte stepping are source-traced; the fixture executes
no ordering path.

`82449970` selects the same bucket and iterates 20-byte records:

- A nonzero record+0 takes the primary path, including `82446268`. Record+12
  is passed at caller stack+84, read at callee stack+244 after its 160-byte
  frame, and can reach state helper `8244BFD8`. Further branches call
  `82F78BC0` or `824463B0`.
- The secondary path reads record+4, resolves it through `8244F418`, and calls
  `8244BE38` with record+12 and byte+16. That helper forwards the tag through
  `8244BFD8` and reaches instance virtual slot 164 after additional gates.

`8241E598` and `82F7AC00` also read category-0 lists using `80*viewId`, equivalent
to five 16-byte headers, and branch between primary/secondary record pointers.
`82F7A830` additionally reads pool+720, the header for view 9/category 0.
These are bounded source consumer findings, not proof of a selected live pass,
successful GPU constants, rendered geometry, or a replay-safe scene closure.

## Closed offline qualification

`windows/tools/fh2_output_consumer_check.py` retains the prior 33 actual functions
and adds `8244FB10`, `82EDBE28` and `82EE7A10`. It reuses the camera and visibility
fixtures without mocking guest callees. The 1,479 new checks establish:

- 144 supplemental-plane cases match the table under both FP policies, both
  flag-272 values and three symmetric camera configurations. Each retains
  fully-inside parent result 2, writes only four tag bytes and preserves the
  camera record. Parent-frustum rejection preserves a sentinel output tag.
- The real pool constructor clears all 160 headers' first three words, leaves
  their fourth words and adjacent bytes unchanged, and copies the expected
  sixteen extent words. No allocator is called.
- All 160 view/category combinations return the expected empty/nonempty result
  for counts 0, 1 and 3: 480 queries, with header bytes unchanged after each.

The prior 790 checks pass, including all 12 original disagreements and 12/12
ordinary kind-1 AABB rejections. Parent-intersecting result 1 is source-traced
but not added as a new special-helper runtime control in this increment.
No change clears the kind-1 HOLD or establishes an actual kind-1 producer.

## Reproduce and retained evidence

Use the preceding camera documents' static command. From a VS x64 shell,
under the CPU GO/owned-process route:

```powershell
python -I windows/tools/fh2_output_consumer_check.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-private-output>
```

Private root: `windows/.local/output-consumers/`.

| Evidence | SHA256 |
| --- | --- |
| static04/result.json | 5D9D8D92397FBB426BF446E2F757887D9A7520FD80874336DFF2F1E70CF2241D |
| runtime01/result.json | FCEFA92AA8D25D278DA2AD25BD1F3F5D7D2908CFBB534F34F33706A8D95D294D |
| runtime01/output-summary.json | FD8D0A515B1B49F561682B6290D833590500A54D7AB8FE256AE9DE5B75C33606 |
| owned01/result.json | 89B9B4200F4D162149F324AF6804E167FA3450215DC628514A67B544A7332172 |

GO495056 interval 2026-11-02T17:27:42Z..17:27:50Z, jobs 1 BelowNormal;
children quiescent, process query safe, lease released and literal absent.
The owned receipt remains failed for the retained HOLD/exit 2, not a crash.
Both public tools refuse a wrong image before output/compile. Private image,
generated bodies, executable and all receipts remain local.

No allocator/sort/submission/dispatcher/worker/scene/SDK DLL/game/window/GPU/
audio/input/device/init/install/owner-state operations occurred. Native 734fff4 /
SDK e223de8d remain frozen. Next source: submission state helper `8244BFD8` and
primary sinks `82F78BC0`/`824463B0`, keeping instance virtual-164 behavior and
actual GPU projection delivery separate until their consumers are established.
