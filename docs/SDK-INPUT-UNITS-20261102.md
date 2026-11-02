# FH2 SDK input and force math: existing suites through the built DLL

The qualified SDK runtime passes **27 existing Catch2 cases /227 assertions**
from wheel mapping, wheel shaping and XInputdFF descriptor suites. No replacement
production implementation was linked into the fixture. This adds a real
compiled-component check behind the held physical route; it does not establish
SDL polling, haptic effect creation/playback, force direction or physical feel.

## Scope and reproduction

Use the qualified e223 SDK checkout, its initialized pinnedCatch2 source and
its newly built `out/win-amd64/rexruntime.dll`/import library in an x64 VS shell:

```powershell
python -I windows/tools/fh2_sdk_input_units.py --sdk <qualified-sdk> --cxx <clang++.exe> --runtime-sha256 7708F5FD2F29D2200E67651042836607ABDB0975ED274F69C71A1E2D35865C80 --out <fresh-project-output>
```

The tool compiles the vendored realCatch2 amalgamation and these unmodified
existing test translation units, sequentially through one compiler driver:

- tests/unit/input/wheel_mapping_test.cpp
- tests/unit/input/wheel_test.cpp
- tests/unit/input/xinputd_ffb_test.cpp

A private modular-header forwarding include points to the actual amalgamated
Catch2 header. Assertions and test registration are not mocked or rewritten.
Only the original rexruntime import library supplies SDK functions; no SDK
production.cpp file or SDL driver is compiled into the fixture.

These audited suites cover parser selectors/GEAR8, steering/pedal shaping,
motor modes/signed centering, force magnitude/gain/minimum/condition scaling,
big-endian descriptors/type ordinals, and in-memory wheel GUID lists. The GUID
test changes only process-local cvars and never calls SaveConfig. GetSink
remains null; no output sink is registered and no SDL/input/haptic startup or
driver effect method is invoked. This scope applies to the recordede223 test
sources; recheck their contents when changing SDK versions.

JUnit records227 assertions,27 case elements,0 failures/errors/skips, seed1.
The distinction matters: the JUnit tests attribute here counts assertions.
The tool records the literal attributes and separately counts case elements.
LLVM confirms direct rexruntime imports plus Windows/MSVC/CRT imports for the
fixture, with no direct SDL import. This does not claim the DLL has no SDL code.
The DLL copy and original hashes both match the required identity after tests.
Wrong-runtime-hash control refuses before compilation/output creation/DLL load.

## Evidence and custody

- Exact app734fff4/SDKe223 native runtime SHA256
  `7708F5FD2F29D2200E67651042836607ABDB0975ED274F69C71A1E2D35865C80`.
- Private fixture root `windows/.local/sdk-input-units/runtime01`: actual
  compiler command, all test/header/Catch2/runtime hashes, compile log, JUnit,
  LLVM imports and output identities. `result.json` SHA256
  `3DF2AAF41DD49BB86D3693405632AA7ACBD255550E47063543A774CDCA9D39C4`.
- Fixture executable SHA256
  `9C12CC27931BDE59F5CFD7B6C06A01382DBF3254135ED584BC3FA2DB8DE715DE`.
- Guna GO493171, jobs1, operatorvuro. Existing pinned Rig-Lease/OwnedProcess
  route, BelowNormal priority, bounded compile/worker deadlines. Interval
  2026-11-02T11:47:44Z..11:48:02Z; all owned children quiescent, safe process
  census, lease released and literal token absent. No custody remains.
- Private owned receipt `windows/.local/sdk-input-units/owned01/result.json`
  SHA256 `D762C15D0693E26BB8D52CA8D56B8CDF6EE2361742EB02C8B29A5ADA546070F0`.
  Exact worker/runner retained alongside it. No full SDK unit target was built.

No app/SDK rebuild, game/window/GPU/audio/input/physical device initialization,
installation, owner-state or display change occurred. Existing native734/e223
and nine-file payload remain unchanged. The physical mute/restore route stays
held; arithmetic passing cannot admit it.
