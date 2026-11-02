# FH2 candidate static import inventory

Candidate app734fff4/SDKe223de8d, private payload manifest37A52E96. This is
read-only PE metadata and filename presence on the November2 host. No payload
binary was executed or loaded, and no dependency was installed or copied.

`windows/tools/fh2_dependency_inventory.py` verifies every manifest member's
size/hash before invoking the existing LLVM20.1.8 reader on the seven PE files.
It records direct normal/delay import module names and symbol counts, raw LLVM
metadata, source/tool/manifest hashes and a host-System32 catalog observation.
It rejects escaping/mismatched members, unexpected image architecture and
incomplete delay-import metadata. No custom binary/PE parser is added.

```powershell
python windows/tools/fh2_dependency_inventory_test.py
python -I windows/tools/fh2_dependency_inventory.py --llvm <llvm-readobj.exe> --payload <private-payload/bin> --manifest <private-payload/manifest.json> --out <fresh-project-output>
```

## Observed result

Seven x64 PE files,102 normal import records, no nonzero delay-import directory
in those images.31 distinct imported module names:

| Catalog observation | Distinct names | Meaning |
| --- | --- | --- |
| Co-located payload member |1 | rexruntime.dll is present beside the executable/facades/GPU plugin |
| Native System32 file present |14 | Windows modules, including DXGI/HID/WinSock; presence is not symbol/loader validation |
| Native System32 MSVC runtime file present |4 | MSVCP140.dll, MSVCP140_ATOMIC_WAIT.dll, VCRUNTIME140.dll, VCRUNTIME140_1.dll |
| Native System32 Vulkan loader present |1 | vulkan-1.dll is imported by the packaged FidelityFX runtime; device/driver capability is untested |
| API-set contracts |11 | api-ms-win-crt-* contracts; availability not queried |

No import filename falls outside this catalog. That is not a startup pass or
a claim that another PC meets the prerequisites. API sets are loader contracts
and need not be physical files, as [Microsoft documents](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-apisets).
Actual DLL resolution also depends on redirection, loaded modules, configured
search paths and other [Windows search-order rules](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order).
The inventory does not simulate those rules or walk host DLL forwarding and
transitive dependencies; it records direct imports of the payload PE files.

TracyClient.dll is not listed in any inspected payload import table, although
the SDK build produces that additional artifact. This inventory provides no
reason to add it to the existing nine-file payload.

## Late loading and limits

Source SDKe223de8d `src/system/gpu_plugin_loader.cpp` builds a per-configuration
rexgpu-<name><postfix>.dll path next to the executable. The Releasefh1 filename
matches the staged rexgpu-fh1.dll. `src/ui/vulkan/vulkan_dlss_upscaler.cpp` and
vulkan_ffx_upscaler.cpp locate the supplied runtime DLLs at run time. These are
source observations, not executed loader paths. The import inventory does not
enumerate all LoadLibrary calls, plugin ABI checks, optional APIs or device
probing. It does not load the Vulkan loader or initialize graphics/input/FFB.

Six focused unit tests pass: normal/nested delay records, incomplete/malformed
output refusal, API-contract handling, case/location catalog behavior, path
escape and hash-mismatch refusal before any CLI call/output. A real tiny x64
PE fixture was also linked with one delayed import and inspected by LLVM,
without running it or creating/loading the target DLL. That caught and fixed
the nested delay-symbol counting case; the private candidate was then
inventoried again with the corrected reader.

Private evidence `windows/.local/dependency-inventory/native734-final/`,
inventory.json SHA256
`F3FA353ABEB9F92CA725D29B28D4A738E7C192F2234C59F371234C19F9A68D8D`.
Tiny PE inputs/import library/metadata are retained in siblingdelay-fixture/;
the initial missing delayimp library command and first nested-symbol assertion
failure are retained in the session evidence. The final linked fixture parses
exactly one delayed symbol. [Microsoft's PE specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
describes the import and delay-import structures consumed by LLVM.

No candidate rebuild, package membership/hash change, owner-state write,
library load, game/GPU/device initialization, installation or rig lease occurred.
The previously qualified native pair and staged payload are unchanged.
