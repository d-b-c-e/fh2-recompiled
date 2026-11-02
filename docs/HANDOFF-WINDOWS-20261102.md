# FH2 Windows combined candidate - November 2, 2026

The corrected combined candidate passes its native build and offline checks,
including actual save/load calls through the newly built SDK DLL. Matching
binaries are staged privately. Nothing was installed or launched; physical
motion/haptic safety qualification, gameplay and owner acceptance remain held.

## Exact candidate

- Compiled app: `7ce460f5b811a239185cea459c1d680524a3307b`.
- SDK: `bddeb1670c2b6890795653076880dc1b9196b7a5`, parent
  `499e0579b2e8a52f68b99748198816be7217ecee`.
- Retains the combined gear-refusal, reverse-above-15-mph guard, finite Data Out,
  focus/garage and corrected endian-capability work. New compiled changes are
  the missing-process-architecture fallback in the Windows build driver and
  correct string escaping in all three SDK TOML writers.
- Wheel helper `0ffe8eed` is included in source, with 42 inert-file checks and
  all 15 existing options matching the SDK. See [wheel setup](WHEEL-SETUP-20261102.md).
- Checked source/docs are published on `vuro/fh2-overnight-20261102`. Later
  patch-line-ending/docs commits do not change the compiled app/SDK identity.
  App main was not promoted. No assets, expanded image, generated guest code or
  native binaries were pushed. No SDK upstream push was made.

The [SDK patch, regression cases and fixture](../windows/patches/README.md)
record exact source availability. Local SDK bundle `sdk-cvar-strings.bundle`
requires base499, SHA-256
`95534D66928C89CC59165D3188A1058153043D1B4E470859624B9659B8B5F6D0`.
The earlier499 source bundle remains at
`E:/Source/dbce-project-mgmt/artifacts/fh2-haptic-endian-femi-20261023/sdk-source.bundle`,
SHA-256 `16CE729390FF679151BD9755389686796DB85E179E1BB518FCBD10C21B042EC9`,
requiring base `59bc11f546a6ea67eefcad974d0c14041b2ab20d`. Neither local SDK
commit is claimed to be available from the third-party remote.

## Verification and custody

- Existing production-endian capability fixture and eight disc-word witnesses
  were retained and hash-verified; their SDK input/header and disc pins are
  unchanged by the cvar-only SDK successor. All three XEX hashes match.
- Three focused architecture-fallback checks pass. Fresh configure detects AMD64.
- Real codegen: 722 files, 210.2 seconds. Native compile/link passes.
- Fresh generated gear fixture: 689 production checks, zero failures, plus
  seeded comparison and negative controls reproducing the refused-read hazard.
- Fresh reverse guard: 46 checks, zero failures. Finite telemetry: 65 checks,
  zero failures. No live vehicle behavior or UDP packets were asserted.
- OriginalSDK499 fails TOML parsing on a path selector (`unknown escape sequence
  '\H'`). Fixed production cvar.cpp passes 200 inert-file checks. The same200
  checks then pass through the **newly built runtime DLL**, with no local cvar
  replacement linked into that second fixture. They cover both serializers,
  merge, real SaveConfig/LoadConfig, repeat saves, eight string classes, typed
  values and unrelated root/table values. Full SDK unit target was not built.
- The helper's42 checks and architecture checks were reused without rerunning
  unchanged prerequisites. No game, input/device or graphics initialization.

Guna GO491322; operator vuro; native/Cargo jobs2. Build04 passes native and
all three generated checks, but its final harness compile fails because its
fmt include path was missing. Only that harness setup was corrected; no
production source or native binary changed. `qualification-05/result.json`
pins the original04 receipt and verifies every output hash before rerunning
only the DLL fixture. Qualification05 is **pass**, completed
`2026-11-02T07:30:08Z`. Both intervals have quiescent owned children, safe process
queries, released leases and absent literal tokens. Build04 remains failed in
its retained receipt; it was not relabeled as passing.

## Matching private output

| Member | SHA-256 |
| --- | --- |
| `fh2.exe` | `2D172D92FE5F57CCD0168F2C4D033B97B10DB08CBD5B4650DFA25FD19EAF557A` |
| `rexruntime.dll` | `04E80039FBF991A22F5DCA0585DAA5727259FD754F4DA98FF3C76ED0DB58098C` |
| `rexgpu-fh1.dll` | `AD8F442809BF3D19591B512A10DFCB86826C9455C2C5A478BD98E4CF90218D27` |
| `fh2_XMediaFacade_default.dll` | `ADD6D790DD79DA6D77E17157DA388B30A535AB024E439FCA19D52EF6EE92F028` |
| `fh2_SpeechFacade_default.dll` | `5B3527B2914FCB2EBC81A547FEA007571BCEC38DDE7AD71B52B99AF2A102F075` |

Build tree: `E:/Source/game-modding/.worktrees/vuro-fh2-s3-20261102`.
Evidence root:
`E:/Source/game-modding/.worktrees/vuro-fh2-overnight-20261102/.local/vuro-20261102/`.
Authoritative qualification receipt SHA-256:
`C67224CED0AD2B3D74388D80DB4A96D773A5F9B335F4C178C7EAFEC2E45AF762`.
Native04 receipt SHA-256:
`18D638BEE401A7F108B6C06AB32AA325727C03D43E2FBD004CFE0D510D0B2B36`.

`private-payload-strings/bin/` contains these five binaries and four existing
upscaler/license files. Established private staging recipe: PlanOnly, copy and
post-copy verification pass. `private-payload-strings/manifest.json` records all
nine sizes/hashes and receipt identity; `private-payload-strings-receipt.json`
records the copy. No game data, launcher, saves or owner config were copied;
this is not a complete game package.

Retain the original passing app6c49/SDK499 tree and `private-payload/` separately.
Keep build01's empty-architecture configure failure, build03's long-path staging
failure, build04's harness failure and the focused cvar01 link failure. Retry04
used a shorter fresh tree; no failed tree or unrelated worktree was deleted.
The source patch has explicit LF attributes; a Windows autocrlf checkout
retains its exact hash and passes apply-check against clean499.

## Image dump, installed baseline and remaining gates

Existing offline image route:
`windows/tools/Test-DiscRevision.ps1 -Xex <default.xex> -ImageOut <private-path>`.
Expanded image SHA-256:
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`.
Keep it private and ignored. Extracted game data remains at
`E:/Source/game-modding/dbce-mods-forza-horizon-2.wt-sync/assets/game_root`.

Owner installation was rehashed unchanged:
`E:/Source/toolkits/launchbox/Launchbox-Racing/Games/Windows/Forza Horizon 2 (Native)/bin/fh2.exe`,
SHA-256 `1139A7A07629AD52CAD686091CE0DC9F165F102E437BACD62C59B3739DCAD18B`
(October16; upstream version unestablished). Its config/user/logs, backups and
older candidates are preserved. Dirty upstream-sync SDK was not touched.
This source/build/private-stage work needs no owner rollback.

Before an agent live run, qualify the physical motion/haptic mute-and-restore
route, obtain a fresh serial GO and named lease, then use the existing private
launch/cleanup route with exact owner-state preservation. Installed behavior,
rendered UI, driving/reverse behavior, live packets, physical bindings/forces,
focus-loss stop and owner acceptance remain separate gates. Single-process
true triples are not implemented; existing multiscreen traces describe linked
instances. String serialization is fixed; the existing merger's broader syntax
and file-writer preservation limits were not changed by this patch.
