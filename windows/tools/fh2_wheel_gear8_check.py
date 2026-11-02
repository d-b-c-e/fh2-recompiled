"""Bridge the real SDK binding parser into FH2's generated reader/sampler fixture.

Run in an x64 VS developer shell. Only PadControlFromName comes from the built
runtime DLL; no SDL/input/graphics initialization or physical devices. Generated
guest fixture sources and binaries stay in the fresh explicit --out directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source-sdk", required=True, type=Path)
p.add_argument("--built-sdk", required=True, type=Path)
p.add_argument("--generated", required=True, type=Path)
p.add_argument("--cxx", required=True, type=Path)
p.add_argument("--out", required=True, type=Path)
p.add_argument("--built-parser", action="store_true", help="Import the parser itself from the built runtime DLL")
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
source, built, out = a.source_sdk.resolve(), a.built_sdk.resolve(), a.out.resolve()
out.mkdir(parents=True, exist_ok=False)
record = {"status": "fail", "startedUtc": datetime.now(timezone.utc).isoformat(), "steps": [],
          "gameLaunched": False, "physicalDevicesInitialized": False, "graphicsInitialized": False,
          "ownerStateWritten": False, "generatedRoutinesOnSyntheticMemory": True,
          "parserMode": "built-runtime-dll" if a.built_parser else "production-source"}


def run(name, command, timeout=120):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=timeout, cwd=out)
    (out / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
    record["steps"].append({"name": name, "command": list(map(str, command)), "exitCode": result.returncode})
    if name != "exports" or result.returncode:
        print(result.stdout + result.stderr, end="", flush=True)
    result.check_returncode()
    return result.stdout


try:
    run("emit", [sys.executable, "-I", root / "tools/fh2_gear_refusal_check.py", "--generated", a.generated.resolve(),
                 "--sdk", built, "--cxx", a.cxx.resolve(), "--out", out / "guest", "--emit-only"])
    llvm = a.cxx.resolve().parent
    exports = run("exports", [llvm / "llvm-readobj.exe", "--coff-exports", built / "out/win-amd64/rexruntime.dll"])
    prefixes = ["?PadControlFromName@input@rex@@"]
    if a.built_parser:
        prefixes += ["?ParseWheelButtonBindings@sdl@input@rex@@"]
    names = [x for x in re.findall(r"^\s+Name: (.+)$", exports, re.M) if any(x.startswith(v) for v in prefixes)]
    assert len(names) == len(prefixes), "Expected exactly the requested production parser/name exports"
    (out / "pad-name.def").write_text("LIBRARY rexruntime.dll\nEXPORTS\n" + "\n".join(names) + "\n")
    run("imports", [llvm / "llvm-dlltool.exe", "-m", "i386:x86-64", "-d", out / "pad-name.def", "-l", out / "pad-name.lib"])
    shutil.copyfile(built / "out/win-amd64/rexruntime.dll", out / "rexruntime.dll")
    driver = (source / "src/input/sdl/sdl_input_driver.cpp").read_text()
    assert "gear = binding.gear;" in driver and "pad.thumb_rx = gear;" in driver, "SDK bridge changed; trace it again"
    record["sha256"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest().upper() for path in
                        [source / "src/input/sdl/wheel_mapping.cpp", source / "src/input/sdl/sdl_input_driver.cpp",
                         out / "guest/fix/harness.cpp", out / "rexruntime.dll"]}
    (out / "bridge.cpp").write_text(r'''
#define main OriginalGearFixture
#include "guest/fix/harness.cpp"
#undef main
#include <rex/input/sdl/wheel_mapping.h>
int main() {
  if (OriginalGearFixture()) return 1;
  using namespace rex::input::sdl;
  const auto bindings = ParseWheelButtonBindings("GEAR1=Shifter|0,GEAR7=Shifter|6,GEAR8=Shifter|7,REVERSE=Shifter|8,RB=9");
  check(bindings.size() == 5, "all explicit gates including8 must parse", int(bindings.size()));
  bool found8 = false;
  for (const auto& binding : bindings) {
    if (binding.gear == 0) continue;
    const int raw = binding.gear;
    check(Gear(kNone, raw) == (raw == -1 ? 0 : raw), "parsed gate reaches actual guest request", raw);
    for (Refusal refused : {kFocus_, kCode, kChord, kClass, kNoFlag})
      check(Gear(refused, raw) == 10, "parsed gate obeys existing refusal path", raw);
    if (raw == 8) {
      found8 = true;
      check(binding.device == "Shifter" && binding.button == 7 && binding.xbuttons == 0,
            "GEAR8 preserves explicit selector/button without gamepad side effects", raw);
    }
  }
  check(found8, "GEAR8 must be recognized", 0);
  for (const char* invalid : {"GEAR0=0", "GEAR9=0", "GEAR10=0", "GEAR-1=0"})
    check(ParseWheelButtonBindings(invalid).empty(), "invalid gate names still refused", 0);
  auto lower = ParseWheelButtonBindings("gear8=Pedals|-axis3");
  check(lower.size() == 1 && lower[0].gear == 8 && lower[0].axis == 3 &&
        lower[0].axis_direction == AxisDirection::kInverted, "case-insensitive axis gate binding", 0);
  check(Gear(kNone, 0) == 9, "released shifter stays neutral", 0);
  std::printf("GEAR8 bridge: %d total checks, %d failures; no SDL/device/game launch\n", checks, failures);
  return failures ? 1 : 0;
}
''', encoding="utf-8")
    command = [a.cxx.resolve(), "-std=c++23", "-O1", "-fuse-ld=lld", "-msse4.1", "-DMODE=0",
               "-D_DLL", "-D_MT", "-Xclang", "--dependent-lib=msvcrt", "-DSPDLOG_COMPILED_LIB", "-DSPDLOG_FMT_EXTERNAL",
               "-Wno-unused-variable", "-Wno-unused-label", "-I", out / "guest", "-I", source / "include"]
    for directory in ["thirdparty/simde", "thirdparty/fmt/include", "thirdparty/spdlog/include"]:
        command += ["-I", built / directory]
    command += [out / "bridge.cpp", root / "src/fh2_wheel_gear.cpp"]
    if not a.built_parser:
        command += [source / "src/input/sdl/wheel_mapping.cpp"]
    command += [out / "pad-name.lib", "-o", out / "bridge.exe"]
    run("compile", command)
    run("run", [out / "bridge.exe"], 15)
    record["status"] = "pass"
finally:
    record["finishedUtc"] = datetime.now(timezone.utc).isoformat()
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
