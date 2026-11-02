# SDK string serialization follow-up

`shiftglue-sdk-cvar-strings.patch` fixes raw quoted strings in all three SDK
TOML writers: both `SerializeToTOML` overloads and `MergeIntoTOML`, which backs
`SaveConfig`. It reuses the vendored toml++ 3.4.0 formatter with no literal or
multiline flags, so paths, quotes, control bytes and Unicode round trip while
each cvar stays on one physical line. Non-string values retain their old path.
The SDK source is BSD-3-Clause; its copyright/license remain in the source tree.
See [toml++ serialization documentation](https://github.com/marzer/tomlplusplus/blob/v3.4.0/docs/pages/main_page.md).
Context7 had no versioned entry; constructor/flag behavior was checked against
the exact vendored 3.4.0 headers as well as the library documentation.

Base SDK: `499e0579b2e8a52f68b99748198816be7217ecee`.
Local successor: `bddeb1670c2b6890795653076880dc1b9196b7a5`.
Patch SHA-256: `67DB71AC46884CF594FFC0BE330354AAB67A056BD80EBF3AA50E49FEB8A14CA2`.
`git apply --check` passes against clean base499. Apply in an isolated SDK
worktree; the original build tree and matching private payload remain on SDK499.
The source branch gitlink is now advanced to bddeb167 for a separate new build.
No SDK upstream push or app-main promotion was made.

The patch includes regression cases in the existing SDK cvar unit suite. That
complete test target was not built here. Instead,
[`fh2_cvar_strings_fixture.cpp`](../tools/fh2_cvar_strings_fixture.cpp) was compiled
with the actual production `src/core/cvar.cpp`, first at base499 and then fixed.
It uses real serializer/merge/SaveConfig/LoadConfig calls and eight inert strings:
HID paths, quotes, mixed quoting, newlines/tabs, NUL/controls, Unicode and empty.
The fixture never initializes game, graphics or input/device systems.

Base499 fails TOML parsing with `unknown escape sequence '\H'`; fixed source
passes **200 checks**, including real save/load and stable repeated saves, typed
booleans/integers, unknown host keys and table preservation. No mocks replace the
cvar functions. To isolate them from the existing runtime DLL's exports, the
focused harness uses a generated import library omitting `rex::cvar` exports;
only unchanged backend functions come from that DLL. A first unfiltered-link
attempt failed with duplicate symbols before any fixture ran; it is retained.

Local evidence root:
`E:/Source/game-modding/.worktrees/vuro-fh2-overnight-20261102/.local/vuro-20261102/`.
`Run-CvarStrings-02.ps1` records exact flags, pinned dependency paths and import
map generation. `cvar-strings-02/result.json` records compiler/fixture identities,
input hashes and successful cleanup; its SHA-256 is
`64DA0F7F0FE51C3426262B856A74455A1F04FB765E484EC9F02E34B32767B2AF`.
Guna GO491236, jobs1, completed `2026-11-02T06:56:42Z`; all owned children
quiescent, process queries safe, named lease released and literal token absent.
The receipt and per-step logs are authoritative; the runner's final console
summary rendered null fields, so completion was verified from the saved receipt.

`sdk-cvar-strings.bundle` retains the exact successor locally, requires base499,
and passes `git bundle verify`. SHA-256:
`95534D66928C89CC59165D3188A1058153043D1B4E470859624B9659B8B5F6D0`.
The patch is published source; the bundle and native fixture outputs stay private.

This is a qualified source follow-up, **not included in the built SDK499 DLL**.
The new source gitlink awaits a native build in a separate tree under Guna
GO491322 (up to90min, jobs2, named operator vuro). Preserve the
passing `6c49f9c`/SDK499 payload. Physical safety, live config round trips inside
FH2, gameplay, force feedback and owner acceptance remain unverified. This patch
does not broaden the existing merger's supported syntax or change its file writer.
