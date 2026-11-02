# Remaining constant-1 calls are audio and SQLite interfaces

Follow-up: [view getter and mirror consumer](VIEW-CONSUMER-20261102.md) identifies
the native mirror-transform role and independent packet symmetric-frustum
rebuilds. The latest static trace has 142 checks; culling remains held.

All seven sites in the bounded constant-1/slot-32 scan are now identified as
**non-camera paths**. The last four sites use XAPO audio configuration and
SQLite file locking. **108 static checks pass**, with no compilation or guest
execution. Actual kind-1 camera selection and CULLING HOLD remain unresolved.

## XAPO receivers: 831CA938 and 831CB410

Assignment helper `831CA678` queries an incoming object's slot 0 with the
legacy IXAPO identifier and writes the resulting interface pointer to
owner+256. `831CB908` performs the same query into owner+8. Their companion
IXAPOParameters queries write owner+260 and owner+12, respectively.

| Image address | Identifier bytes expressed as a GUID |
| --- | --- |
| 8210C350 | A90BC001-E897-E897-55E4-9E4700000000, legacy IXAPO |
| 8229EB00 | A90BC001-E897-E897-55E4-9E4700000001, legacy IXAPOParameters |

The bytes agree with [Wine's legacy XAPO interface definitions](https://github.com/wine-mirror/wine/blob/2528aff26208257fdbf980666a4f0e66d47563ce/include/xapo.idl).
The installed Windows SDK 10.0.26100.0 header has modern, different GUIDs;
its interface method shape is a cross-check, not the title's exact SDK version.

`831CA938` invokes slot 32 on both owner+256 and owner+8; `831CB410` invokes
it on owner+256. Each passes count 1, input buffer-parameter pointer, count 1,
output buffer-parameter pointer, then checks the HRESULT. Slot 36 unlocks it.
This is the [IXAPO::LockForProcess contract](https://learn.microsoft.com/en-us/windows/win32/api/xapo/nf-xapo-ixapo-lockforprocess),
not a one-argument camera kind setter. The format-pointer/frame-count pairs
also match [XAPO buffer parameters](https://learn.microsoft.com/en-us/windows/win32/api/xapo/ns-xapo-xapo_lockforprocess_parameters).
No XAPO was initialized, locked or executed during the trace.

Context7 had no matching XAPO documentation for the focused query; the
official Microsoft pages and installed header supplied the API cross-check.
The legacy identifier is checked separately, rather than substituted with the
modern Windows identifier.

## SQLite receiver: 831349B8

`83148EA8` allocates storage, sets owner+56 to its embedded file-object buffer,
and passes that buffer to the storage provider's callback at byte 24. The
provider layout and calls identify the documented version-1 prefix of
[sqlite3_vfs](https://www.sqlite.org/c3ref/vfs.html): size/path limits at +4/+8,
`xOpen` at +24, `xAccess` at +32 and `xFullPathname` at +36 on this 32-bit ABI.
The image also contains the tested `:memory:` filename at `82152E2C`.

The provider fills the embedded `sqlite3_file` and its `pMethods` pointer.
The [sqlite3_io_methods prefix](https://www.sqlite.org/c3ref/io_methods.html)
starts with an integer version word. Consequently these offsets are:

| File method-table offset | Operation in 831349B8 |
| --- | --- |
| 28 | xLock with 2, SQLITE_LOCK_RESERVED |
| 32 | xUnlock with 1, SQLITE_LOCK_SHARED |
| 36 | xCheckReservedLock with an output pointer |

The constants match SQLite's documented [file locking levels](https://www.sqlite.org/c3ref/c_lock_exclusive.html).
The numeric table-call scanner therefore also matched a C callback table; it
did not establish a C++ camera interface. This is a file-lock downgrade, not
a camera-kind update. The exact title SQLite release and concrete VFS module
are not established. Context7 and official SQLite documentation corroborate
the common interface prefix. No database, file open or lock was executed.

## Next offline item: camera factory and registered-view route

The subsequent search starts from identified camera ownership:

- RTTI tables `8225134C` (`CPresentation`) and `82003524` (its thread-safe
  refcounted wrapper) both bind slot 56 to `82F5BE50`. That function allocates
  a 528-byte camera, invokes `82F46838`, installs camera table `82002D44`,
  appends its smart pointer to the registry at owner+10104/+10108, and returns
  the registered pointer. The camera constructor's default kind remains 3.
- Both presentation tables bind slot 60 to `82F5BEE0`. It passes the incoming
  camera to `82F59C88`, which searches the registry and erases a match via
  `82FFB710`, releasing the displaced smart pointer. It also clears matching
  renderer-side references. This is camera removal, not a second factory.
- Presentation slot 28, `82F5A2C8`, forwards the same owner to the already
  traced `82F50780` initializer. That initializer creates the source-backed
  orthographic kind-2 camera; it does not select kind 1.
- RTTI `CPresentationView`, table `8200243C`, binds slot 28 to `82471158`.
  The setter resolves an incoming camera through registry lookup `82473418`
  and stores the registered reference at view+400.
- Presentation slot 72, `82F4F1D0`, also resolves a camera through `82473418`
  and invokes the actual lazy-cache builder `82408998` on it.

Registry consumer `823F46D8` examines camera+268 and passes selected camera
pointers/indices to `823F3050`, using two 288-byte renderer records starting
at renderer+55824. That helper writes record+4 and, unless record+0 equals 1,
record+8. **That record-header 1 is not camera kind+8.** These are pointer
admission facts, not cloned scene packets or demonstrated projection upload.
Two scanned records do not prove a global view-count limit.

This establishes static camera ownership and a view-assignment route. It
does not correlate a live feed-context+40 camera, prove main-scene visibility,
qualify hook ordering/ABI, or clear the projection/plane disagreement. Next
useful source work is the view's slot-32 camera getter and the resolved-camera
path from `82F4F1D0` into `82F46060`, retaining the negative culling fixture.
Variable kind arguments and copy/alias paths remain possible; the bounded
constant-1 result is not proof that kind 1 is unused.

## Reproduce and evidence

```powershell
python -I windows/tools/fh2_extent_trace.py --generated <generated/default> --image <expanded-image.bin> --out <fresh-private-output>
```

Private root: `windows/.local/kind-streams/`. Final `static03/result.json`
records 108 checks, 41 selected function hashes, 85,237 scanned functions and
an empty `remainingUnclassifiedSlot32Sites` for the original seven candidates.
SHA256: `0160ED6670B25F8CB1E556247D88C493EBC9BA85DD20A188873CFAAAF109FE41`.
Wrong-image refusal before output passes. Private source extracts, API
provenance/header hashes and legacy IDL snapshot remain in that root; no game
image or generated body is public.

This increment has no build, guest execution, CPU lease, SDK DLL, game/window,
graphics/audio/input/device initialization, installation or owner-state writes.
Prior 368 fixture assertions and 960 VMX comparisons are retained, not rerun.
Native 734fff4 / SDK e223de8d remain frozen. Culling stays HOLD.
