# FH2 scene cut: static result and next capture

Task Vemi491724. **The proposed singleton/vtable hook is audio. No safe
once-simulated three-view scene replay is established.** This investigation
instead identifies the camera-to-presentation and visibility-packet boundaries,
excludes unsafe loops, and supplies an inert probe and a bounded future capture
plan. No game, graphics device, display, input, installation or owner file was
accessed by execution. Reading the private title image is static analysis.

## Reproducible source evidence

Title v0.0.0.6, media15E4FA3D. Expanded image base82000000, size24,117,248,
SHA256 `3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`.
Private XEX SHA256
`DBBE28A8023B1A39DD9ADBBC3CF38EC0D5DC26D85AEEF056A6005AD17BBBD684`.
Qualified generated code is in the app7ce460f/SDKbddeb167 worktree,
`E:/Source/game-modding/.worktrees/vuro-fh2-s3-20261102/windows/generated/default`.
Never publish the image or generated guest code. Function partition numbers are
unstable; use guest addresses and verified image identity.

`windows/tools/Trace-Fh2Scene.py` refuses a different image hash and verifies
18 named generated function records, their selected direct edges/instructions,
10 actual big-endian vtable slots and two embedded FMOD paths. It emits hashes,
addresses and call metadata, without game bytes or generated source. Run from
the triples worktree:

```powershell
python -I windows/tools/Trace-Fh2Scene.py --image windows/.local/triples/fh2-image.bin --generated E:/Source/game-modding/.worktrees/vuro-fh2-s3-20261102/windows/generated/default --output windows/.local/triples/scene-static.json
g++ -std=c++17 -Wall -Wextra -Werror -O2 windows/triples/probe/SceneProbe.Tests.cpp -o windows/.local/triples/scene-probe-tests.exe
./windows/.local/triples/scene-probe-tests.exe
```

Both checks pass. Probe fixtures cover guest big-endian words, exact context and
packet fields, bounds/overflow refusal, unchanged output on partial failure and
no guest writes. This proves the adapter contract against synthetic memory;
it does not prove native hook registration, scheduling, GPU identity or runtime
receiver classes. Existing534 geometry/config checks remain separate evidence.

REA6.3.0 doctor found no usable native provider (no Hopper/Ghidra/IDA and client
configuration drift). No repair/configuration/engine install was performed.
Fallback was private generated PPC comments plus expanded-image words/RTTI and
installed Capstone5.0.7. Private doctor/image/static receipts live under
`windows/.local/triples/`. These limitations do not make speculative labels facts.

## Corrected call graph and state effects

All numbers below are guest virtual addresses or decimal byte offsets. A
direct edge is distinct from a virtual target established by a table read;
runtime receiver selection still needs confirmation.

| Boundary | Observed path and state | Replay implication |
| --- | --- | --- |
| Camera update |829C4440/829C45D8 call829C16F8,829C11C8,829C13D8.829C11C8 computes camera and ends with audio.829C16F8 includes camera/input/time state. | Keep selected update once.829C13D8's target meaning is unresolved; do not label it rendering. |
| Audio |83598C0C constructed by82D3BF80/82D3B430, primary table82149134. Slot48=82D305F0 ->83032690 -> event table822648A8+228=8303F550 ->8306EC68 ->830757F8. Event/core factories reference fmod_eventi.cpp82264650 and fmod.cpp8226596C. | Four112-byte records at+20896, count+21344, count setter830757D0 range1..4 are FMOD listeners. Exclude from graphics. |
| Camera feed |8262CC40 takes context r3. Camera=context+8; matrix829BAC58 returns camera+240; FOV829BAC60 reads+304. Calls context+40 interface slots168(matrix),56(FOV multiplied by57.295776 at82005910),68(aspect),196(clips). Resets camera byte167. | Useful observation boundary; not pure, and runtime interface factory needs confirmation. |
| Deferred camera |RTTI CPresentationCameraDeferred table8224FE8C, subobject offset8. Slot168=82F45590 copies64-byte pose to queued80-byte payload, callback82F45528. Slot56=82F44E58 queues FOV, callback82F44E40. Dispatcher824051A0. | Queue owns copied data; changing a host global after enqueue cannot supply per-draw identity. Table match alone does not prove context+40's runtime type. |
| Base camera |CPresentationCamera table8224FBDC. Pose823FBA80 writes+16..79; FOV82F435F8 writes+260 degrees; aspect82F43608 writes+256; clips823F3068 write+208/+212. Dirty byte+480.82F46988 builds symmetric projection at+80..143 using these fields. | An asymmetric matrix also needs coherent derived/culling state; merely replacing+80 is insufficient proof. |
| Snapshot recorder |8262CC40 ->82F467E0 on singleton835FFE44: two128-byte records, index+1776 and dirty+130. | Recorder, not a draw call or renderer. |
| View preparation |CPresentationView table8200243C slot48=82F5CA60 ->82F5C5B0 ->82F5AF30(view,packet pointer loaded from view+1064,1,1). Slot44=8245E918. Deferred view table8224FD84+48=82F46C60 queues callback82F44598; +44=82F46BE0 queues82F478A0. |82F5CA60 changes temporal byte470, may drain82FA5410 and clean82EE9E60.8245E918 is a932-instruction shared-state orchestrator, not an isolated scene-only cut. |
| Packet publication |82F5AF30 builds a packet larger than14KB, retains resources, selects frame/slot state, changes view+896/+1068, sets packet bytes14033=1/14034=0 and signals packet+14012 via82D88228. | Repeating publication races ownership/events and shared state. Packet is not safely cloneable by memcpy. |
| Packet worker |82F562E8 ->82F53D60 waits on+14012, handles optional work+14028, calls82F4D818(packet,1), sets+14034 and signals+14016/+14020. Stop flag+14032; paired workers use344-byte blocks at+14036/+14380. | This is synchronized work, not a safe injected3x loop. No waits may be added inside the observer. |
| Camera-derived work |82F4D818 derives camera records from80-byte entries at packet+9120..9124, index+9136, prepares up to six camera-derived records, then82EF12D0.823FB1B0 builds plane/vector data using trigonometry;82F42C50 adds distance/FOV data. | Visibility-related preparation is established; six derived records must not be relabelled main/left/right views. Exact record roles remain unproven. |
| Visibility work |82EF12D0 clears/modifies resource bits and dispatches two worker groups or calls82450DE8 directly.824827F8 is the waiting worker that also calls82450DE8.82450DE8 walks resource arrays13848/13852/13856/13860 and calls8244F4A0,8244EF48,824501A0,824510B8. | Candidate place to observe main/mirror/shadow visibility ownership. Not proven scene draw; shared resource/list writes prohibit blind replay. |
| GPU/post/present |SDK draw packet decoder ->Vulkan IssueDrawImpl ->CmdVkDraw/Indexed. XE_SWAP ->IssueSwap/IssueSwapImpl and final fullscreen composite ->presenter. fh1_camera.cpp observes shader constants heuristically. | These are after guest visibility; replaying draw packets cannot recover culled side geometry. Present/post boundary cannot establish HUD partition or a scene cut. |

RTTI lookup uses MSVC TypeDescriptor, CompleteObjectLocator and actual table
references, with valid code pointers.825ED3D8's static singleton8342BBEC is
**CPlayerManager@Forza2**, not a renderer. It must not become the new guessed
scene manager. The true factory chain from context+4 virtual56 to context+40
remains a runtime receiver question. CRenderAdapterLink is likewise unproven
for this receiver; a matching slot number is not type evidence.

## Minimal inert probe

`windows/triples/probe/SceneProbe.hpp` accepts a caller-supplied nonfaulting,
bounds-checked reader and captures five big-endian words. It neither registers
a hook nor calls guest code, writes memory, allocates heap storage, waits or opens files.
CameraFeed expects context r3 at8262CC40; PacketReady expects packet r4 at the
**successful exit** of82F5AF30 (the integration must preserve entry r4), and
VisibilityWork expects packet r3 at82450DE8. The observer sequence orders
records only; it is deliberately not presented as frame/view/GPU identity.
The eventual integration must reject unmapped addresses, use a bounded
nonblocking buffer with dropped-record counts, and copy only while the owning
thread has valid object lifetime. This stub is not linked into the native app.

## Exact future owner capture plan

Current assignment expressly forbids game/device/install launches. This plan
requires a later authorized runtime interval and the existing qualified
FFB/motion mute, rig lease, disposable runtime and byte-restoration route. It
does not authorize that interval or remove the held physical-safety gate.

1. Use app7ce460f/SDKbddeb167 plus a separately identified diagnostic build;
   hash executable/DLLs/XEX and retain baseline. Use a disposable runtime home,
   fixed existing display topology and owner-chosen known solo scene. No
   installation change. Capture120 completed XE_SWAPs or60 seconds, whichever
   comes first; stop at16MiB of metadata. No input during capture.
2. Install read-only entry/exit observations by verified guest address (never
   edit generated partitions). Record guest thread id, timestamp, caller/LR,
   receiver, actual receiver vtable, observer sequence and host command-batch
   sequence. At8262CC40 record context+8/+40, those vtables, camera+240 matrix
   and+304 FOV, and count selected829C4440/45D8 updates. Confirm the dynamic
   camera class before claiming the static table path is active.
3. At deferred camera dispatcher824051A0 record only the two selected callback
   ids, receiver and copied payload hash. Observe callback entry and base pose,
   FOV, aspect and clip setters. Correlate producer/consumer ordering using an
   explicit diagnostic queue record id, not a changing CPU-global camera id.
4. At82F5AF30 entry/exit retain view r3 and packet r4; collect slot/index+28,
   camera entry span/index9120/9124/9136, dirty/stop flags14032..14034 and event
   object addresses14012/14016/14020. Observe worker82F53D60,82F4D818,
   82EF12D0 and82450DE8 including thread/caller and packet identity. Hash owned
   camera/plane blocks before/after; do not dump whole object heaps or dereference
   freed resource arrays. Count workers and establish lifetime through exit.
5. Observe view slots44/48 and their actual virtual callees. Add bounded
   caller/receiver breadcrumbs around *that actual* slot44 call tree to locate
   transitions into scene submissions, HUD, post and present. Correlate guest
   shader/target/viewport and command-batch ids through GPU draw/resolve/swap
   decoding. A target or shader heuristic alone does not classify a HUD pass.
   Match the normal scene and HUD submissions in the one-window capture before
   proposing a split. No matrix replacement or extra traversal in this run.
6. The trace must identify which camera/planes feed each main visibility job,
   where its draw list is consumed, and a callable interval excluding simulation,
   audio, global cleanup, mirrors/shadows, shared temporal updates, HUD and
   present. Document state/resource ownership and restoration for that interval.
   If one interval does not exist, implement explicit phases rather than
   looping a mixed entry point. Per-view temporal/color/depth ownership and
   GPU-ordered view markers remain required before any three-view experiment.
7. Stop the owned diagnostic process, drain logs, restore and hash affected
   state/topology, verify owned children quiescent, and release the lease only
   after restoration. Retain hashes, metadata and dropped-record count under
   the FH2 project. A complete trace is still not rendered triple-screen or
   physical-device acceptance.

This is the next blocking evidence for native triples. Offline planner/config
work is complete enough to feed that later integration; no enabled game toggle,
window-span install or rendered claim should be added from this static result.
