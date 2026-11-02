# Submission tags and matrix-derived staging are distinct paths

`8244BFD8` emits a two-word command containing the submission tag. The two
primary sinks `82F78BC0`/`824463B0` traverse resource descriptors and stage
matrix-derived data through a separate scratch object and cached vector banks.
This establishes those source paths, not the actual GPU projection consumer or
the secondary instance's concrete virtual-slot-164 implementation.
**CULLING HOLD remains.**

266 static checks pass across 85,237 functions, with 113 selected source hashes.
A closed 38-function fixture passes **1,584 new ordering checks / 3,853 combined**,
retaining all 12 original projection/plane disagreements and 12 ordinary kind-1
AABB rejections. The tool still exits 2. No production/native/SDK changes occur.

## Tag command writer: 8244BFD8

This helper receives a command-state owner in r3 and the incoming tag in r4.
The cursor is owner+48, the limit is +56. If the cursor is above the limit it
calls `8241CD50`; that helper can refill, synchronize and obtain another cursor.
Neither helper executes in the offline fixture.

The writer appends two 32-bit words using preincrement stores:

```text
C0006000
owner[13084]
```

It stores the final cursor at owner+48. The header is recorded as a literal
command word; its hardware opcode/product meaning is not guessed.

| Owner field | Incoming tag nonzero | Incoming tag zero |
| --- | --- | --- |
| 13084, word | Incoming tag | FFFFFFFF |
| 13092, word | 1 | 0 |
| 13088, word | 0 | 0 |
| 11060, word | Incoming tag | 0 |
| 11064, word | 0 | 0 |
| 11068, byte bit 0 | Clear | Recomputed by conditions below |

For zero tag, the low status bit is set only when the following source
condition holds; the other bits in byte+11068 are preserved:

```text
!(flags & 0x0C) && owner_byte[12563] == 0 &&
((flags & 0x10) ||
 ((flags & 0x20) && every_pair(A == B || A == 0)))

A words: 12816, 12820, 12824, 12828, 12832
B words: 13104, 13108, 13112, 13116, 13120
```

This is a cached-state/tag command contract. It is not a 4x4 projection copy,
and the tag's product meaning is still unresolved. Equal numeric offsets in
unrelated objects are not treated as shared receiver identity.

## Primary sinks and cached vector banks

`82446268` previously routed primary records to `82F78BC0` or `824463B0`.
Both sinks apply resource/subpass gates and traverse nested descriptors through
virtual methods. They read transform data via resource+16 and compose it with
the caller-provided matrix blocks. This is not a closed scene replay route.

Both use renderer scratch at **owner+59792** (`addis 1; addi -5744`). Scratch+1212
points to the selected command-state context. `82446388` obtains that context:
a TLS byte at `*r13+8` selects graphics-owner+9312 or +9316, then reads +20.
No actual thread/context selection is established by static source alone.

`824463B0` calls `82445BF0` with a matrix-derived block. That wrapper resets its
scratch counters/flags and calls two copy helpers with logical vector index
128, count 21 and dirty mask `00000000FC000000`:

| Helper | Destination formula | Nominal range for index 128/count 21 | Dirty word |
| --- | --- | --- | --- |
| 82445C78 | context + 16*(index+120) | 3968..4303 | OR context qword +0 |
| 82445B18 | context + 16*(index+376) | 8064..8399 | OR context qword +8 |

These helpers copy 16-byte vectors, including an unaligned source-load path;
they do not emit a command-buffer packet. The destination math is source
evidence, not a qualification of arbitrary context alignment or a live ABI.

`82F78BC0` calls `82DE1B20` with the same scratch object. It stages five
four-vector blocks at logical indices 128, 132, 136, 140 and 144 in both banks,
then one tail vector at index 148. The five block masks plus tail mask combine
to the same `FC000000` dirty bits. The optional callback and material/resource
traversal remain unexecuted.

Later source boundaries are distinct:

- `824463B0` calls `8245FAE8` to process descriptor payloads and `82426E60` to
  finish a pending scratch entry. Those helpers call further state/entry code,
  including `824265F8`.
- `82F78BC0` reaches `82DE1F30`, which stages more data and calls `82426180`.
  Those later consumers still need tracing to establish command payloads,
  destinations and which source block is the GPU projection.
- The secondary record route remains `8244BE38` to a concrete instance's
  virtual slot 164. That target is not resolved merely by tracing primary sinks.

No base-camera projection getter or GPU projection identity is inferred from
matrix products, staging-bank duplication, dirty masks or a tag command.

## Closed ordering-leaf qualification

`windows/tools/fh2_order_leaf_check.py` retains the prior 36 actual functions and
adds the two closed 65-instruction leaves `82479CE8`/`82480298`. The parent
ordering routines select their leaf path for at most 32 records. No recursive
ordering routine, allocator, state emitter, staging helper or submission sink
executes in this fixture; no guest callee is mocked.

The 1,584 additional checks cover 396 cases: counts 0..32, six key patterns and
both directions. The patterns include increasing, decreasing, equal, repeated,
unsigned edge-word and deterministic mixed keys. Against an independent host
stable-sort oracle using the **unsigned word at record+8**, they establish:

- Correct ascending/descending order and equal-key stability.
- All 20 payload bytes move together, including fields unrelated to the key.
- Prefix, unused record space and following bytes remain unchanged.
- Stack, LR and the r31 nonvolatile sentinel survive the call.
- A second ordering call leaves the entire buffer byte-exactly unchanged.

Edge words include sign-bit and NaN-like float encodings. They are deliberately
treated as unsigned keys, matching the actual instructions; this does not
qualify numeric float/NaN ordering or the metric producer's live input domain.
The prior 2,269 checks pass, with the culling negatives intact. No physical,
rendering, gameplay or owner acceptance is implied.

## Reproduce and retained evidence

Use the preceding camera documents' static command. From a VS x64 shell, under
a CPU GO that explicitly permits the two leaf sorts and the owned-process route:

```powershell
python -I windows/tools/fh2_order_leaf_check.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-private-output>
```

Private root: `windows/.local/submission-state/`.

| Evidence | SHA256 |
| --- | --- |
| static02/result.json | 5031BC70EAA33DBB454A16DCAFFE8943E4998CC7DBF9AFF1A632937B44954F5C |
| runtime01/result.json | 4E7329BF44644CD645FF0B34D2610C64BD95DCD0055C3B3733FF07E14A1A5485 |
| runtime01/order-summary.json | 8137860D39E6ABB525C5CC752EA569B03A123316A6C78CFE71201881F40F3989 |
| owned01/result.json | AC6F926CC34DF6EC3D6B8E67F83EC7E311425365491743B1D209DBACAB477B93 |

GO495260 interval 2026-11-02T17:55:20Z..17:55:28Z, jobs 1 BelowNormal;
children quiescent, process query safe, lease released and literal absent.
The owned receipt remains failed for retained HOLD/exit 2, not a crash. Both
public tools refuse a wrong image before output/compile. Private image,
generated bodies, executable and receipts remain local.

No recursive sort/allocator/state emitter/staging/submission/dispatcher/worker/
scene/SDK DLL/game/window/GPU/audio/input/device/init/install/owner-state work
occurred. Native 734fff4 / SDK e223de8d remain frozen. Next source: cached-bank
consumers `82426180`/`824265F8`; resolve secondary virtual-164 receiver identity
separately. The two 54-instruction staging-copy helpers are a bounded next
offline candidate, with a fresh CPU GO needed before qualification.
