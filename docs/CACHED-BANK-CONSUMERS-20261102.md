# Cached-bank consumers upload groups larger than the staging write

`82426180` drains dirty cached banks through `824266B0`; `82426800` selects bank
bits using an entry's masks before calling the same writer. Each dirty bit
covers **four vectors / 64 bytes**. The preceding 21-vector staging write marks
six groups, so a full eligible run uploads **24 vectors**, including three
preserved cached vectors. This is source evidence, not an executed upload or
proof of which vector block is the GPU projection. **CULLING HOLD remains.**

288 static checks pass across 85,237 functions, with 126 selected source hashes.
A closed 40-function fixture passes **5,184 new staging checks / 9,037 combined**,
retaining the original 12 projection/plane disagreements and 12 ordinary kind-1
AABB rejections. The tool still exits 2. No production/native/SDK changes occur.

## Two dirty-bank consumers

`82426180` reads dirty qwords at context+0/+8. For nonzero values it calls
`824266B0` with bank starts +1920/+6016 and encoded destination-word bases
16384/17408 (`4000`/`4400`). It clears each corresponding dirty qword after
the call, then processes further state and command words.

`824265F8` is a separate entry dispatcher. With a nonzero TLS byte 8 and a
non-null owner+9348 it queues the supplied entry through owner+9348+32, updates
associated state and returns through its synchronized route. Otherwise it
selects owner+9312 or +9316, reads context+20 and calls `82426800` directly.
The queue path and direct path are not treated as interchangeable execution.

`82426800` has a special entry-type branch. On its ordinary path it intersects
context dirty qword +0 with entry+24 and qword +8 with entry+32, then passes
nonzero intersections to `824266B0`. After each such call it clears the **whole
corresponding context dirty qword**. If the intersection is zero it skips that
call and clear. This describes the instructions; no lifecycle defect or
retention policy is inferred without tracing the surrounding entry contract.

## Group writer and direct command layout

`824266B0` finds the leading dirty bit and a contiguous run of set bits. For
each skipped group it advances the cached source by 64 bytes and the encoded
destination by 16 words. For a run of G groups it writes 16*G data words.

With sufficient capacity, the direct path pads with literal `80000000` words
as needed to align vector payload stores, writes this header, then copies four
16-byte vectors per group:

```text
header = ((16*G - 1) << 16) | (encoded_base + 16*first_group)
```

The cursor points to the last written word and is stored at context+48.
When capacity is insufficient the helper calls `82477138`; that fallback's
implementation is a separate trace boundary. No bank writer or fallback runs
in the fixture.

For the prior dirty mask `00000000FC000000`, leading groups=32 and run groups=6:

| Bank | Cached source range, inclusive | Data words / vectors | Direct-path header |
| --- | --- | --- | --- |
| +1920, encoded base 4000 | 3968..4351 | 96 / 24 | 005F4200 |
| +6016, encoded base 4400 | 8064..8447 | 96 / 24 | 005F4600 |

The 21-vector copy writes only 3968..4303 or 8064..8399. Its three following
vectors remain cached state, not zeroed padding. The fixture verifies those
bytes remain unchanged. The derived headers apply to the full eligible mask
and direct-capacity path; an entry-mask intersection can select smaller runs.
Encoded word destinations are recorded literally rather than assigned an
unverified shader-stage or GPU-projection meaning.

## Secondary instance identity remains a separate resolver path

The ordinary record resolver `8244F418` returns cached record+8 immediately
when present. Otherwise it uses candidate record+4 or obtains a candidate via
`8244DFC8(record[0])`. A candidate passes `8244EBD8` only when its word+48 is 1
and byte+64 is nonzero; then the resolver stores record+8 and instance+120 as
a backlink. These fields are admission checks, not a concrete C++ type.

`8244DFC8` uses a cached resource+16 pointer. Its lazy path checks resource
state through `82EE4578`, obtains a reference through `82D35E18`, and reads the
pointer at referenced resource+128. `82D35E18` validates via `8244CC30` and calls
`82DA57F0` to copy a reference: virtual slot 8 acquires and slot 12 releases.
That is not a newly identified concrete-instance constructor.

`8244CC30` synchronizes resource state, updates its counter and can invoke
resource virtual slots 44 and 68. The implementation that populates the
resource body, and the concrete instance ultimately dispatched by
`8244BE38` virtual byte offset 164, remain unresolved.

A tempting RTTI match is explicitly excluded. Table `820017AC` names
`Presentation_Unified::CTrackRenderModelInstance_Unified`, but its next complete
object locator occurs at byte offset 60. The next table at `820017EC` belongs
to a thread-safe `CUIPostProcess` wrapper. Reading `820017AC+164` crosses that
boundary; it does not identify the instance's method. Its slot-48 helper also
has an output-vector ABI rather than the ordinary culling gate's ABI. Broad
RTTI candidate matches do not establish the runtime receiver.

## Closed staging-copy qualification

`windows/tools/fh2_staging_copy_check.py` retains the prior 38 actual functions
and adds the two closed 54-instruction writers `82445C78`/`82445B18`. No guest
callee is mocked. The destination context is aligned; arbitrary destination
alignment is not admitted by this fixture.

The 5,184 new checks cover 1,296 cases: 36 valid index/count pairs, six source
byte offsets (0,1,3,4,7,15), three 64-bit dirty masks and both writers. Indices
include 0,1,127,128,235,255; counts include 0,1,3,4,5,21,32 when within the
256-vector bank. Against an independent byte-copy/64-bit-OR oracle they verify:

- Exact copied bytes and the selected dirty qword's OR, including a high-bit
  mask and zero-count calls that still update dirty state.
- The other bank, unrelated context bytes, preceding/following guards and
  uncopied vectors remain unchanged.
- Source bytes and their surrounding guards remain unchanged.
- SP, LR and the r31 sentinel survive; repeating the call is byte-exactly
  idempotent.

The prior 3,853 checks pass, including the two previously qualified leaf sorts
and all culling negatives. Bank consumers, command emitters, synchronization,
resource resolution, scene traversal and submission remain source-only.

## Reproduce and retained evidence

Use the preceding camera documents' static command. From a VS x64 shell, under
a fresh CPU GO and the owned-process route:

```powershell
python -I windows/tools/fh2_staging_copy_check.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-private-output>
```

Private root: `windows/.local/cached-bank-consumers/`.

| Evidence | SHA256 |
| --- | --- |
| static02/result.json | BA392023A4306C8ED93915E4805CDCDDAB0D5A02C489FE156201567EB6EFF5AD |
| runtime01/result.json | A4DA90FA8B446ECBF15249470A5BEA57203D5DF72CD86B97208F8286C55C49D3 |
| runtime01/staging-summary.json | 0E138210F98DA4D739D82AEC796EAE34748717235284DDD9A6F7BA92C482C7F4 |
| owned01/result.json | 7DAD7AD5F95EFB5B9AEE2016491BE931B6440D28DD69B0E6A6DB90732ACD76C9 |

GO495396 interval 2026-11-02T18:25:39Z..18:25:46Z, jobs 1 BelowNormal;
children quiescent, process query safe, lease released and literal absent.
The owned receipt remains failed for retained HOLD/exit 2, not a crash.
Both public tools refuse a wrong image before output/compile. Private image,
generated bodies, executable, candidate scans and receipts remain local.

No recursive sort/guest allocator/bank consumer/command emitter/submission/
dispatcher/worker/scene/SDK DLL/game/window/GPU/audio/input/device/init/install/
owner-state work occurred. Native 734fff4 / SDK e223de8d remain frozen.
Next source: writer capacity fallback `82477138` and resource body population
through the virtual-68 path, retaining GPU projection and concrete virtual-164
identity as separate gates. No guessed field swaps, bypass or renderer hook.
