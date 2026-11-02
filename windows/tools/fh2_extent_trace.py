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
            "sub_82D3BF80", "sub_82D3B430", "sub_82D48C60", "sub_82D371F0",
            "sub_831CA678", "sub_831CB908", "sub_831CA938", "sub_831CB410",
            "sub_831349B8", "sub_83148EA8", "sub_82F5A2C8", "sub_82F5BEE0",
            "sub_82F59C88", "sub_82FFB710", "sub_823F46D8", "sub_823F3050",
            "sub_82473418", "sub_82471158", "sub_82F4F1D0", "sub_824517D0",
            "sub_82DE9AF0", "sub_82D440A0", "sub_82456A90", "sub_82F46060",
            "sub_82E41AA0", "sub_82478900", "sub_82F4EE70", "sub_82F59FB8",
            "sub_82F4EE30", "sub_82F4D818", "sub_823FBA80", "sub_82456A60", "sub_8244DFA0",
            "sub_82F46458", "sub_82F47188", "sub_82F42C50", "sub_82475C80", "sub_82F5AF30",
            "sub_82476B00", "sub_82475C48", "sub_823F59C8", "sub_82470088", "sub_82400E48",
            "sub_82401630", "sub_82473410",
            "sub_82EF12D0", "sub_82450DE8", "sub_8244F4A0", "sub_8244EF48", "sub_8244ED60", "sub_8244EEE8", "sub_8244DFA8", "sub_8244EF08", "sub_824515D8", "sub_82451138", "sub_824513C0", "sub_824827F8", "sub_824501A0", "sub_8244EC00", "sub_8244FA90", "sub_8244FE60"}


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
            for target in ("sub_823F2FF0", "sub_82F43678", "sub_82E431E0", "sub_82F5BE50", "sub_82F435E8", "sub_82F44BB0", "sub_82F46060"):
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
    for name, member, parameters in (("sub_831CA678",256,260),("sub_831CB908",8,12)):
        sequence(name, 7, ["lis r10,-32239", "mr r30,r3", f"addi r5,r3,{member}", "addi r4,r10,-15536", "lwz r11,0(r11)", "mr r3,r31", "mtctr r11", "bctrl "])
        sequence(name, 19, [f"addi r5,r30,{parameters}", "addi r4,r10,-5376"])
    sequence("sub_831CA938", 60, ["rotlwi r3,r11,0", "addi r7,r1,112", "li r6,1", "addi r5,r1,96", "li r4,1", "lwz r11,0(r3)", "lwz r11,32(r11)", "mtctr r11", "bctrl "])
    sequence("sub_831CA938", 81, ["rotlwi r3,r11,0", "addi r7,r1,96", "li r6,1", "addi r5,r1,104", "li r4,1", "lwz r11,0(r3)", "lwz r11,32(r11)", "mtctr r11", "bctrl "])
    sequence("sub_831CB410", 43, ["lwz r3,256(r31)", "lwz r11,0(r3)", "addi r7,r1,96", "li r6,1", "addi r5,r1,104", "li r4,1", "lwz r11,32(r11)", "mtctr r11", "bctrl "])
    # sqlite3_vfs.xOpen fills the sqlite3_file at pager+56. Its method table
    # has an iVersion word, so byte32 is xUnlock, not a C++ camera method.
    sequence("sub_83148EA8", 97, ["addi r11,r3,176", "mr r31,r3", "stw r11,168(r3)", "addi r11,r11,48", "cmplwi cr6,r29,0", "stw r11,56(r3)"])
    sequence("sub_83148EA8", 145, ["stw r23,84(r1)", "addi r7,r1,84", "lwz r11,24(r30)", "andi. r6,r25,32543", "mr r3,r30", "mtctr r11", "lwz r5,56(r31)", "lwz r4,132(r31)", "bctrl "])
    sequence("sub_831349B8", 20, ["lwz r3,56(r31)", "addi r4,r1,88", "lwz r11,0(r3)", "lwz r11,36(r11)", "mtctr r11", "bctrl "])
    sequence("sub_831349B8", 47, ["lwz r3,56(r31)", "li r4,2", "lwz r11,0(r3)", "lwz r11,28(r11)", "mtctr r11", "bctrl "])
    sequence("sub_831349B8", 61, ["lwz r3,56(r31)", "li r4,1", "lwz r11,0(r3)", "lwz r11,32(r11)", "mtctr r11", "bctrl "])
    # Receiver-backed route for future camera searches: a typed presentation
    # creates/registers cameras; slot60 removes one from this same registry.
    sequence("sub_82F5A2C8", 114, ["mr r3,r31", "bl 0x82f50780"])
    sequence("sub_82F5BE50", 24, ["addi r3,r31,10104", "bl 0x824d3168", "addi r3,r1,80", "bl 0x8248cc60", "lwz r11,10108(r31)", "lwz r3,-4(r11)"])
    sequence("sub_82F5BEE0", 4, ["mr r31,r4", "lwz r4,0(r4)", "bl 0x82f59c88", "mr r3,r31", "bl 0x8248cc60"])
    sequence("sub_82F59C88", 3, ["mr r7,r4", "lwz r11,10108(r3)", "lwz r5,10104(r3)", "addi r4,r3,10104"])
    sequence("sub_82F59C88", 36, ["addi r3,r1,80", "bl 0x82ffb710"])
    sequence("sub_82FFB710", 25, ["lwz r11,4(r30)", "mr r3,r26", "stw r28,0(r26)", "addi r11,r11,-4", "stw r11,4(r30)"])
    sequence("sub_823F46D8", 7, ["lwz r31,10104(r3)", "addi r26,r3,10104", "lwz r11,10108(r3)"])
    sequence("sub_823F46D8", 33, ["mr r4,r28", "lwzx r5,r30,r31", "add r11,r29,r11", "addis r3,r11,1", "addi r3,r3,-9712", "bl 0x823f3050", "addi r29,r29,288", "cmpwi cr6,r29,576"])
    sequence("sub_823F3050", 0, ["lwz r11,0(r3)", "stw r4,4(r3)", "cmpwi cr6,r11,1", "beqlr cr6", "stw r5,8(r3)", "blr "])
    sequence("sub_82473418", 4, ["lwz r10,10108(r3)", "mr r11,r3", "lwz r8,10104(r3)"])
    sequence("sub_82471158", 8, ["addi r3,r1,80", "addi r30,r31,400", "bl 0x82de9af0", "mr r4,r3", "lwz r3,4(r31)", "bl 0x82473418", "mr r4,r3", "mr r3,r30", "bl 0x82d440a0"])
    sequence("sub_82F4F1D0", 18, ["mr r4,r3", "mr r3,r30", "bl 0x82473418", "mr r28,r3"])
    sequence("sub_82F4F1D0", 107, ["bl 0x82408998"])
    sequence("sub_824517D0", 4, ["addi r4,r4,400", "mr r31,r3", "bl 0x82de9af0", "mr r3,r31"])
    sequence("sub_82DE9AF0", 11, ["lwz r11,0(r31)", "mr r3,r31", "lwz r11,8(r11)", "mtctr r11", "bctrl ", "stw r31,0(r30)"])
    sequence("sub_8244DFA0", 0, ["lwz r3,10120(r3)", "blr "])
    sequence("sub_82456A60", 0, ["lwz r3,500(r3)", "blr "])
    sequence("sub_82F4F1D0", 120, ["lvx128 v127,r28,r9"])
    sequence("sub_82F4F1D0", 133, ["bl 0x82f46060", "addi r11,r29,2299"])
    sequence("sub_82F4F1D0", 143, ["lwzx r3,r11,r30", "ld r11,328(r1)", "lwz r31,0(r3)", "std r11,88(r1)", "lwz r11,168(r31)", "mtctr r11", "bctrl "])
    for index,line in ((7,"lwz r11,460(r1)"),(87,"lwz r11,484(r1)"),(226,"bl 0x82e41aa0"),(234,"bl 0x82478900"),(237,"lwz r11,452(r1)")):
        sequence("sub_82F46060", index, [line])
    sequence("sub_82F46060", 243, ["stvx128 v60,r11,r10", "stvx128 v61,r11,r9", "stvx128 v62,r11,r8", "stvx128 v63,r0,r11"])
    sequence("sub_82E41AA0", 0, ["lvx128 v62,r0,r3", "lis r11,-32256", "lvx128 v63,r0,r4", "addi r10,r1,-16", "vsubfp128 v61,v62,v63"])
    sequence("sub_82E41AA0", 26, ["vmulfp128 v63,v63,v59", "vsubfp128 v63,v61,v63", "vmulfp128 v63,v63,v60", "vsubfp128 v1,v62,v63", "blr "])
    sequence("sub_82478900", 51, ["stvx128 v60,r0,r3", "stvx128 v63,r3,r11", "stvx128 v59,r3,r10", "stvx128 v62,r3,r9", "blr "])
    sequence("sub_82F4EE70", 42, ["cmpwi cr6,r30,2", "bne cr6,0x82f4ef5c"])
    sequence("sub_82F4EE70", 59, ["cmpwi cr6,r30,3", "bne cr6,0x82f4ef9c"])
    sequence("sub_82F59FB8", 118, ["li r29,0"])
    sequence("sub_82F59FB8", 151, ["lwz r11,0(r31)", "mr r3,r31", "lwz r11,56(r11)", "mtctr r11", "bctrl ", "mr r4,r3", "mr r3,r30", "bl 0x82d440a0"])
    sequence("sub_82F59FB8", 183, ["lwz r3,0(r30)", "li r4,0", "lwz r11,0(r3)", "lwz r11,44(r11)", "mtctr r11", "bctrl ", "addi r29,r29,1", "cmpwi cr6,r29,4"])
    sequence("sub_823FBA80", 0, ["std r4,32(r1)", "addi r11,r3,16"])
    sequence("sub_823FBA80", 24, ["stb r8,480(r3)", "blr "])
    sequence("sub_82F4D818", 163, ["bl 0x82f46060"])
    sequence("sub_82F4D818", 181, ["bl 0x823fb1b0"])
    sequence("sub_82F4D818", 210, ["bl 0x823fb1b0"])
    expect(set(direct.get("sub_82F46060",[])) == {"sub_82F4F1D0","sub_82F4D818"}, "Mirror matrix helper callers changed")
    sequence("sub_82F46458", 10, ["mulli r10,r10,80"])
    sequence("sub_82F46458", 18, ["lfs f0,52(r11)", "fadds f0,f0,f13", "lfs f12,48(r11)", "lfs f13,56(r11)", "stb r8,9344(r3)"])
    sequence("sub_82F47188", 23, ["bl 0x82475c80"])
    for index in (39,66,92,119,145,171):
        sequence("sub_82F47188", index, ["bl 0x823fb1b0"])
    for index in (45,71,97,124,150,176):
        sequence("sub_82F47188", index, ["bl 0x82f42c50"])
    sequence("sub_82F47188", 112, ["lfs f4,-5324(r11)"])
    sequence("sub_82F5AF30", 7, ["lwz r21,400(r3)"])
    sequence("sub_82F5AF30", 357, ["beq 0x82f5b544"])
    sequence("sub_82F5AF30", 383, ["stfs f0,9280(r31)", "stfs f13,9284(r31)", "stfs f12,9288(r31)", "stfs f11,9292(r31)"])
    sequence("sub_82F5AF30", 389, ["lwz r11,0(r21)", "mr r4,r21", "addi r3,r1,208", "lwz r11,180(r11)", "mtctr r11", "bctrl "])
    for index,offset in ((410,9280),(416,9284),(422,9288),(428,9292)):
        sequence("sub_82F5AF30", index, [f"stfs f1,{offset}(r31)"])
    sequence("sub_82F5AF30", 459, ["bl 0x82422d80"])
    sequence("sub_82F5AF30", 464, ["addi r11,r31,9216"])
    sequence("sub_82476B00", 4, ["addi r4,r4,16", "li r5,64"])
    sequence("sub_82475C48", 4, ["addi r4,r4,80", "li r5,64"])
    expect(not any(re.match(r"lwz r\d+,184\(r\d+\)", c) for c in selected["sub_82F5AF30"][1]), "Packet producer now calls stored-projection getter; retrace")
    sequence("sub_82F42C50", 8, ["lfs f13,20(r3)"])
    sequence("sub_82F42C50", 35, ["stfs f0,16(r31)"])
    sequence("sub_82F42C50", 39, ["lvx128 v63,r30,r11", "stvx128 v63,r0,r31", "lfs f13,8(r31)", "fneg f13,f13", "stfs f13,8(r31)"])
    sequence("sub_82F42C50", 50, ["stfs f0,16(r31)", "stvx128 v63,r0,r31", "stfs f0,24(r31)"])

    # Visibility dispatch, ordinary AABB consumer and distinct mask/byte storage.
    sequence("sub_82EF12D0", 32, ['li r4,0', 'lwz r5,16(r31)', 'lwz r3,8(r31)', 'bl 0x82c023a0'])
    sequence("sub_82EF12D0", 81, ['li r11,2', 'addi r10,r31,1440', 'addi r9,r31,8096', 'addi r8,r31,7584'])
    sequence("sub_82EF12D0", 89, ['stfs f30,384(r11)', 'stfs f31,388(r11)', 'stw r10,208(r11)', 'stw r9,212(r11)', 'stw r7,368(r11)', 'stw r8,360(r11)'])
    sequence("sub_82EF12D0", 114, ['lwz r10,0(r8)', 'rlwinm r11,r10,2,0,29', 'lwzx r11,r11,r7', 'mulli r11,r11,344', 'add r11,r11,r31', 'addi r11,r11,14036', 'lwz r9,140(r11)', 'addi r9,r9,3', 'rlwinm r9,r9,2,0,29', 'stwx r10,r9,r11', 'lwz r9,140(r11)', 'addi r9,r9,1', 'stw r9,140(r11)'])
    sequence("sub_82EF12D0", 150, ['addi r29,r31,14372', 'li r30,2', 'li r4,1', 'mr r3,r29'])
    sequence("sub_82EF12D0", 167, ['lbz r9,9302(r31)', 'addi r7,r31,8096', 'lwz r11,44(r31)', 'addi r10,r31,7584', 'stw r7,100(r1)', 'addi r8,r31,1440', 'lfs f0,9296(r31)', 'stw r10,248(r1)', 'stfs f0,260(r1)', 'stw r8,96(r1)', 'stb r9,268(r1)', 'addi r4,r31,48', 'stw r11,256(r1)'])
    sequence("sub_82EF12D0", 188, ['lwz r11,9376(r31)', 'addi r6,r1,96', 'lwz r10,9380(r31)', 'mr r3,r31', 'lwz r9,176(r31)', 'fmr f2,f31', 'fmr f1,f30', 'stw r11,236(r1)', 'stw r10,240(r1)', 'stw r9,232(r1)', 'bl 0x82450de8'])
    sequence("sub_82450DE8", 4, ['li r11,5', 'lwz r10,8(r6)', 'mr r30,r6', 'fmr f31,f1', 'srawi r9,r11,31', 'addi r24,r6,8'])
    sequence("sub_82450DE8", 48, ['mr r4,r30', 'mr r3,r31', 'bl 0x8244f4a0'])
    sequence("sub_8244EF48", 233, ['lwz r4,4(r29)', 'rlwinm r6,r30,5,0,26', 'addi r7,r1,112', 'lwz r5,0(r29)', 'add r6,r6,r4', 'lbz r10,172(r29)', 'addi r4,r1,116', 'stw r7,92(r1)', 'mulli r11,r30,192', 'lwz r9,224(r31)', 'stw r4,84(r1)', 'stb r27,103(r1)', 'li r24,0', 'addi r8,r31,192', 'mr r7,r30', 'stb r24,112(r1)', 'add r5,r11,r5', 'stw r24,116(r1)', 'mr r4,r28', 'mr r3,r31', 'bl 0x8244ed60'])
    sequence("sub_8244EF48", 258, ['li r5,1', 'bl 0x8244ef08'])
    sequence("sub_8244EF48", 282, ['mulli r11,r30,5', 'stw r24,160(r1)', 'stw r27,172(r1)', 'lwz r10,13844(r31)', 'stb r9,176(r1)', 'add r11,r11,r29', 'addi r4,r1,160', 'rlwinm r11,r11,4,0,27', 'add r3,r11,r10', 'bl 0x824515d8'])
    sequence("sub_8244EF48", 296, ['li r5,0', 'bl 0x8244ef08'])
    sequence("sub_8244ED60", 56, ["lfs f0,104(r1)","fneg f0,f0","lfs f13,120(r1)","fneg f13,f13","stfs f0,120(r1)","stfs f13,104(r1)"])
    sequence("sub_8244ED60", 63, ['lbz r11,113(r30)', 'cmplwi r11,0', 'beq 0x8244ee80', 'addi r5,r1,96', 'addi r4,r1,112', 'mr r3,r24', 'bl 0x8244fa90', 'clrlwi. r11,r3,24', 'beq 0x8244ede0'])
    sequence("sub_8244ED60", 87, ['addi r11,r1,96', 'addi r10,r1,112', 'mr r3,r31', 'lvx128 v2,r0,r11', 'lvx128 v1,r0,r10', 'bl 0x82451138', 'addic r11,r3,-1', 'subfe r3,r11,r3'])
    sequence("sub_8244EEE8", 0, ['li r11,1', 'lwz r10,68(r3)', 'slw r11,r11,r4', 'and r11,r10,r11', 'addic r10,r11,-1', 'subfe r3,r10,r11', 'blr '])
    sequence("sub_8244DFA8", 0, ['li r11,1', 'lwz r10,72(r3)', 'slw r11,r11,r4', 'and r11,r10,r11', 'addic r10,r11,-1', 'subfe r3,r10,r11', 'blr '])
    sequence("sub_8244EF08", 0, ['add r11,r4,r3', 'clrlwi r10,r5,24', 'lbz r9,76(r11)', 'cmplw cr6,r10,r9', 'beqlr cr6', 'li r9,1', 'cmplwi cr6,r10,0', 'stb r9,54(r3)', 'stb r5,76(r11)', 'lwz r11,108(r3)', 'beq cr6,0x8244ef3c', 'addi r11,r11,1', 'b 0x8244ef40', 'addi r11,r11,-1', 'stw r11,108(r3)', 'blr '])
    sequence("sub_824515D8", 57, ['lwz r11,4(r31)', 'addi r11,r11,20', 'stw r11,4(r31)'])
    sequence("sub_82451138", 151, ['cmplwi cr6,r11,3', 'bne cr6,0x824513a4', 'li r3,0', 'blr ', 'addi r11,r11,-1', 'cntlzw r11,r11', 'rlwinm r11,r11,27,31,31', 'xori r11,r11,1', 'addi r3,r11,1', 'blr '])
    sequence("sub_824513C0", 41, ['fadds f12,f12,f9', 'fsubs f13,f12,f13', 'fcmpu cr6,f13,f0', 'bgt cr6,0x8245148c', 'addi r10,r10,1', 'addi r11,r11,16', 'cmplw cr6,r10,r6', 'blt cr6,0x8245140c', 'li r3,1', 'blr ', 'li r3,0', 'blr '])
    sequence("sub_824827F8", 13, ['addi r29,r31,4', 'addi r28,r31,340', 'mr r6,r29', 'lfs f2,184(r31)', 'lfs f1,180(r31)', 'bl 0x82450de8'])
    expect(struct.unpack_from(">4f", raw, 0x13F47C0) == (1.,1.,-1.,1.), "Ordinary AABB conversion vector changed")
    expect(tuple(struct.unpack_from(">16I", raw, 0x2486A8)) == (1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1), "Visibility worker grouping table changed")

    sequence("sub_8244FA90", 11, ["lvx128 v63,r0,r4","lvx128 v62,r0,r5","addi r10,r1,80","addi r11,r11,2888"])
    sequence("sub_8244FE60", 0, ['lis r11,-32256', 'lfs f13,20(r3)', 'lfs f0,3152(r11)', 'fcmpu cr6,f13,f0', 'bge cr6,0x8244fe7c', 'li r3,1', 'blr ', 'lvx128 v63,r0,r3', 'addi r11,r1,-16', 'lvx128 v62,r0,r4', 'vsubfp128 v63,v62,v63', 'lfs f0,16(r3)', 'lfs f13,24(r3)', 'li r3,1', 'fmuls f13,f13,f1', 'vmsum3fp128 v63,v63,v63', 'stvx128 v63,r0,r11', 'lfs f12,-16(r1)', 'fmuls f0,f0,f12', 'fcmpu cr6,f0,f13', 'blelr cr6', 'li r3,0', 'blr '])

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
    expect(raw[0x10C350:0x10C360].hex() == "a90bc001e897e89755e49e4700000000", "Legacy IXAPO IID changed")
    expect(raw[0x29EB00:0x29EB10].hex() == "a90bc001e897e89755e49e4700000001", "Legacy IXAPOParameters IID changed")
    expect(cstring(0x82152E2C) == ":memory:", "SQLite memory filename changed")
    expect(cstring(0x82250CB4) == "mirrorR*" and cstring(0x82250CC0) == "mirrorL*", "Native mirror selectors changed")
    expect(struct.unpack_from(">f",raw,0xAF0)[0] == 2., "Reflected-ray scale changed")
    expect(struct.unpack_from(">f",raw,0x1EB34)[0] == 2.5 and struct.unpack_from(">f",raw,0x24FA48)[0] == 5000., "Packet axial far constants changed")
    expect(table_type(0x8225134C) == ".?AVCPresentation@@", "Presentation type changed")
    expect(table_type(0x82003524) == ".?AV?$TRefCountedObjectThreadSafe@VCPresentation@@@@", "Refcounted presentation type changed")
    for table in (0x8225134C,0x82003524):
        for slot,target in ((28,0x82F5A2C8),(56,0x82F5BE50),(60,0x82F5BEE0)):
            expect(word(table+slot) == target, "Presentation camera lifecycle slot changed")
    expect(table_type(0x8200243C) == ".?AVCPresentationView@@" and word(0x8200243C+28) == 0x82471158 and word(0x8225134C+72) == 0x82F4F1D0, "Typed view-camera route changed")
    expect(word(0x8200243C+32) == 0x824517D0, "View camera reference getter changed")
    values = {0x8209282C:-4., 0x82004ABC:4., 0x8224FA5C:.10000000149011612, 0x8224FA60:7.5}
    for address, value in values.items():
        expect(struct.unpack_from(">f", raw, address-0x82000000)[0] == value, "Producer constant changed")
    slots = {32:0x82F435E8,44:0x82F46988,48:0x82F43678,52:0x823F2568,60:0x82470088,72:0x82400E48,
             76:0x823F2FF0,92:0x82456A60,168:0x823FBA80,180:0x82476B00,184:0x82475C48,
             188:0x82401630,192:0x82473410,196:0x823F3068,252:0x823F59C8}
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
                                               "sub_82D4CB20":"CAudioEmission or CDummyAudioEmission",
                                               "sub_831CA938":"IXAPO LockForProcess at owner+256 and owner+8",
                                               "sub_831CB410":"IXAPO LockForProcess at owner+256",
                                               "sub_831349B8":"sqlite3_file xUnlock(SQLITE_LOCK_SHARED)"},
              "remainingUnclassifiedSlot32Sites":{k:v for k,v in kind32_candidates.items() if k not in ("sub_8293D7F0","sub_83237BD8","sub_82D4CB20","sub_831CA938","sub_831CB410","sub_831349B8")},
              "typedCameraLifecycle":{"owner":"CPresentation","createSlot":56,"removeSlot":60,
                                      "registryBeginOffset":10104,"registryEndOffset":10108,
                                      "viewCameraAssignment":"82471158 via registry resolver82473418 to view+400",
                                      "rendererRecordAdmission":"823F46D8 ->823F3050; record pointers only",
                                      "initializerKindEstablished":2,"kind1SelectionEstablished":False},
              "viewConsumerTrace":{"getter32":"824517D0: acquired reference copy of view+400",
                                   "consumer":"82F46060: reflected-ray/look-at camera transform",
                                   "mirrorSelectors":{"2":"mirrorL*","3":"mirrorR*"},
                                   "destinationCameraArrayOffset":9196,"destinationCameraCount":4,
                                   "destinationSetupKind":0,"cameraTransformSetterSlot":168,
                                   "packetCaller":"82F4D818","packetIndependentSymmetricFrustums":True,
                                   "projectionUploadEstablished":False,"liveReceiverEstablished":False},
              "packetProjectionTrace":{"selectedEntryStride":80,"selectedCenterOffset":9328,
                                       "selectedPositionOffsets":[48,52,56],"centerYOffset":0.5,
                                       "axialFrustumBase":1440,"frustumStride":192,"axialCount":6,
                                       "viewMatrixOffset":9152,"inverseViewMatrixOffset":9216,
                                       "scalarOffsets":{"fov":9280,"aspect":9284,"near":9288,"far":9292},
                                       "metadataBase":8096,"metadataStride":32,
                                       "recordIndices":{"axial":[0,1,2,3,4,5],"mirrorSelectors":{"0":6,"1":6,"2":7,"3":8},
                                                        "view":"packet+36","farVariant":"packet+40","additionalFarVariant":15},
                                       "directStoredProjectionGetterFound":False,
                                       "cullingConstruction":"symmetric FOV reconstruction",
                                       "gpuProjectionDeliveryEstablished":False},
              "visibilityTrace":{"dispatcher":"82EF12D0","consumer":"82450DE8",
                                 "workerCount":2,"workerStride":344,"workerPayloadOffset":4,
                                 "context":{"frustumPointer":0,"metadataPointer":4,"viewIds":8,"viewCount":136},
                                 "workerGroupZeroIds":[9],"ordinaryInstanceConsumer":"8244EF48 ->8244ED60 ->82451138",
                                 "ordinaryBoundsConversion":"negate and swap Z min/max before AABB helper",
                                 "metadataGate":"8244FA90 ->8244FE60: weight16*distanceSquared <= factor24*halfExtentSquared; field20<0 bypass",
                                 "inputMaskOffset":68,"secondMaskOffset":72,"visibilityByteBase":76,
                                 "visibilityCountOffset":108,"dirtyByteOffset":54,
                                 "bucketHeaderStride":16,"bucketIndex":"5*viewId+category","outputRecordStride":20,
                                 "resourceParticipationBitset":"packet pointer+8 with length+16; separate from instance masks",
                                 "dispatcherExecuted":False,"workerExecuted":False,"gpuProjectionDeliveryEstablished":False},
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
