#Requires -Version 7.0
<#
.SYNOPSIS
    Checks that a Forza Horizon 2 (Xbox 360) default.xex has the code layout that
    app/overrides.toml was written for.

.DESCRIPTION
    Decrypts and expands the retail XEX2 (basic compression, as shiftglue-sdk
    src/system/xex_module.cpp ReadImageBasicCompressed does), then compares the
    instructions at addresses whose expected encoding is annotated in app/overrides.toml.
    Relative branches are included, so a shifted layout fails. Nothing is written beside
    the game; -ImageOut saves the expanded image if you want it.

.EXAMPLE
    pwsh -File windows\tools\Test-DiscRevision.ps1 -Xex assets\game_root\default.xex
#>
param([Parameter(Mandatory)][string]$Xex, [string]$ImageOut)
$ErrorActionPreference = 'Stop'
$d = [IO.File]::ReadAllBytes((Resolve-Path $Xex))
function U32([int]$o) { ([uint32]$d[$o] -shl 24) -bor ([uint32]$d[$o+1] -shl 16) -bor ([uint32]$d[$o+2] -shl 8) -bor [uint32]$d[$o+3] }
function U16([int]$o) { ([uint32]$d[$o] -shl 8) -bor [uint32]$d[$o+1] }
if ([Text.Encoding]::ASCII.GetString($d, 0, 4) -ne 'XEX2') { throw 'not an XEX2 file' }
$peOffset = U32 8; $secOffset = U32 0x10; $count = U32 0x14
$headers = @{}
for ($i = 0; $i -lt $count; $i++) { $headers[(U32 (0x18 + 8*$i))] = U32 (0x1C + 8*$i) }
$exec = $headers[[uint32]0x40006]
$ffi = $headers[[uint32]0x3FF]
$infoSize = U32 $ffi; $enc = U16 ($ffi + 4); $comp = U16 ($ffi + 6)
if ($comp -ne 1) { throw "compression type $comp (only basic = 1 is handled)" }
$blocks = for ($o = $ffi + 8; $o -lt $ffi + $infoSize; $o += 8) { [pscustomobject]@{ data = U32 $o; zero = U32 ($o + 4) } }
$retail = [byte[]](0x20,0xB1,0x85,0xA5,0x9D,0x28,0xFD,0xC3,0x40,0x58,0x3F,0xBB,0x08,0x96,0xBF,0x91)
$aes = [Security.Cryptography.Aes]::Create(); $aes.Key = $retail
$session = $aes.DecryptEcb([byte[]]$d[($secOffset + 0x150)..($secOffset + 0x15F)], 'None')
$total = ($blocks | Measure-Object data -Sum).Sum
$cipher = [byte[]]::new($total); [Array]::Copy($d, $peOffset, $cipher, 0, $total)
$plain = if ($enc -eq 1) { $aes.Key = $session; $aes.DecryptCbc($cipher, [byte[]]::new(16), 'None') } else { $cipher }
$imageSize = U32 ($secOffset + 4)
$img = [byte[]]::new($imageSize)
$src = 0; $dst = 0
foreach ($b in $blocks) { [Array]::Copy($plain, $src, $img, $dst, $b.data); $src += $b.data; $dst += $b.data + $b.zero }
if ($ImageOut) { [IO.File]::WriteAllBytes($ImageOut, $img) }
function W([int64]$a) { $o = [int]($a - 0x82000000L); '{0:X8}' -f (([uint32]$img[$o] -shl 24) -bor ([uint32]$img[$o+1] -shl 16) -bor ([uint32]$img[$o+2] -shl 8) -bor [uint32]$img[$o+3]) }

# Expected encodings, from the comments in app/overrides.toml.
$checks = @(
    @{ a = 0x82E83A70L; w = @('3863006C','4BFFFF84'); what = 'addi r3,r3,0x6C; b 0x82E839F8' },
    @{ a = 0x82E78AF8L; w = @('3863FF84','4800AF74'); what = 'addi r3,r3,-0x7C; b 0x82E83A70' },
    @{ a = 0x82C9EFD8L; w = @('3D600001','616B7164','7C63582E','4E800020'); what = 'lis/ori r11 = 0x17164; lwzx r3,r3,r11; blr' },
    @{ a = 0x82C9EFF0L; w = @('38630110'); what = 'addi r3,r3,0x110' },
    # Leaves without a prologue right after the previous function's backward b.
    @{ a = 0x8305E794L; w = @('4BFFFFF0'); what = 'b back (tail of the function before 0x8305E798)' },
    @{ a = 0x8305E8ACL; w = @('4BFFFFF0'); what = 'b back (tail of the function before 0x8305E8B0)' },
    @{ a = 0x83045374L; w = @('4BFFFFF0'); what = 'b back (tail of the function before 0x83045378)' }
)
$fail = 0
foreach ($c in $checks) {
    $got = for ($i = 0; $i -lt $c.w.Count; $i++) { W ($c.a + 4*$i) }
    $ok = ($got -join ' ') -eq ($c.w -join ' ')
    if (-not $ok) { $fail++ }
    '{0}  {1:X8}  {2,-48} {3}' -f ($(if ($ok) { 'MATCH' } else { 'DIFF ' })), $c.a, $c.what, ($got -join ' ')
}
[pscustomobject]@{
    title_id = '{0:X8}' -f (U32 ($exec + 12)); media_id = '{0:X8}' -f (U32 $exec)
    version = '{0}.{1}.{2}.{3}' -f ((U32 ($exec + 4)) -shr 28), (((U32 ($exec + 4)) -shr 24) -band 0xF), (((U32 ($exec + 4)) -shr 8) -band 0xFFFF), ((U32 ($exec + 4)) -band 0xFF)
    image_size = $imageSize; entry_point = '{0:X8}' -f $headers[[uint32]0x10100]
    image_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($img))
    result = $(if ($fail) { "$fail of $($checks.Count) checks differ: overrides.toml does not fit this revision" } else { "all $($checks.Count) checks match" })
}
if ($fail) { exit 1 }
