# FH2 Windows combined candidate - November 2, 2026

The corrected combined candidate now builds and passes its offline checks.
Nothing was installed or launched. Physical motion/haptic safety qualification
remains held; live gameplay, device behavior and owner acceptance are unverified.

## Exact source and outcome

- Compiled app: `6c49f9cdf1bebc188740fe47bf95ee4aabc735de`, based on
  `1a63fe41cacaeb9107a0701ef9a55c340a34f8f6`.
- SDK gitlink: `499e0579b2e8a52f68b99748198816be7217ecee`. This is the
  corrected endian-capability source, retaining the focus/garage ancestors.
- The app retains gear-read refusal, reverse-above-15-mph guard and finite Data
  Out work. The new production change recovers Windows' machine
  `PROCESSOR_ARCHITECTURE` only when absent from the build process environment.
- Helper source `0ffe8eed6ec6477860682c2e4915d46492a2003b` was integrated after
  the build stopped. It adds no compiled code or SDK change. Later README and
  handoff edits likewise do not change the compiled pair.
- Public source branch: `vuro/fh2-overnight-20261102`. App main was not promoted.
  No game data, expanded image, generated guest code or binaries were pushed.

The SDK commit is local source, not a claim of publication to its third-party
remote. The preserved private source bundle is
`E:/Source/dbce-project-mgmt/artifacts/fh2-haptic-endian-femi-20261023/sdk-source.bundle`,
SHA-256 `16CE729390FF679151BD9755389686796DB85E179E1BB518FCBD10C21B042EC9`;
it requires base SDK `59bc11f546a6ea67eefcad974d0c14041b2ab20d`.

## Checks and custody

- Production endian capability header/fake-device fixture passes. The earlier
  integer stand-in was not used.
- All eight disc instruction checks pass. Existing three XEX inputs and retained
  generated baselines match the October 23 recipe.
- First build stopped at CMake configure because the process architecture
  variable was empty. Its failed receipt/logs are retained separately.
- Three focused build-driver checks pass: missing-variable fallback, actual
  pinned CMake 3.31 architecture detection, and existing-value preservation.
- Second build passes configure, real codegen (722 files, 196.3 seconds), native
  compile/link, and fresh generated semantic checks. Gear fixture: 689 production
  checks, zero failures, plus negative controls reproducing the refused-read
  hazard. Reverse guard: 46 checks, zero failures. Finite telemetry: 65 checks,
  zero failures. These do not prove live gear/vehicle behavior or UDP packets.
- The [settings helper](WHEEL-SETUP-20261102.md) passes 42 inert-file checks and
  matches 15 SDK option names/types/ranges. SDK SaveConfig string escaping is a
  documented remaining caveat; no runtime round-trip claim is made.
- Guna GO `490917`, named operator `vuro`, native/Cargo jobs 2. Completed
  `2026-11-02T06:41:36Z`; all owned children quiescent, process queries safe,
  lease released and literal lease token absent. No game/device/owner install.

## Private output and evidence

Build tree (detached at the compiled app):
`E:/Source/game-modding/.worktrees/vuro-fh2-buildenv-20261102`.
Its `windows/out/build/win-amd64-release/` produced:

| Member | SHA-256 |
| --- | --- |
| `fh2.exe` | `C8AD02C66CAA4309CB6FF2B04BE80AE18A0F6943EC20C80FAE8D31A7AEEC653A` |
| `rexruntime.dll` | `FD12AEA39E8A1DC5BED5A4B3FEA39AB24C9ECA14E458A8CDDB3E66C782AE939F` |
| `rexgpu-fh1.dll` | `754856CE0C493D53190646CAFB3E0167F0B9EF169F197407E956A429C61208A2` |
| `fh2_XMediaFacade_default.dll` | `A22DF848531CA50E99D4419D0C6C7187B06B4AACD647373F27710248DA19A13B` |
| `fh2_SpeechFacade_default.dll` | `2DF9220BD908AE34EF70544D60370E4A6F5852D1C879A71ABE68994B4B174F1F` |

Evidence root:
`E:/Source/game-modding/.worktrees/vuro-fh2-overnight-20261102/.local/vuro-20261102/`.
Retain `build-01/`, `architecture-check/`, `build-02/result.json`, runners,
input manifests, tool-refresh record, SDK source and recovered baselines.
Final build receipt SHA-256:
`55A2842A6ACDAC584070C0FAE2C0E2B27FF772D55AF7DC34F06875C2E0899F93`.

`private-payload/bin/` contains the matching five binaries and four existing
upscaler files including their licenses. The established private staging recipe
was reused with only its two source pins changed; PlanOnly, copy and post-copy
verification passed. `private-payload-receipt.json` records the copy. No game data,
launcher, saves or owner config were copied; this is not a complete game package.

## Image dump, installed baseline and next action

Follow-up source: [SDK string serialization patch](../windows/patches/README.md),
local SDK successor `bddeb1670c2b6890795653076880dc1b9196b7a5`, fixes escaping
in all three TOML writers. Actual production-cvar fixtures reproduce base499's
parse failure and pass 200 checks with the fix, including real SaveConfig/LoadConfig
on inert project files. The patch applies cleanly to499; its exact source bundle
is retained privately. No SDK remote push was made. This follow-up is not in the
compiled DLL or app gitlink, which remain499; next full-build integration needs
a separate tree and fresh CPU slot. Preserve the passing payload above.

The existing offline image route remains
`windows/tools/Test-DiscRevision.ps1 -Xex <default.xex> -ImageOut <private-path>`.
Expanded image SHA-256:
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`.
Keep the image private and ignored. The existing extracted game root remains
`E:/Source/game-modding/dbce-mods-forza-horizon-2.wt-sync/assets/game_root`.

Owner installation remains untouched at
`E:/Source/toolkits/launchbox/Launchbox-Racing/Games/Windows/Forza Horizon 2 (Native)/bin/fh2.exe`,
SHA-256 `1139A7A07629AD52CAD686091CE0DC9F165F102E437BACD62C59B3739DCAD18B`
(October 16; upstream version unestablished). Preserve its config/user/logs and
all earlier candidate/rollback artifacts. The dirty upstream-sync SDK was not
altered. This source/build-only increment needs no owner rollback.

Before any agent live run: qualify the physical output safety route, obtain a
fresh serial GO and named lease, use the existing private launch/cleanup route,
and preserve exact owner state. Installation, rendered UI, gameplay, reverse
behavior, live telemetry, wheel force/focus-loss stop and owner acceptance each
remain separate gates. Single-process true triples remain unimplemented;
existing multiscreen traces describe linked instances.
