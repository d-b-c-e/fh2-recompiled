# FH2 native settings: report save results

SDK source candidate **e35aedef68e8015d2fd0b79067f0bb12d907c6a5** adds
TrySaveConfig on top of the [preservation candidate](CONFIG-PRESERVATION-20261102.md)
fb1822c9. It returns true only after publication or a no-change result, and
false on parse/read/staging/write/rename failures. The existing void SaveConfig
entry point remains as a wrapper, keeping its existing signature and symbol.
Default-only no-ops may leave a nonexistent file absent, as before.

The native SettingsDialog Save button stores that result and shows
`Last save completed.` or `Save failed; see the log.` after an attempt. The
label describes the last attempt, so editing later is not presented as a new
save. Both scroll panels reserve footer space using the current font/style
metrics for the button/path and status rows. This is SDK F4 settings work;
no FH2 F6/F7 camera overlay or camera persistence is implied.

## Reproduction and evidence

Apply `windows/patches/shiftglue-sdk-cvar-preserve.patch` to bddeb167, then
`windows/patches/shiftglue-sdk-save-result.patch` to fb1822c9. The latter patch
changes four SDK files: cvar API/source and settings overlay header/source.
Patch SHA256 `C6FA28E868775339F0680166FB6D45EA6DB82B9861FA76CE99AB3BB3C861D235`.
Forward apply-check against an isolated fb1822 index and reverse-check against
e35aedef pass. Private `windows/.local/cvar-preserve/sdk-save-result.bundle`
requires fb1822, verifies, SHA256
`C5ED7EB9DFA9CDC05954C66410125F43BFCF0C91831DC21C9369410D80334647`.
Both predecessor branches/bundles and qualified native payload are retained.

Use the existing production-cvar runner in an x64 VS developer shell:

```powershell
pwsh -File windows/tools/Check-Fh2CvarPreservation.ps1 -BuiltSdk <qualified-built-sdk> -SourceSdk <patched-sdk> -Out <fresh-project-output> -Compiler <clang++.exe> -SaveResult
```

Results on November2:

- Actual candidate cvar.cpp **18 save-result checks PASS**: new/update/no-change
  success, no-op default/empty behavior, invalid/duplicate/composite refusal,
  staging collision, unreadable directory, missing parent, **real read-only
  destination rename failure**, retained staging/original bytes, and legacy API.
- Existing **67 preservation +200 serializer/save/load checks PASS** on the
  same candidate. Every cvar function is candidate production source, with
  existing parser/backend code; no cvar mocks or old-DLL replacement.
- Actual settings_overlay.cpp **compiles to an object** using the new header
  and actual SDK/ImGui dependencies. No UI link, ImGui frame, native window,
  GPU/input/device initialization, game or owner settings access occurred.
- Receipt/logs `windows/.local/cvar-preserve/save-result01/`, result.json SHA256
  `E4DB6548CC04BC56BE0D0EC253ADEACFC2C943098D4D209028F47AC5CF435FD8`.
  Initial UI compile had harmless unused link-library argument warnings; the
  runner now removes link libraries for object compilation. A separate
  `windows/.local/cvar-preserve/save-ui-only/` compile passes with the filtered
  command and retains source/header/object hashes. Passing cvar suites were
  reused rather than rerun for that command-only cleanup.

The app SDK gitlink stays bddeb167. No full SDK/runtime DLL/app build,
installation or SDK upstream push was made; no existing binary includes this
later change. A future compatible SDK/app build must include both patches.
Visible layout, actual click reachability, game settings readback and owner
acceptance remain unverified. Physical motion/haptic testing remains held.
