# Procedural instance family matches the visibility layout

The RTTI-backed `proceduralGeometry::CProceduralGeometry` family has the fields
used by the secondary-instance visibility and resolver paths. Nine direct
base-constructor callers supply concrete tables and byte-offset-164 targets.
This narrows the receiver search; it does not establish which object the game
selects at runtime or complete the resource-population chain. **CULLING HOLD.**

The current read-only trace passes **387 static checks**, scans 85,237 generated functions,
and records 171 selected function hashes. No constructor, allocator, pure-call,
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
The continuation below traces the common admission and several derived mask writers.

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

## Common admission and mask continuation

The next source checkpoint locates factory `82FAA460`. It selects among the
nine allocators, requests one object, sets backlink-like field+116, then calls
`82F95418`. That initializer enters only from ready word+48 zero, sets header+4,
calls derived virtual byte-offset 120, optionally invokes virtual148, calls
`82F83BE0`, then writes **ready word+48 = 1**. This is the missing source
transition from construction to resolver eligibility; it does not prove success
for any particular live resource.

Several derived slot-120 loaders change the constructor masks on their
population paths, before the common header mask helper:

| Type / method | Mask+68 change | Word+72 change |
| --- | --- | --- |
| Models / 82F98CF0 | OR 01000800 | OR 01000000 |
| AnimatedScene / 82F90410 | OR 01000800 | OR 10000000 |
| Characters / 82F93C00 | OR 00000800 | unchanged by this recorded sequence |
| Vegetation / 82F96D10 | OR 00000800 | unchanged by this recorded sequence |
| LightMaps / 82F86228 | clear to zero | clear to zero |

`82F83BE0` checks header floats at +8 and +12 against zero. Unless the first
compares less than zero, it ORs 00000040 into instance+68. Unless the second
compares less than zero, it ORs 0000003F into +68. These describe the actual
negative branches, including unordered comparisons; no semantic camera names
are assigned. The LightMaps clear precedes this common helper, which can add
bits again. The alternate `82F952E0` initialization route also calls that helper
before setting ready48 to one.

Resource callback `82DAA178` invokes the factory and stores a non-null result
at output+8. An image reference to this function sits in a callback/tag table;
it has **not** been established as resource virtual68. The bridge from
`8244CC30`'s actual virtual68 target to this callback, and live resolver selection,
remain open. None of these resource callbacks or mutation paths was executed.

## Typed resource population follow-up (soba, local source only)

The direct caller `82DAA3F0` supplies output=`resource+120` to `82DAA178`;
the callback's output+8 publication therefore reaches **resource+128**, agreeing
with the existing instance resolver's body pointer. RTTI identifies its table
`821547FC` as `CTrackProceduralGeometryResource`. Factory `82DAA9F0` requests136
bytes, calls the common initializer, then installs that table.

The table's **virtual60** is `82DAA3F0`. **Virtual88** is `82DA97A0`, which dispatches
virtual60 before releasing the resource reference at+64. In contrast, both
**virtual44 and virtual68** point to `83188AC0`, the exact `return0` leaf. This
rules out treating this table's optional virtual68 as the population callback:
`8244CC30` itself tests virtual44 before optionally calling virtual68. The source
population chain for this typed table is88 ->60 ->callback ->factory, not68.
No call is replayed, and no generic callback-table word is mislabeled a vtable.

Nine added RTTI/table/source guards extend378 to387 checks; three added function
hashes extend168 to171. The fresh receipt is
`windows/.local/soba-reconcile/resource-population/result.json`, SHA256
`D6FDCD3429C0DEC589FDE64E854704A245F467582E1276540138C0C9C18C3EA6`.
This is still not evidence that the live resource selected by the resolver has
this table, that its caller uses88, or that kind1 extents are suitable for another
camera. `resourcePopulationEstablished=false` and **CULLING HOLD** remain explicit.

## Evidence and next step

`windows/tools/fh2_extent_trace.py` records the family, allocator strides, base
layout, table targets and Models call sites. It publishes derived metadata and
compact instruction guards, never generated guest bodies or the title image.
Private receipt: `windows/.local/instance-receiver/admission02/result.json`, SHA256
`C043FD437BD43BF2BB4D722CDB411997427EFAA836F854A5B6907AD2A4372B88`.
The initial guard rejected the two power-of-two allocators' shift instructions;
matching their actual `rlwinm` scales resolved that guard, without changing the
source under examination.

Next establish the actual selected resource/table and the caller of virtual88
for the typed population path, plus additional participation-mask writers. A later qualified live observer
must establish the actual selected receiver and view roles. No hook, replay,
mask rewrite, production build, owner install or runtime claim is authorized by
this static result alone. The kind-1 frustum producer and culling admission
remain unresolved.

## Restart handoff - November 2

Owner reboot/update instruction495969 ends this interval after this atomic
source checkpoint. No FH2 test was launched; no vuro lease or native process
remains. Installed owner fh2.exe remains1139A7A07629AD52CAD686091CE0DC9F165F102E437BACD62C59B3739DCAD18B;
no deployment or owner rollback was performed. Private candidate734fff4/e223
remains separate. Full installed-member hashes, rollback boundaries, runtime
route, abort evidence and exact resume order are recorded in the hub's
`docs/handoffs/2026-11-02-vuro.md`.

After restart, resume the private runtime smoke first once the desktop provider
works and a fresh closed-app census confirms the owner-reported Pit House quit.
Obtain a fresh serial GO/lease from guna; old495741 cannot be reused. Preserve
all preparedattempt01 evidence. Use FFB/haptics/rumble OFF/zero and observed
foreground-guarded interaction. Then prepare a qualified read-only scene
observer build: existing734 SceneProbe is inert/unlinked. Do not claim scene
capture readiness until that observer exists. Further offline work is the
resource virtual68 bridge, live receiver/view-role evidence and kind-1 producer.
No new work or slot request begins before the restart handoff is complete.
