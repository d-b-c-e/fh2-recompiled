# FH2 toolkit adoption

2026-11-02 source checkpoint. Native input uses the SDK route; it is not a DBCE
input shim. Source-only planner work does not establish rendered triples.

| Standard | Title | State | Evidence / remaining work |
|---|---|---|---|
| STD-041 | Triple framing: always corrected; Game or Realistic per mounted camera | in progress | In-progress source scope: Canonical planner plus explicit offline guest matrix adapter:5,726 checks/288 actual stock matrices PASS. Runtime unit/mode choice, scene/culling and compositor not connected |
| STD-042 | Every camera's view is adjustable, remembered and named on screen | unchecked | No camera overlay, live offsets or stage-start restoration |
| STD-043 | Hotkeys wait only for their own keys; a held H-pattern gate wins | partial | Explicit GEAR8 parser -> generated reader/sampler434 checks; built-DLL existing input/FFB suites27 cases/227 assertions. Hotkey behavior and physical lever delivery still unverified |
| STD-044 | A write changes only what it owns, and keeps the file's bytes | partial | Wheel helper69 checks/24 explicit options including raw calibration; combined native734/e223 with built-DLL strings200, preservation67 and save-result18 checks PASS. Save feedback compiles; rendered UI/click/readback remains unverified |
| STD-045 | Force feedback is On by default; My Rig decides and Apply writes it | unchecked | No force default changes; physical motion/haptic safety route held |
| STD-046 | Triple cameras: a starting choice per camera, tweaks as offsets | in progress | In-progress source scope: Offline independent per-camera starts/selection/FOV offsets/reset; native camera identity/F7/persistence/placement pending |
| STD-047 | One borderless window across all screens; eye distance to the panel-edge plane | in progress | In-progress source scope: One span rectangle, edge-plane geometry, N-display/curved-slice coverage tested; no renderer/window mutation yet |
| STD-048 | Numpad + zooms in, − zooms out | unchecked | Direction specified; native keys and untouched-default migration not implemented |
| STD-049 | Cab-over vehicles: the bonnet camera sits on the roof front edge | unchecked | No FH2 car-body profile fitting or cab-over qualification |

See [scene design](docs/TRIPLE-SCENE-DESIGN-20261102.md) and the native candidate
handoff. Installation, rendering, gameplay, physical output and owner acceptance
remain separate from offline geometry/config tests.
