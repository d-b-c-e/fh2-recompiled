"""Verify bounded FH2 static evidence. Inputs stay private; output is metadata only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

IMAGE_SHA = "3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244"
BASE = 0x82000000
EDGES = {
    "829C4440": ["829C11C8"], "829C45D8": ["829C11C8"],
    "82D305F0": ["83032690"], "8303F550": ["8306EC68"],
    "8262CC40": ["829BAC58", "829BAC60", "82F467E0"],
    "82F5CA60": ["82F5C5B0"], "82F5C5B0": ["82F5AF30"],
    "82F53D60": ["82F4D818"], "82F4D818": ["82EF12D0"],
    "82EF12D0": ["82450DE8"], "824827F8": ["82450DE8"],
}
SLOTS = {
    (0x82149134, 48): 0x82D305F0,
    (0x822648A8, 228): 0x8303F550,
    (0x8224FE8C, 168): 0x82F45590,
    (0x8224FE8C, 56): 0x82F44E58,
    (0x8224FBDC, 168): 0x823FBA80,
    (0x8224FBDC, 56): 0x82F435F8,
    (0x8224FBDC, 68): 0x82F43608,
    (0x8224FBDC, 196): 0x823F3068,
    (0x8200243C, 44): 0x8245E918,
    (0x8200243C, 48): 0x82F5CA60,
}
PATTERNS = {
    "829BAC58": ["addi r3,r3,240"],
    "829BAC60": ["lfs f1,304(r3)"],
    "823FBA80": ["480(r3)"],
    "82F435F8": ["stfs f1,260(r3)"],
    "82F43608": ["stfs f1,256(r3)"],
    "823F3068": ["stfs f1,208(r3)", "stfs f2,212(r3)"],
    "82F5AF30": ["14033(r31)", "14034(r31)", "addi r3,r31,14012"],
    "82F53D60": ["lbz r11,14032(r31)", "lbz r11,14034(r31)"],
}


def analyze(image, generated):
    raw = image.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != IMAGE_SHA:
        raise ValueError("Expanded-image revision mismatch; refusing address assumptions")
    checks = []
    for (table, slot), target in SLOTS.items():
        actual = struct.unpack_from(">I", raw, table + slot - BASE)[0]
        assert actual == target, f"slot {table:08X}+{slot}"
        checks.append({"table": f"{table:08X}", "slot": slot, "target": f"{target:08X}"})
    for address, expected in [(0x82264650, b"..\\src\\fmod_eventi.cpp"),
                              (0x8226596C, b"..\\src\\fmod.cpp")]:
        assert raw[address - BASE:address - BASE + len(expected) + 1] == expected + b"\0"
    functions = {}
    wanted = set(EDGES) | set(PATTERNS)
    for path in sorted(generated.glob("*.cpp")):
        source = path.read_text(encoding="utf-8-sig")
        matches = list(re.finditer(r"DEFINE_REX_FUNC\(sub_([0-9A-F]+)\)", source))
        for index, match in enumerate(matches):
            address = match[1]
            if address not in wanted:
                continue
            assert address not in functions, f"duplicate function {address}"
            body = source[match.start():matches[index + 1].start() if index + 1 < len(matches) else None]
            calls = [x.upper() for x in re.findall(r"// bl 0x([0-9a-f]+)", body)]
            for callee in EDGES.get(address, []):
                assert callee in calls, f"missing edge {address}->{callee}"
            for pattern in PATTERNS.get(address, []):
                assert any(pattern in line.strip()[3:] for line in body.splitlines()
                           if line.strip().startswith("// ")), f"missing instruction {address}: {pattern}"
            functions[address] = {"directCalls": calls,
                                  "generatedBodySha256": hashlib.sha256(body.encode()).hexdigest()}
    assert wanted == set(functions), f"missing functions: {wanted - set(functions)}"
    return {"imageSha256": digest, "imageBytes": len(raw), "staticChecksPassed": True,
            "gameExecuted": False, "safeSceneReplayEstablished": False,
            "vtableChecks": checks, "functions": functions,
            "fovRadiansToDegrees": struct.unpack_from(">f", raw, 0x5910)[0]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.image, args.generated)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(result['functions'])} function records, {len(SLOTS)} vtable slots; static only")
