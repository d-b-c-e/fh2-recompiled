"""Run the SDK's existing pure input suites against an exact built runtime DLL.

Uses the vendored real Catch2 amalgamation and unmodified SDK test sources.
No application/runtime startup, SDL initialization, sink registration or device
output. Run in a VS x64 developer shell; serialize compilation on the shared rig.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--cxx", required=True, type=Path)
    parser.add_argument("--runtime-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    sdk, out, cxx = args.sdk.resolve(), args.out.resolve(), args.cxx.resolve()
    runtime = sdk / "out/win-amd64/rexruntime.dll"
    if sha(runtime) != args.runtime_sha256.upper():
        raise ValueError("Built runtime hash mismatch; refusing to load it")
    tests = [sdk / "tests/unit/input" / name for name in
             ("wheel_mapping_test.cpp", "wheel_test.cpp", "xinputd_ffb_test.cpp")]
    catch = sdk / "thirdparty/catch2/extras"
    sources = [catch / "catch_amalgamated.cpp", *tests]
    headers = [catch / "catch_amalgamated.hpp", sdk / "include/rex/input/sdl/wheel_mapping.h",
               sdk / "include/rex/input/sdl/wheel.h", sdk / "include/rex/input/xinputd_ffb.h",
               sdk / "include/rex/cvar.h"]
    for path in [*sources, *headers, sdk / "out/win-amd64/rexruntime.lib"]:
        if not path.is_file():
            raise FileNotFoundError(path)
    out.mkdir(parents=True, exist_ok=False)
    record = {"status": "fail", "startedUtc": datetime.now(timezone.utc).isoformat(), "steps": [],
              "gameLaunched": False, "graphicsInitialized": False, "physicalDevicesInitialized": False,
              "sinkRegistered": False, "ownerStateWritten": False, "productionSourcesReplaced": False,
              "inputSha256": {str(path): sha(path) for path in [runtime, *sources, *headers]},
              "scriptSha256": sha(Path(__file__))}

    def run(name, command, timeout):
        result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=timeout, cwd=out)
        (out / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        record["steps"].append({"name": name, "command": list(map(str, command)), "exitCode": result.returncode})
        if result.returncode:
            print(result.stdout + result.stderr, end="", flush=True)
        result.check_returncode()
        return result.stdout

    try:
        # Existing tests include this modular header. Forward it to the same
        # vendored Catch2's actual amalgamated header; no test macros are mocked.
        (out / "include/catch2").mkdir(parents=True)
        (out / "include/catch2/catch_test_macros.hpp").write_text(
            f'#include "{(catch / "catch_amalgamated.hpp").as_posix()}"\n')
        shutil.copyfile(runtime, out / "rexruntime.dll")
        command = [cxx, "-std=c++23", "-O1", "-fuse-ld=lld", "-D_DLL", "-D_MT", "-Xclang", "--dependent-lib=msvcrt",
                   "-DSPDLOG_COMPILED_LIB", "-DSPDLOG_FMT_EXTERNAL", "-I", out / "include", "-I", sdk / "include"]
        for directory in ("thirdparty/fmt/include", "thirdparty/spdlog/include", "thirdparty/simde"):
            command += ["-I", sdk / directory]
        command += [*sources, sdk / "out/win-amd64/rexruntime.lib", "-o", out / "sdk-input-tests.exe"]
        # One compiler driver, sequential translation units; no -j/native build.
        run("compile", command, 360)
        run("tests", [out / "sdk-input-tests.exe", "--rng-seed", "1", "--reporter", "junit", "--out", out / "tests.xml"], 30)
        suites = ET.parse(out / "tests.xml").getroot()
        record["testSuites"] = [dict(node.attrib) for node in suites.iter("testsuite")]
        if not record["testSuites"] or any(int(x.get("failures", 0)) or int(x.get("errors", 0)) for x in record["testSuites"]):
            raise ValueError("Incomplete or failing Catch2 result")
        record["testCases"] = sum(1 for _ in suites.iter("testcase"))
        if not record["testCases"]:
            raise ValueError("No existing test cases executed")
        record["executableSha256"] = sha(out / "sdk-input-tests.exe")
        record["runtimeCopySha256"] = sha(out / "rexruntime.dll")
        if record["runtimeCopySha256"] != args.runtime_sha256.upper() or sha(runtime) != record["runtimeCopySha256"]:
            raise ValueError("Runtime changed during fixture")
        run("imports", [cxx.parent / "llvm-readobj.exe", "--coff-imports", out / "sdk-input-tests.exe"], 15)
        record["status"] = "pass"
        print(f"PASS: {record['testCases']} existing Catch2 input/FFB test cases against the exact built runtime; no devices")
    finally:
        record["finishedUtc"] = datetime.now(timezone.utc).isoformat()
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
