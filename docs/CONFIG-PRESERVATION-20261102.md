# FH2 native config preservation: isolated SDK follow-up

This STD044 follow-up fixes the SDK settings writer without changing the
qualified SDK/app or an owner file. The app gitlink stays bddeb167. The new SDK
source candidate is **fb1822c99e63819f06d7dc44fafc943f52d8ed40**, retained at
`windows/.local/cvar-preserve/sdk`, branch `vuro/cvar-preserve-20261102`.
No SDK upstream push or native SDK DLL/app rebuild has been performed.

## Changed behavior

The former MergeIntoTOML scanned physical lines. It could rewrite a
registered-looking key inside an owner's multiline string, mistake bracket
text inside a string for a table header, ignore quoted root keys, remove inline
comments/spacing and add an unwanted final newline. SaveConfig stripped the BOM
and could truncate an existing sibling `.tmp` recovery file.

The new merger parses with existing toml++3.4.0, edits only the source spans of
registered **root scalar values**, and inserts missing modified flags in root
scope. Original keys, quotes, equals spacing, inline comments, line endings,
BOM and unrelated string/array/table content remain byte-for-byte. UTF-8
source columns are decoded-codepoint counts, mapped back to byte offsets;
tables/strings are not recognized by scanning their text. Changed multiline
owned values become the existing single-line escaped literal; unrelated
multiline values remain intact.

Malformed/duplicate TOML and an owned key holding an array/table are refused.
The generated result is parsed again before writing. SaveConfig catches those
errors, refuses unreadable existing files, keeps the original BOM and uses
C++23 noreplace when creating its staging file. An existing `<config>.tmp`
therefore blocks the save and remains intact. A write/rename error is logged;
this patch does not add a new overlay success/failure UI or change the public
void SaveConfig API. A failed rename can retain the new staging file for
diagnosis. Do not delete a retained staging file without establishing ownership.

The existing sibling-write/rename publication remains. This is not a guarantee
against another program replacing the config concurrently between read and
rename, nor a power-loss durability claim. Existing typed serialization and
string escaping are retained.

## Source and reproduction

[`shiftglue-sdk-cvar-preserve.patch`](../windows/patches/shiftglue-sdk-cvar-preserve.patch)
applies to SDKbddeb167. SHA256
`9A34CD5CB457E196B32F4F19D490EFF2D54E3CEEC1AE8F1E3B632F83243729C8`.
It changes only src/core/cvar.cpp, the API comment and one existing unit
expectation that previously required comment removal. BSD-3-Clause source
copyright/license are retained. Forward apply-check against the clean qualified
base and reverse apply-check against the isolated successor pass.

Private `windows/.local/cvar-preserve/sdk-preserve.bundle` requires bddeb167,
verifies successfully and retains fb1822c9. SHA256
`E32C2E3EA658F95F7AD1C24C631B414B31EB09089BDCD680EFE9F7B4B7B8F708`.
The earlier bddeb/499 bundles and matching binaries remain separate.

In an x64 Visual Studio developer shell with clang++/llvm-readobj/llvm-dlltool:

```powershell
pwsh -File windows/tools/Check-Fh2CvarPreservation.ps1 -BuiltSdk <qualified-built-sdk> -SourceSdk <isolated-patched-sdk> -Out <fresh-project-evidence-folder> -Compiler <clang++.exe>
```

The runner builds **actual candidate cvar.cpp** plus each focused fixture and
the exact vendored parser. It filters cvar exports from the backend import
library so no old-DLL cvar function can replace the candidate implementation.
Only unchanged backend functions come from the qualified runtime DLL. It
does not initialize game, graphics, input or physical devices, access owner
settings, install a candidate, or build the whole SDK/app. Logs and result.json
record commands, source/fixture/runtime hashes and exit codes.

Context7 supplied unversioned source-position documentation. Exact3.4.0
source_region/key/parser headers were checked for inclusive begin/exclusive
end,1-based positions and decoded-codepoint columns. See the pinned
[source-region definition](https://github.com/marzer/tomlplusplus/blob/v3.4.0/include/toml%2B%2B/impl/source_region.hpp).

## Evidence and remaining gates

- Before-fix real runtime-DLL fixture fails its first exact scalar/comment
  preservation assertion. The executable/output is retained under
  `windows/.local/cvar-preserve/before/`.
- Candidate actual cvar.cpp: **67 preservation checks PASS**. Quoted/escaped
  keys, Unicode/emoji, owned and unknown multiline strings with key/header
  text, arrays/inline/dotted tables, array-of-tables, mixed LF/CRLF, no final
  newline, BOM, missing-key root placement, stable second save, malformed and
  ambiguous refusal, and unchanged existing staging files.
- Existing real serializers/merge/SaveConfig/LoadConfig fixture: **200 checks
  PASS**, all eight string classes. The full SDK unit suite was not built.
- Authoritative logs/receipt: `windows/.local/cvar-preserve/final/`, SHA256 of
  result.json `5BB58D5AB15164E6E9170E403B5230EE1D8A9BF9010789368DC452EDE5DA8EF3`.
  Production cvar.cpp SHA256
  `30D0C92B5C291B48868067338F1D8EC9EBF03F718A0B006D291C8CA720EDBB5D`.
  Existing toml++ deprecated literal-operator warnings remain; no production
  warnings were suppressed or third-party headers changed.

These are source/compiled-component and inert-file results. SDKbddeb and the
app7ce460f binaries/private payload do not include this later source change.
A separate SDK/app build and native settings UI/game readback remain required.
Motion/haptic, gameplay, devices and owner acceptance stay held/unverified.
