"""Record bounded, read-only camera extent evidence from private FH2 artifacts.

No compilation, guest execution, runtime DLL, game, device or owner-file access.
Output contains derived metadata and hashes, never generated function bodies.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct

IMAGE_SHA = "3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244"
SELECTED = {"sub_823F2FF0", "sub_82F44FB0", "sub_82F44F90", "sub_82F43678",
            "sub_82408998", "sub_82E431E0", "sub_82F50780", "sub_823F2568",
            "sub_82F46838", "sub_82F5BE50", "sub_82F435E8", "sub_82F44BB0", "sub_82F44B98",
            "sub_8293D7F0", "sub_8293F718", "sub_82931940", "sub_8292F400",
            "sub_83237BD8", "sub_83237BB0", "sub_83237D50", "sub_83237C40", "sub_83237DA0",
            "sub_82D3BF80", "sub_82D3B430", "sub_82D48C60", "sub_82D371F0"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("generated", "image", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    raw = args.image.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != IMAGE_SHA:
        raise ValueError("Wrong title image")
    selected, direct, raw_writers, modes, extents = {}, {}, {}, set(), set()
    kind32_candidates = {}
    count = 0
    for path in args.generated.glob("*.cpp"):
        source = path.read_text(encoding="utf-8-sig")
        matches = list(re.finditer(r"DEFINE_REX_FUNC\((\w+)\)", source))
        for i, match in enumerate(matches):
            name = match[1]
            body = source[match.start():matches[i+1].start() if i+1 < len(matches) else None]
            comments = re.findall(r"\t// (.+)", body)
            count += 1
            if name in SELECTED:
                if name in selected:
                    raise ValueError("Duplicate selected function")
                selected[name] = (body, comments)
            for target in ("sub_823F2FF0", "sub_82F43678", "sub_82E431E0", "sub_82F5BE50", "sub_82F435E8", "sub_82F44BB0"):
                if f"{target}(ctx, base);" in body or f"REX_TAIL_CALL({target})" in body:
                    direct.setdefault(target, []).append(name)
            offsets = sorted({int(v) for v in re.findall(r"\t// stfs f\d+,(240|244|248|252)\(r(?:3|31)\)", body)})
            if len(offsets) >= 3:
                raw_writers[name] = offsets
            if any(re.match(r"lwz r\d+,76\(r\d+\)", c) for c in comments) and sum(bool(re.match(r"(?:lfs|fmr|fmuls|fdivs|fadds|fsubs) f[1-4],", c)) for c in comments) >= 4:
                extents.add(name)
            if any(re.match(r"lwz r\d+,48\(r\d+\)", c) and any(v in comments[max(0,j-6):j+4] for v in ("li r4,0", "li r4,1")) for j,c in enumerate(comments)):
                modes.add(name)
            for j, line in enumerate(comments):
                match32 = re.match(r"lwz r\d+,32\((r\d+)\)", line)
                if not match32 or not any(re.match(r"lwz "+match32[1]+r",0\(r\d+\)", c) for c in comments[max(0,j-6):j]) or not any("mtctr" in c for c in comments[j+1:j+3]):
                    continue
                writes = [(k,c) for k,c in enumerate(comments[max(0,j-10):j+1],max(0,j-10)) if re.match(r"(?:li|lis|mr|addi|addis|lwz|ori|rotlwi|rlwinm|lbz) r4,", c)]
                if writes and writes[-1][1] == "li r4,1" and not any(c.startswith(("bl ","bctrl")) for c in comments[writes[-1][0]+1:j]):
                    kind32_candidates.setdefault(name, []).append(j)
    if set(selected) != SELECTED:
        raise ValueError("Missing selected camera function")
    checks = 0

    def expect(ok, label):
        nonlocal checks
        checks += 1
        if not ok:
            raise ValueError(label)

    def sequence(name, start, expected):
        expect(selected[name][1][start:start+len(expected)] == expected, name + " contract changed")

    sequence("sub_823F2FF0", 0, ["li r11,1", "stfs f1,240(r3)", "stfs f2,244(r3)", "stfs f3,248(r3)", "stb r11,480(r3)", "stfs f4,252(r3)", "blr "])
    sequence("sub_82F44F90", 0, ["lwz r11,0(r3)", "lfs f4,16(r4)", "lfs f3,12(r4)", "lfs f2,8(r4)", "lfs f1,4(r4)", "lwz r11,76(r11)", "mtctr r11", "bctr "])
    sequence("sub_82F44FB0", 20, ["stfs f31,4(r3)", "stfs f30,8(r3)", "mr r7,r3", "addi r11,r11,-48", "stfs f29,12(r3)", "stfs f28,16(r3)"])
    for index, line in {55:"lfs f6,212(r31)",57:"lfs f5,208(r31)",59:"lfs f4,252(r31)",61:"lfs f3,244(r31)",63:"lfs f2,248(r31)",65:"lfs f1,240(r31)",69:"bl 0x82e431e0"}.items():
        sequence("sub_82408998", index, [line])
    # Four near-corner triples, before any inference about inward/outward winding.
    for index, line in {40:"stfs f31,160(r1)",41:"stfs f29,164(r1)",43:"stfs f27,168(r1)",45:"stfs f31,112(r1)",53:"stfs f28,116(r1)",55:"stfs f27,120(r1)",71:"stfs f30,144(r1)",72:"stfs f28,148(r1)",74:"stfs f27,152(r1)",75:"stfs f30,128(r1)",76:"stfs f29,132(r1)",77:"stfs f27,136(r1)"}.items():
        sequence("sub_82E431E0", index, [line])
    sequence("sub_82F50780", 98, ["lis r11,-32247", "lis r10,-32256", "mr r3,r30", "lfs f4,10284(r11)", "lfs f3,19132(r10)", "fmr f1,f4", "fmr f2,f3", "lwz r11,0(r30)", "lwz r11,76(r11)", "mtctr r11", "bctrl ", "lwz r11,0(r30)", "li r4,0", "mr r3,r30", "lwz r11,52(r11)", "mtctr r11", "bctrl "])
    sequence("sub_82F46838", 33, ["li r27,3"])
    sequence("sub_82F46838", 45, ["stw r27,8(r3)"])
    sequence("sub_82F435E8", 0, ["li r11,1", "stw r4,8(r3)", "stb r11,480(r3)", "blr "])
    sequence("sub_82F44B98", 0, ["lwz r11,0(r3)", "lwz r4,4(r4)", "lwz r11,32(r11)", "mtctr r11", "bctr "])
    sequence("sub_82F44BB0", 13, ["stw r30,4(r3)"])
    # Receiver identity: this list's owning subobject is ForzaUI, and its
    # population helper casts UI controls before appending their pointers.
    sequence("sub_8293F718", 22, ["addi r9,r6,26404", "addi r11,r5,26388", "stw r10,32(r31)", "li r30,0", "stw r9,108(r31)"])
    sequence("sub_8293D7F0", 27, ["lwz r11,196(r30)", "addi r29,r30,196", "lwz r10,200(r30)"])
    sequence("sub_82931940", 23, ["addi r11,r11,-26688", "addi r4,r10,-24468", "stw r11,80(r1)", "addi r5,r1,80", "mr r3,r31", "bl 0x83002ab8", "addi r29,r31,304", "addi r3,r1,80", "mr r4,r29", "bl 0x8292f400"])
    sequence("sub_8292F400", 15, ["lis r10,-31944", "lis r11,-31944", "addi r30,r10,-11796", "addi r29,r11,-11128", "mr r6,r29", "lwz r3,0(r31)", "mr r5,r30", "li r7,0", "li r4,0", "bl 0x823f4828"])
    sequence("sub_8292F400", 25, ["stw r3,80(r1)", "cmplwi r3,0", "beq 0x8292f47c", "addi r4,r1,80", "mr r3,r28", "bl 0x82735e38"])
    # These two primary tables share AddRef/Release and have deleting
    # destructors at slot32; they are not presentation-camera tables.
    sequence("sub_83237BB0", 0, ["addi r11,r3,40", "mfmsr r9", "mtmsrd r13,1", "lwarx r10,0,r11", "addi r10,r10,1"])
    sequence("sub_83237BD8", 0, ["addi r11,r3,40", "mfmsr r9", "mtmsrd r13,1", "lwarx r10,0,r11", "addi r10,r10,-1"])
    sequence("sub_83237BD8", 13, ["lwz r11,0(r3)", "li r4,1", "lwz r10,32(r11)", "mtctr r10", "bctr "])
    sequence("sub_83237D50", 8, ["addi r9,r11,23428", "addi r8,r10,23388", "li r7,0", "stw r9,0(r31)", "stw r8,4(r31)", "mr r3,r31", "stw r7,40(r31)"])
    for name in ("sub_83237C40", "sub_83237DA0"):
        sequence(name, 11, ["lwz r7,28(r3)", "addi r31,r3,8", "cmplwi cr6,r7,16"])
    sequence("sub_82D3B430", 4, ["lis r11,-32235", "mr r31,r3", "addi r11,r11,-28364"])
    sequence("sub_82D3BF80", 15, ["lis r11,-31911", "mr r8,r27", "mr r7,r28", "mr r6,r29", "mr r5,r30", "stw r3,-29684(r11)"])
    sequence("sub_82D48C60", 11, ["lwz r4,-29684(r28)", "addi r30,r31,4024", "lwz r11,0(r4)", "lwz r11,32(r11)", "mtctr r11", "bctrl ", "mr r4,r3", "mr r3,r30", "bl 0x82da57f0"])
    sequence("sub_82D371F0", 47, ["addi r10,r10,-31012"])
    sequence("sub_82D371F0", 53, ["stw r10,0(r3)"])
    sequence("sub_82D371F0", 97, ["addi r11,r11,-30268", "stw r11,0(r3)"])

    def word(address):
        return struct.unpack_from(">I", raw, address-0x82000000)[0]

    def cstring(address):
        start = address-0x82000000
        return raw[start:raw.index(0,start)].decode("ascii")

    def table_type(table):
        return cstring(word(word(table-4)+12)+8)

    expect(table_type(0x82086724) == ".?AVCAnimatedScrollingListCtrl@ForzaUI@@", "List owner RTTI changed")
    expect(word(word(0x82086720)+4) == 108 and word(0x82086724+40) == 0x8293D7F0, "List subobject changed")
    expect(cstring(0x8337D1EC+8) == ".?AVCUI4Control@@" and cstring(0x8337D488+8) == ".?AVCUIContainerItemCtrl@@", "List cast types changed")
    expect(cstring(0x8203A06C) == "GROUP_ITEMS", "List property changed")
    for table, destructor in ((0x822C5B60,0x83237C40),(0x822C5B84,0x83237DA0)):
        expect(word(table) == 0x83237BB0 and word(table+4) == 0x83237BD8 and word(table+32) == destructor, "Refcounted string table changed")
    expect(table_type(0x82149134) == ".?AVCAudioEngine@@" and word(0x82149134+32) == 0x82D371F0, "Audio engine factory changed")
    expect(table_type(0x821486DC) == ".?AV?$TRefCountedObject@VCAudioEmission@@@@", "Audio emission type changed")
    expect(table_type(0x821489C4) == ".?AV?$TRefCountedObject@VCDummyAudioEmission@@@@", "Dummy audio emission type changed")
    values = {0x8209282C:-4., 0x82004ABC:4., 0x8224FA5C:.10000000149011612, 0x8224FA60:7.5}
    for address, value in values.items():
        expect(struct.unpack_from(">f", raw, address-0x82000000)[0] == value, "Producer constant changed")
    slots = {32:0x82F435E8,44:0x82F46988,48:0x82F43678,52:0x823F2568,76:0x823F2FF0,196:0x823F3068}
    for table in (0x8224FBDC, 0x82002D44):
        for slot, target in slots.items():
            expect(struct.unpack_from(">I", raw, table+slot-0x82000000)[0] == target, "Camera vtable changed")
    expect(direct.get("sub_82E431E0") == ["sub_82408998"], "Constructor caller set changed")
    record = {"status":"static-contract-recorded-culling-held", "checks":checks,
              "observedUtc":datetime.now(timezone.utc).isoformat(), "imageSha256":IMAGE_SHA,
              "generatedFunctionCount":count, "directCallers":direct,
              "directFloatWriterCandidates":raw_writers,
              "slot76FloatCandidates":sorted(extents), "slot48ModeCandidates":sorted(modes),
              "candidateIntersection":sorted(extents & modes),
              "slot32KindOneCandidates":kind32_candidates,
              "identifiedNonCameraCandidates":{"sub_8293D7F0":"CUIContainerItemCtrl list in ForzaUI CAnimatedScrollingListCtrl",
                                               "sub_83237BD8":"refcounted small-string Release to deleting destructor",
                                               "sub_82D4CB20":"CAudioEmission or CDummyAudioEmission"},
              "remainingUnclassifiedSlot32Sites":{k:v for k,v in kind32_candidates.items() if k not in ("sub_8293D7F0","sub_83237BD8","sub_82D4CB20")},
              "kind1ExtentProducerEstablished":False, "cullingAdmitted":False,
              "sourceBackedControl":{"producer":"82F50780", "kind":2,
                                     "storedExtents":[-4,4,4,-4], "near":values[0x8224FA5C],"far":7.5},
              "functionSha256":{k:hashlib.sha256(v[0].encode()).hexdigest().upper() for k,v in selected.items()},
              "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()}
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "result.json").write_text(json.dumps(record, indent=2)+"\n")
    print(f"{checks} static checks; {count} generated functions scanned; kind1 producer unresolved; CULLING HOLD")


if __name__ == "__main__":
    main()
