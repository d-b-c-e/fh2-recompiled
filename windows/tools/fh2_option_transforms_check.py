#!/usr/bin/env python3
"""Pin FH2's generated wheel action transforms without launching the game.

    python -I windows/tools/fh2_option_transforms_check.py --generated <windows/generated/default> --image <expanded-default.xex>
"""
import argparse
import hashlib
import re
import struct
from pathlib import Path


def function(tree: Path, name: str) -> str:
    for path in sorted(tree.glob("fh2_recomp.*.cpp")):
        source = path.read_text(errors="replace")
        start = source.find(f"DEFINE_REX_FUNC({name}) {{")
        if start >= 0:
            return source[start:source.index("\n}\n", start)]
    raise SystemExit(f"{name} not found in {tree}")


def instructions(body: str) -> list[str]:
    return re.findall(r"^\s*// (.+)$", body, re.MULTILINE)


def require_sequence(haystack: list[str], needles: list[str], label: str) -> None:
    at = 0
    for needle in needles:
        try:
            at = haystack.index(needle, at) + 1
        except ValueError as exc:
            raise AssertionError(f"{label}: missing {needle}") from exc


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--generated", required=True, type=Path)
parser.add_argument("--image", required=True, type=Path)
args = parser.parse_args()

image = args.image.read_bytes()
assert hashlib.sha256(image).hexdigest().upper() == "3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244", "disc image"
for address, expected in ((0x820167F8, b"Wheel"), (0x82019CDC, b"Options/"),
                          (0x8201DBE4, b"InvertGearUpDown"), (0x82019CA8, b"InvertHandbrakeClutch"),
                          (0x8201DBCC, b"InvertCameraLookBack"), (0x82005B1C, b"Main/Shifting")):
    assert image[address - 0x82000000:].split(b"\0", 1)[0] == expected, f"guest string {address:08X}"
actions = {}
for row in range(20):
    pointer, action = struct.unpack_from(">II", image, 0x82021DC8 - 0x82000000 + 8 * row)
    actions[action] = image[pointer - 0x82000000:].split(b"\0", 1)[0]
assert {key: actions[key] for key in (4, 5, 3, 6, 13, 17)} == {
    4: b"ShiftUp", 5: b"ShiftDown", 3: b"Handbrake", 6: b"Clutch",
    13: b"LookStraightBack", 17: b"SwitchCamera"}, "action name/ID table"

producer = instructions(function(args.generated, "sub_82576B78"))
require_sequence(producer, ["cmpwi cr6,r23,1", "mr r4,r29", "addi r5,r11,-25380",
                            "bl 0x82492158"], "wheel class constructs WheelOptions/")
for byte, offset in ((0, -9244), (1, -25432), (2, -9268)):
    require_sequence(producer, [f"addi r5,r11,{offset}", "bl 0x8249f558", "bl 0x825451d0",
                                "bl 0x82649760", f"stb r11,{80 + byte}(r1)"],
                     f"WheelOptions key at byte {byte}")
require_sequence(producer, ["addi r5,r11,23324", "bl 0x825451d0", "bl 0x827bd1c0",
                            "stb r11,83(r1)", "addi r6,r1,80", "bl 0x825afa18"],
                 "Main/Shifting is the fourth byte")
consumer = instructions(function(args.generated, "sub_825AFA18"))
for byte, left, right in ((0, 4, 5), (1, 3, 6), (2, 13, 17)):
    require_sequence(consumer, [f"lbz r11,{byte}(r25)", f"cmpwi cr6,r3,{left}" if byte == 0 else f"cmpwi cr6,r31,{left}",
                                f"li r31,{right}", f"cmpwi cr6,r31,{right}", f"li r31,{left}"],
                     f"option byte {byte} swaps action IDs {left}/{right}")
require_sequence(consumer, ["cmplwi cr6,r24,0", "bne cr6,0x825afc40", "lbz r11,3(r25)",
                            "cmplwi r11,0", "cmpwi cr6,r11,5", "li r31,25",
                            "cmpwi cr6,r31,5", "li r5,25", "bl 0x82d86c78"],
                 "fourth byte is gated to controller class 0, not wheel class 1")
print("FH2 option action transforms: source assertions passed (three WheelOptions keys and Main/Shifting; three swaps)")
