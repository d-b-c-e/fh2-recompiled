"""Build/run the production Windows sender against inert SDK adapters and real loopback UDP.

No game, graphics, guest code execution, physical devices or owner files. Cvar
adapters model the installed SDK's registry-locked Query API; this is not a
native SDK/app build. Outputs remain under the explicit --out directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cxx", required=True)
parser.add_argument("--out", required=True, type=Path)
parser.add_argument("--sdk", type=Path, help="Use built SDK headers/DLL instead of adapters; run in an x64 VS developer shell")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
args.out = args.out.resolve()
args.out.mkdir(parents=True, exist_ok=False)
stubs = args.out / "sdk-adapters"
(stubs / "rex/ppc").mkdir(parents=True, exist_ok=True)
(stubs / "rex/cvar.h").write_text(r'''
#pragma once
#include <cstdint>
#include <initializer_list>
#include <string>
#include <string_view>
#include <type_traits>
namespace fixture {
int Port();
std::string Format();
struct Registrar {
  Registrar range(int, int) { return {}; }
  Registrar allowed(std::initializer_list<const char*>) { return {}; }
};
}
namespace rex::cvar {
bool SetFlagByName(std::string_view name, std::string_view value);
template<class T> T Query(std::string_view) {
  if constexpr (std::is_same_v<T, int32_t>) return fixture::Port();
  else return fixture::Format();
}
}
#define REXCVAR_DEFINE_INT32(name, value, category, description) \
  int32_t& FLAGS_##name##_storage_() { static int32_t v = value; return v; } \
  [[maybe_unused]] static auto reg_##name = fixture::Registrar{}
#define REXCVAR_DEFINE_STRING(name, value, category, description) \
  std::string& FLAGS_##name##_storage_() { static std::string v = value; return v; } \
  [[maybe_unused]] static auto reg_##name = fixture::Registrar{}
#define REXCVAR_GET(name) FLAGS_##name##_storage_()
#define REXCVAR_QUERY(type, name) rex::cvar::Query<type>(#name)
''', encoding="utf-8")
(stubs / "rex/logging.h").write_text(
    '#pragma once\n#define REXLOG_WARN(...) ((void)0)\n#define REXLOG_INFO(...) ((void)0)\n', encoding="utf-8")
(stubs / "rex/ppc/context.h").write_text(
    '#pragma once\n#include <cstdint>\nstruct PPCContext { struct Reg { uint32_t u32{}; } r3, r4; };\n',
    encoding="utf-8")
exe = args.out / "sender-fixture.exe"
command = [args.cxx, "-std=c++23", "-O1"]
if args.sdk:
    sdk = args.sdk.resolve()
    command += ["-fuse-ld=lld", "-D_DLL", "-D_MT", "-Xclang", "--dependent-lib=msvcrt",
                "-DNOMINMAX", "-DWIN32_LEAN_AND_MEAN", "-DREX_PLATFORM_WINDOWS=1",
                "-DSPDLOG_FMT_EXTERNAL", "-DSPDLOG_COMPILED_LIB"]
    for directory in ["include", "thirdparty/fmt/include", "thirdparty/spdlog/include", "thirdparty/simde"]:
        command += ["-I", str(sdk / directory)]
    command += [str(sdk / "out/win-amd64" / name) for name in ["rexruntime.lib", "fmt.lib", "spdlog.lib"]]
    shutil.copyfile(sdk / "out/win-amd64/rexruntime.dll", args.out / "rexruntime.dll")
else:
    command += ["-Wall", "-Wextra", "-Werror", "-DFH2_FIXTURE_SDK_ADAPTERS", "-I", str(stubs)]
command += [str(root / "tools/fh2_telemetry_sender_fixture.cpp"), "-o", str(exe), "-lws2_32"]
receipt = {"status": "fail", "startedUtc": datetime.now(timezone.utc).isoformat(),
           "mode": "built-sdk" if args.sdk else "sdk-adapters", "gameExecuted": False,
           "graphicsInitialized": False, "physicalDeviceInitialized": False, "ownerStateWritten": False,
           "network": "127.0.0.1 only, ephemeral fixture receiver ports", "command": command}
receipt["sha256"] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest().upper() for name in
                     ["src/fh2_telemetry.cpp", "src/fh2_telemetry.h", "tools/fh2_telemetry_sender_fixture.cpp"]}
if args.sdk:
    receipt["sha256"]["rexruntime.dll"] = hashlib.sha256((args.out / "rexruntime.dll").read_bytes()).hexdigest().upper()
try:
    for step, invocation, timeout in [("compile", command, 120), ("run", [str(exe)], 15)]:
        result = subprocess.run(invocation, capture_output=True, text=True, timeout=timeout, cwd=args.out)
        (args.out / (step + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        receipt[step + "ExitCode"] = result.returncode
        print(result.stdout + result.stderr, end="", flush=True)
        result.check_returncode()
    receipt["sha256"]["sender-fixture.exe"] = hashlib.sha256(exe.read_bytes()).hexdigest().upper()
    receipt["status"] = "pass"
finally:
    receipt["finishedUtc"] = datetime.now(timezone.utc).isoformat()
    (args.out / "result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
