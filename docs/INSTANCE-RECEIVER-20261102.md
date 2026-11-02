# Procedural instance family matches the visibility layout

The RTTI-backed `proceduralGeometry::CProceduralGeometry` family has the fields
used by the secondary-instance visibility and resolver paths. Nine direct
base-constructor callers supply concrete tables and byte-offset-164 targets.
This narrows the receiver search; it does not establish which object the game
selects at runtime or complete the resource-population chain. **CULLING HOLD.**

The read-only trace passes **349 static checks**, scans 85,237 generated functions,
and records 156 selected function hashes. No constructor, allocator, pure-call,
virtual method, renderer or GPU submission was executed. The previously qualified
9,037 closed-helper checks and their projection/AABB failures are retained,
not rerun. Frozen native `734fff4` / SDK `e223de8d` remains unchanged.

## Base layout and admission

Constructor `82FA5238` installs table `82252A5C`, named
`.?AVCProceduralGeometry@proceduralGeometry@@`. It initializes word+48 to zero,
byte+64 to one, word+72 to zero, the 32 visibility bytes at +76..107 to zero,
count+108 to zero and backlink+120 to zero. These agree with the earlier
`EEE8` mask+68, `DFA8` word+72, `EF08` visibility-byte/count and `F418` backlink
uses. Agreement is source evidence, not proof that every resolved instance is
one of these nine types.

The base initializes mask+68 to **512**, the bit for view ID 9. It does not
identify view 9 as the main/player camera. Initialization or later writers can
change the mask. Word+48 starts at zero, so construction alone fails the
`8244EBD8` admission requirement (`word48 == 1 && byte64 != 0`). The nine derived
constructors do not themselves admit the instance by setting that word to one.
The initializers and later admission/mask writers still need tracing.

The base's byte-offset-164 target is `82C01010`, a pure-call/fatal path; it is
excluded from execution. Its table ends before the next locator rather than
crossing into the unrelated table excluded in the preceding investigation.

## Derived constructors and dispatch

Addresses are guest addresses; method offsets are bytes. Array allocators call
`82F83990`, loop over the named constructor and advance by the listed stride.
These are source-derived allocation strides, not observed live object sizes.
All types below are in `proceduralGeometry`.

| Type | Constructor | Table | Allocator | Stride | Method +164 |
| --- | --- | --- | --- | --- | --- |
| CProceduralCharacters | 82FA92B0 | 8200267C | 82FA9718 | 160 | 8246A250 |
| CProceduralPoints | 82FA8378 | 82252BBC | 82FA8898 | 168 | 82F86A58 |
| CProceduralAnimatedScene | 82FA9110 | 820027DC | 82FA97B8 | 204 | 8240DF10 |
| CProceduralLightGlows | 82FA8190 | 820029EC | 82FA8938 | 152 | 82F9DE68 |
| CProceduralAnimatedObject | 82FA9080 | 8200272C | 82FA9768 | 196 | 82692020 |
| CProceduralModels | 82FA85B0 | 8200293C | 82FA89D8 | 512 | 824279C0 |
| CProceduralVegetation | 82FA8478 | 8200288C | 82FA88E8 | 172 | 824234D0 |
| CProceduralLightMaps | 82FA82D0 | 82252B0C | 82FA8988 | 128 | 82692020 |
| CProceduralBillboards | 82FA91B0 | 82252C6C | 82FA96C8 | 168 | 82F93968 |

`CProceduralAnimatedObject` and `CProceduralLightMaps` share `82692020`, which
returns without work. `82F12860`, used by several table gates, returns one.
The table identities and offsets are pinned independently through the image's
RTTI and dispatch words; generic gate results do not prove runtime admission.

`CProceduralModels` method `824279C0` reaches `82445BF0` at two call sites and
`8245FAE8` / `82426E60` later in its traversal. It therefore connects this typed
family to the previously traced staging and dirty-bank dispatch pipeline.
This 1,252-instruction method also traverses properties/resources and performs
other calls. It is not admitted as a closed or replay-safe fixture, and this
connection does not identify a GPU projection block.

## Evidence and next step

`windows/tools/fh2_extent_trace.py` records the family, allocator strides, base
layout, table targets and Models call sites. It publishes derived metadata and
compact instruction guards, never generated guest bodies or the title image.
Private receipt: `windows/.local/instance-receiver/static02/result.json`, SHA256
`18424B65D360D8BB1FBFF1EFDB4369917A0B00F02F391B2ACE15D7029FC4CFAE`.
The initial guard rejected the two power-of-two allocators' shift instructions;
matching their actual `rlwinm` scales resolved that guard, without changing the
source under examination.

Next trace the resource virtual-68 population path and the family initializers
that set ready word+48 and participation mask+68. A later qualified live observer
must establish the actual selected receiver and view roles. No hook, replay,
mask rewrite, production build, owner install or runtime claim is authorized by
this static result alone. The kind-1 frustum producer and culling admission
remain unresolved.
