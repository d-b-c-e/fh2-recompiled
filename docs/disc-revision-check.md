# Disc revision check: media 15E4FA3D (version 0.0.0.6)

2026-10-15. Upstream built `app/overrides.toml` from the USA disc **media `7C7779D1`,
version 0.0.0.12** (`docs/fh2_disco.md`). The disc used for the Windows build here is the
same title (`4D530AA4`) but **media `15E4FA3D`, version 0.0.0.6**, so the file hashes of all
three XEX files differ:

| File | Upstream SHA-256 | This disc SHA-256 |
|---|---|---|
| `default.xex` | `516b04d7…1feb7` | `dbbe28a8…bd684` |
| `XMediaFacade_default.xex` | `1b080164…56490` | `423a3ba0…36d3c` |
| `SpeechFacade_default.xex` | `275ed703…27878` | `6504b536…b6230` |

The code layout is what matters for the function boundaries, and it matches:

- Same image size (24,117,248 bytes), image base `0x82000000` and entry point `0x82BF2CD0`.
- `windows/tools/Test-DiscRevision.ps1` decrypts and expands `default.xex` and compares the
  instructions at every address whose encoding `app/overrides.toml` annotates (thunks,
  accessor table, the no-prologue leaves after a backward `b`). **7 of 7 match**, including
  relative branches, which would fail if anything in between had moved.
- Expanded image SHA-256 on this disc: `3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`.

The same thing happens with Forza Horizon 1: Pinyon Shift's title update built for disc
0.0.0.12 applies exactly to the USA 0.0.0.10 disc.

Not yet checked: the two facade DLLs (their overrides carry no annotated encodings) and
code that changed in place without moving. Codegen's own validation ("target not in any
function", invalid calls at run time) is the next check.
