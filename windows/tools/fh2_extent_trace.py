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
            "sub_82F46838", "sub_82F5BE50", "sub_82F435E8", "sub_82F44BB0", "sub_82F44B98"}


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
