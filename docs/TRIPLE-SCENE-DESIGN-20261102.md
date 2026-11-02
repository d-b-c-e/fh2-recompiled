# FH2: three views in one spanning window

Source baseline: app7ce460f / SDKbddeb167, qualified offline; no game/device or
display launch. This design starts the new renderer, not a claim that it exists.
Main helper integration is b208452; main still uses older SDK1e8968f. Preserve
the separate qualified native candidate and both private payloads.

**Static correction during the follow-up trace:** singleton0x83588C0C and its
vtable+48 are the FMOD audio/listener path, not the scene view manager. The
camera-update function also computes camera state, but its final virtual call
must not be repeated as a render hook. Vtable0x82149134+48 resolves82D305F0,
which reaches FMOD event/core factories with embedded source paths
`..\src\fmod_eventi.cpp` (image82264650) and `..\src\fmod.cpp` (8226596C).
The downstream four112-byte records and count field are audio listeners. This
supersedes the view-manager inference in the older sync-branch multiscreen
trace and in the first revision of this design. Scene cut investigation is
continuing from the camera data and actual render submission separately.

Follow-up [scene-cut trace](SCENE-CUT-TRACE-20261102.md) identifies the actual
presentation-camera queue and synchronized visibility packet workers, with
reproducible static checks, an inert probe and exact future capture plan. No
mixed view/worker entry point is yet proven safe to repeat for three views.

## Presentation and geometry

One borderless window covers the row's desktop rectangle. Surround and separate
Windows displays use this same path; no per-display game windows or linked
instances. One desktop swap presents all views. Physical geometry comes from
the pinned dbce-triple-screen-toolkit RigDefinition/RigPlanner APIs. Eye distance
is to the center display's edge plane; never subtract sagitta. Use physical
RigSlice pixel rectangles, independent left/right folds and actual panel sizes.
Curved slices retain their measured-eye warp, with WithSourceOn for a virtual
Game-FOV eye. A wide single image is not three views.

STD041-049: always correct angles/curves; starting sets cockpit Realistic,
bonnet Game, bumper Realistic, chase Game. F7 selection and FOV/position offsets
belong to each camera/set. Single-screen keeps game framing. Wider than seat-true
stretches the sides even when seams agree. Mounted starts and 5cm near clip need
FH2-specific geometry and rig checks; Art's values are not silently adopted as
measured FH2 placement. No new FFB default/output change accompanies this work.

## Located consumer path

Generated code is private evidence under the qualified tree's
windows/generated/default; addresses below are title v0.0.0.6. Do not publish
generated guest source or the expanded image.

| Boundary | Observed source | Meaning / limitation |
| --- | --- | --- |
| App setup | windows/src/main.cpp, Fh2App::OnPreSetup/OnPostSetup | Existing input/telemetry/capture lifecycle; no scene callback or triple renderer |
| Camera update | sub_829C11C8, called by sub_829C4440 and sub_829C45D8 | Updates camera state then calls sub_829BE688; calling this whole update three times would also repeat camera smoothing/state |
| Linked-console camera adjustment | sub_829BE688, prior docs/multiscreen-trace.md | Conditional yaw/FOV adjustment for one console, not a scene/render-loop multiplier |
| Audio listener submission | tail of sub_829C11C8, return0x829C13C4 | Singleton0x83588C0C/vtable+48 ->82D305F0; r4=0 and four SIMD vectors reach FMOD listener state, not a scene traversal |
| Audio manager construction | sub_82D3BF80 | Allocates24400 bytes, calls82D3B430, stores singleton0x83588C0C; vtable+972 ->82D3EFE8 initializes FMOD event/core handles |
| Draw packet dispatch | SDK src/graphics/command_processor.cpp, draw packet path | Guest draw/resolve packets arrive after guest-side visibility selection |
| Vulkan draw | SDK src/graphics/vulkan/command_processor.cpp, IssueDraw/IssueDrawImpl | Prepares FH1 targets, then CmdVkDraw/CmdVkDrawIndexed; not an engine scene traversal |
| Camera observation | SDK src/graphics/vulkan/fh1_camera.cpp, NoteCameraDraw/FinishCameraFrame | Tracks WVP c128-c131 and car c0-c3 for temporal work; heuristic/delayed observation is not authoritative camera ownership |
| Guest frame boundary | CommandProcessor::ExecutePacketType3_XE_SWAP | Records IssueSwap then increments observation_frame_sequence; command batches are asynchronous |
| Native presentation | VulkanCommandProcessor::IssueSwap/IssueSwapImpl | Resolves/postprocesses current frame and submits one presenter image; final full-screen draw is not extra scene views |
| Window | SDK src/ui/window_sdl.cpp; Window::SetFullscreen | Existing single SDL window; spanning bounds/borderless policy still need an explicit adapter |

Static evidence source: E:/Source/game-modding/.worktrees/vuro-fh2-s3-20261102.
Generated function/file numbering is not stable across codegen. Find functions
by name; do not patch generated C++ or use file-number-based hooks.

## How to issue three views in one frame

1. Advance game simulation and selected camera once. At a scene-only render cut,
   capture the resulting camera pose/FOV, not a previous-frame SDK heuristic.
2. Build the complete measured rig plan and selected camera's framing. Preserve
   physical slice identities/warp when moving the source onto the virtual rig.
   Offsets apply on that calculated start. Do not alter stored physical data.
3. For left/center/right (or each curve slice), supply its view/projection and
   culling planes to the guest scene render traversal. Keep one simulation epoch,
   recompute visibility per view, and restore guest camera/render state afterward.
   Never run the entire game update three times. Main-view temporal state must
   not bleed into mirrors, shadow maps, cubemaps or screen-space effects.
4. Emit ordered view begin/end identity in the GPU command stream so the SDK's
   asynchronous recorder/executor sees the right frame/view. A mutable host
   global changed by the game thread is insufficient. Partition main scene color,
   depth, resolves and temporal history by frame/view; shared resource decisions
   require proof. Complete each view before its targets are reused.
5. At one XE_SWAP, composite completed view images into RigSlice.Pixels, apply
   each curved warp, draw the HUD once using an explicit center/full-span policy,
   and present once. Incomplete/mismatched view sets must not masquerade as a
   complete triple frame. Restore original single-view behavior when disabled.

**Unresolved integration cut:** vtable+48 is now resolved and excluded as audio.
Follow the camera data to the actual scene visibility/render submission; the
FMOD listener count is not a render-view count. Find the scene-only traversal
and its side effects. No existing function is asserted safe
to loop until this is established. The offline planner/config/fixtures can be
completed independently; a draw-replay shortcut cannot close this gap.

## First offline implementation

Implement a small renderer-independent consumer that calls RigDefinition and
RigPlanner directly, with pinned vendored core source rather than a mandatory
private checkout. Raw rig configuration and per-camera starting sets are the
input; derived view bounds/bases, pixel rectangles and warp grids are transient
output. Reject malformed/unknown configuration versions and nonfinite geometry.
Do not write owner settings or add an enabled game toggle before a live consumer
exists. Test edge-plane distance, seams, unequal angles, flat/curved slices,
Game/Realistic defaults and independent camera/set state, invalid input and
output coverage. This is geometry/config evidence, not rendered triples.

Native host integration must subsequently consume those same plans with explicit
guest matrix layout, handedness, depth range, jitter and unit conversions. The
SDK's Vulkan viewport alone does not establish these conventions. A managed
offline consumer is not a new runtime CLR dependency or a claim of a connected
native renderer. Final renderer admission needs separate source/build evidence
and owner-authorized rendered qualification after the physical safety route.
