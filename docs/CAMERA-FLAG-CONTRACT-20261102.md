# Camera flag: native algebra, dirty state and static feed selection

Later [overwrite/consumer investigation](CAMERA-SURVIVAL-20261102.md) locates
the concrete post-write point and proves late matrix survival through the lazy
cache. Its independent containment check is **HOLD**; the native asymmetric
matrix/plane contract is not admitted from this flag algebra result.

The flag follow-up resolves all four tested asymmetric matrix branches
algebraically and finds an existing feed selecting **flag1 then symmetric
mode0**. The flag setter changes only byte272: it does **not** dirty/rebuild the
projection. This is useful native integration evidence; the selected live
receiver, flag's semantic name and GPU/culling contract remain unverified.

## Stored and queued flag

Base camera vtable8224FBDC slot80 is82F43618, a two-instruction byte store to
camera+272. Slot84 is823FF818, which returns that stored byte. Eight synthetic
input words exercise low-byte truncation/getter return while comparing all512
camera bytes: only+272 changes, including dirty480 and existing matrix bytes
remaining unchanged. Noncanonical values are ABI stress cases, not claims
that a public boolean caller normally supplies them.

Deferred slot80 wrapper82F45078 stores the low byte into payload+4 and queues
callback82F45060. That callback zero-extends the payload byte and invokes
receiver virtual80. The symmetric mode wrapper82F44CC0 instead stores a full
word atpayload+4; callback82F44CA8 loads a word and invokes virtual44. Both
paths use copied8-byte payloads. This is static payload evidence; no queue,
allocator, dispatcher or actual runtime object is executed by the oracle.

## Exact mathematical flag branches

For each row below, apply the ordinary off-axis row-vector formula from
[the API note](OFFAXIS-API-20261102.md) to the listed **effective** extents.
These are algebraic equivalents of the actual outputs, not an invented display
or mirror meaning for byte272. Depth remains near0/far1 in all finite cases.

| Mode r4 | Byte272 | Effective left/top/right/bottom | Forward axis |
| --- | --- | --- | --- |
|0 |0 |l,t,r,b |+Z |
|0 |1 |−l,−t,−r,−b |+Z |
|1 |0 |l,t,r,b |−Z |
|1 |1 |−l,t,−r,−b |−Z |

The last branch leaves top unchanged while negating bottom. Consequently,
ordinary symmetric t=−b becomes an effective zero-height interval, producing
nonfinite Y coefficients. The six existing survey cases are now explained
exactly, with remaining14 matrix coefficients still checked. They are never
projected, normalized, clamped or admitted as renderable matrices. Whether
that branch expects a different input convention or is defective in a real
consumer remains unestablished.

Mode0/flag1 negates the X/Y scales but keeps the original asymmetric offsets;
it is not equivalent to negating the complete clip X/Y coordinates. The
existing GuestProjection negateClipXY argument targets the separately verified
symmetric builder and must not be silently relabelled as this native flag.

## Static feed and overwrite boundary

In8262CC40's camera-present branch, the originalr4 flag is retained inr29.
The context+40 receiver is called through virtual80 with that flag, then
through virtual44 with an explicitr4=0. Two inspected direct callers setr4=1:

- 8262D0F0 calls camera update829C4440, then feeds8262CC40 at8262D134.
- 8262D298 calls camera update829C45D8, then feeds8262CC40 at8262D2CC.

Thus those **static call paths** choose byte1 and symmetric mode0. They do not
select asymmetric slot48. Placing an asymmetric update earlier in this path
would be overwritten by the later symmetric call. For a deferred receiver,
integration must also preserve actual payload/consumer ordering; a mutable
host global cannot carry per-view identity through the queue.

This does not prove which class context+40 holds at runtime, that these callers
run in a selected scene, or that every game camera has these choices. In
particular, the existence of the nonfinite mode1/flag1 survey branch does not
prove that the inspected normal feed uses it. The future read-only capture
must correlate receiver/vtable, flag/mode/kind and matrix/depth/culling state.

## Reproduce and evidence

The existing `windows/tools/fh2_offaxis_oracle.py` command now verifies5 base
vtable words,7 selected actual image instruction words and7 static function
bodies/selected sequences. It executes only the4 actual pure setter/getter/
builder bodies on synthetic memory, with the same pinned image734/e223 headers.
No dispatcher/math callee is mocked; static traced functions are not executed.

- **4,656 algebra/corner/depth checks PASS**: all120 branch cases,114 finite
  matrices,96 coefficient/classification checks for the6 nonfinite matrices.
  Retains the original2,400 byte272=0 checks and adds2,256 for flag1 branches.
  Five extent rectangles,3 clip ranges, both FP policies and both modes.
- **8 full-object flag setter/getter state cases PASS**, plus existing per-case
  extent setter, kind/mode/dirty, pose64bytes and SP assertions.
- Wrong-image control refuses before compilation/output creation. No native
  app/SDK rebuild or linked hook; the small standalone compile loads no SDK DLL
  and maps the image only as nonexecutable data.
- Private `windows/.local/camera-flag/run01/oracle.json` records hashes, selected
  image words, executed/static function identities and all numeric bits. SHA256
  `D66A7D28AD01D508F8D686188F2A46586D138559A7B0154EF91E65FD594A65EE`.

Native734/e223/private payload, managed adapter and toolkit remain unchanged.
No game/window/GPU/input/device initialization, owner write, install or lease.
Scene replay/culling/resources, runtime depth state and physical acceptance
remain open. The flag's algebra being understood does not admit those gates.
