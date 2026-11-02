# FH2 toolkit adoption

2026-11-02 source checkpoint. Native input uses the SDK route; it is not a DBCE
input shim. Source-only planner work does not establish rendered triples.

| Standard | State | Evidence / remaining work |
| --- | --- | --- |
| STD-041 | in progress | Canonical planner plus explicit offline guest matrix adapter:5,726 checks/288 actual stock matrices PASS. Runtime unit/mode choice, scene/culling and compositor not connected |
| STD-042 | unchecked | No camera overlay, live offsets or stage-start restoration |
| STD-043 | partial | Explicit GEAR8 parser -> generated reader/sampler434 checks; newly built SDK. Hotkey behavior and physical lever delivery still unverified |
| STD-044 | partial | Wheel helper42; combined native734/e223 with built-DLL strings200, preservation67 and save-result18 checks PASS. Save feedback compiles; rendered UI/click/readback remains unverified |
| STD-045 | unchecked | No force default changes; physical motion/haptic safety route held |
| STD-046 | in progress | Offline independent per-camera starts/selection/FOV offsets/reset; native camera identity/F7/persistence/placement pending |
| STD-047 | in progress | One span rectangle, edge-plane geometry, N-display/curved-slice coverage tested; no renderer/window mutation yet |
| STD-048 | unchecked | Direction specified; native keys and untouched-default migration not implemented |
| STD-049 | unchecked | No FH2 car-body profile fitting or cab-over qualification |

See [scene design](docs/TRIPLE-SCENE-DESIGN-20261102.md) and the native candidate
handoff. Installation, rendering, gameplay, physical output and owner acceptance
remain separate from offline geometry/config tests.
