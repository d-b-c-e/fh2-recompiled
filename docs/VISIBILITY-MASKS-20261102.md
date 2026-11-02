# Packet visibility consumes per-view frustums and separate instance state

`82EF12D0` passes frustum/metadata arrays and explicit view IDs to `82450DE8`.
The ordinary instance route reaches an actual AABB helper, then updates a
per-view byte and appends accepted records to category buckets. This is CPU
visibility construction; GPU projection delivery remains unestablished.
**CULLING HOLD remains.**

217 static checks pass across 85,237 generated functions, with 83 selected
source hashes. A closed offline fixture passes **422 new helper checks / 790
combined**, retaining the original 12 projection/plane disagreements and exit
2. The ordinary AABB helper also rejects all 12 kind-1 projected-interior boxes.
No production renderer, native binary or SDK code changes are included.

## Dispatch and view identity

The dispatcher clears the resource participation bitset at the pointer in
packet+8, using the byte length at +16. Eligible 256-byte resource records can
set bits by their nested resource index. This bitset is separate from instance
view masks, per-view visibility bytes and accepted output lists.

The synchronous branch constructs a context on the stack and calls `82450DE8`.
The asynchronous branch fills two 344-byte worker records at packet+14036 and
+14380. `824827F8` waits on worker+336, calls the same consumer with context at
worker+4, and signals completion at worker+340. These synchronization functions
and the worker are traced only; they are not executed by the fixture.

| Context offset | Source / meaning established |
| --- | --- |
| 0 | Frustum pointer: packet+1440, 192-byte stride |
| 4 | Metadata pointer: packet+8096, 32-byte stride |
| 8 | Explicit view-ID array, up to 128 copied bytes |
| 136 | Number of IDs |
| 140 / 144 | First axial ID and count for IDs 0..5 |
| 156 | Initially pointer to packet+7584; reused as view count below |
| 160 | Selected ID matching packet+44 |
| 164 / 168 | Scalars copied from packet+9296 / +9320 |
| 172 / 173 | Flags from packet+9302 / packet owner+216 |

The active source IDs start at packet+48, with count at +176. The 16-word
grouping table at `822486A8` sends ID 9 to group 0 and other IDs 0..15 to group
1. Neither ID 9 nor packet+44 is labelled the player/main camera from this
grouping alone. The fixture's 32 mask-bit cases do not qualify the dispatch
table for IDs beyond its traced 16 entries.

`82450DE8` calls `8244F4A0` for indexed lists, traverses the secondary resource
list through `8244EF48`, and processes primary 256-byte records through
`824501A0`. Before each primary-resource call it writes a selected ID-span
pointer to context+148 and its count to +156; the context is mutable scratch
state, not an immutable serialized schema. These paths use virtual methods, resource resolvers and shared
lists. They are not a demonstrated replay-safe scene cut.

## Ordinary instance and metadata route

`8244EF48` first resolves an instance and tests its +68 bit for the requested
view through `8244EEE8`. Its ordinary path derives `frustumBase + 192*viewId`
and `metadataBase + 32*viewId`, then calls `8244ED60`.

`8244ED60` applies additional instance gates, including a virtual slot-48 call.
It obtains AABB bounds through `8289FC18`. Before culling, it **negates and
swaps the minimum/maximum Z bounds**. The ordinary closed helper `82451138`
also uses the vector (1,1,-1,1) at `833F47C0`; a direct +Z synthetic box is not
the caller's input contract. The fixture reproduces the caller conversion.

The optional metadata gate `8244FA90` forms the AABB center and squared
half-extent length, then calls `8244FE60`. With a negative metadata+20 it
returns true. Otherwise it accepts when:

```text
metadata[16] * squared_distance(center, metadata_origin)
    <= metadata[24] * squared_half_extent_length
```

Field +20 selects bypass; it is not the numeric threshold in this comparison.
This is consistent with the preceding 32-byte metadata trace and does not
turn metadata into a GPU projection matrix. This gate is source-traced only.
For view 9 with additional volumes, `8244ED60` instead calls `8244FB10`;
that path is not covered by the ordinary-helper fixture.

## Masks, visibility bytes and output buckets

| Instance storage | Actual helper behavior |
| --- | --- |
| +68, 32-bit word | `8244EEE8`: test bit `1 << viewId` |
| +72, 32-bit word | `8244DFA8`: test bit `1 << viewId`; further role not inferred |
| +76+viewId, byte | `8244EF08`: store the requested visibility byte |
| +54, byte | Mark dirty when the stored byte changes |
| +108, word | Increment for changed nonzero input; decrement for changed zero input |

The byte setter returns without writes when the low input byte equals the
stored byte. Its qualified fixture inputs are binary 0/1 and IDs 0..31.
The source has no bounds check, count saturation or binary-input clamp; no
broader contract is implied by the fixture. It does not rewrite masks +68/+72.

On ordinary acceptance, `8244EF48` sets the visibility byte to 1, obtains a
five-bit category mask from instance virtual slot 20, and appends to each
enabled category. The bucket address is:

```text
*(packet+13844) + 16 * (5*viewId + category), category 0..4
```

Each bucket has a **16-byte header**, and `824515D8` appends **20-byte records**.
Its end pointer advances by 20; capacity exhaustion can call allocator
`82EE68B8`. These strides must not be conflated. Rejection sets the instance's
visibility byte to 0. ID 9 also has an additional side-effect call; its product
role remains unqualified. No allocator/output-list mutation runs in the fixture.

## Closed helper qualification

`windows/tools/fh2_visibility_check.py` reuses the 28-function camera fixture
and adds five actual closed helpers: `8244EEE8`, `8244DFA8`, `8244EF08`,
`82451138` and `824513C0`, for **33 linked generated functions**. No guest callee
is mocked. Synthetic memory is private; the expanded title image is data.

The 422 additional checks establish:

- All 32 bits of the two separate mask words read correctly. Binary visibility
  transitions maintain the byte, count and dirty flag; repeated values are
  byte-exact no-ops. Neighbor bytes and both input masks remain unchanged.
- Under both FP policies, both flag-272 values and three camera configurations,
  caller-converted symmetric interior boxes return 2; backward and beyond-far
  boxes return 0. The helper leaves camera record bytes unchanged.
- The separate support-plane helper `824513C0` accepts inside, touching and
  crossing AABBs, rejects a wholly outside AABB, and accepts zero planes.
- The ordinary AABB helper returns 0 for all 12 kind-1 projected-interior boxes.
  These are observed results, not assertions added to force a negative outcome.

The prior 368 checks pass, with all 12 original point/projection disagreements
intact. The combined tool exits 2 and the owned receipt remains failed for
that HOLD. This does not establish a real scene's branch selection, visibility,
GPU constants, rendered seams, gameplay or hardware behavior.

## Reproduce and retained evidence

Use the static command in the preceding camera documents. From a VS x64 shell,
under the CPU GO/owned-process route:

```powershell
python -I windows/tools/fh2_visibility_check.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-private-output>
```

Private root: `windows/.local/visibility-masks/`.

| Evidence | SHA256 |
| --- | --- |
| static03/result.json | 08B9B4B50D7A883021F9B12AC889FF6F2EFCE63CACA90EECD9D759D647DB89C7 |
| runtime02/result.json | 93273B4CF104DFA7F3D12BF6FEF6C1F292490C636365E0A0FA0BB13B0B6F6E77 |
| runtime02/visibility-summary.json | 76CA8AC3BAEB7D140F954B59C48816CE1C8E9EFA1B00533C8E357EBC6C7AFFF4 |
| owned02/result.json | F7073AE460D675AA852B3EDB5481859C979436282E9164087EDD9E3152BA3664 |
| owned01/result.json | FC50F19FC1C9485FC9CF23D7251965253E5588EAA2C1ED05B95FA6266B01588F |

GO494834 interval 2026-11-02T17:01:16Z..17:01:23Z, jobs 1 BelowNormal;
children quiescent, process query safe, lease released and literal absent.
GO494807's failed direct-+Z fixture is retained in runtime01/owned01 and was
safely released at 17:00:12Z. The corrected fixture changes only synthetic input
to match the actual caller. Both public tools refuse a wrong image before
output/compile; guard-result.json records that check.

No dispatcher/worker/scene/SDK DLL/game/window/GPU/audio/input/device/init,
installation or owner-state writes occurred. Native 734fff4 / SDK e223de8d
remain frozen. Next bounded source work: trace primary-resource output helper
`82451578` and special-view `8244FB10` separately from the ordinary path; follow
their output consumers without treating CPU visibility as GPU projection
delivery. No guessed plane swap, negation, bypass or renderer hook is added.
