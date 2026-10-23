#!/usr/bin/env python3
"""Checks the FH2 Forza Data Out telemetry (windows/src/fh2_telemetry.{h,cpp}, fh2_dbce_overrides.toml) without the
game:
- source: the void hook at 0x8249B3F0 beside the refusal hook, off by default, 127.0.0.1 only, never blocking the
  game thread, the vendored encoder's hash, the lifecycle and the CMake entries;
- with --generated (windows/generated/default after codegen): the hook emitted once, in sub_8249A8E8, right before
  the bctrl at 0x8249B3F0, with the call and its continuation 0x8249B3F4 intact; with --baseline (a tree generated
  without it), sub_8249A8E8 gains only that line;
- with --cxx: fh2_telemetry.h on fake guest memory (reads and refusals) and its packets through the vendored encoder
  (lengths, offsets, gear mapping, stale frames, untraced fields zero, nonfinite rejection and valid packet bytes).

    python -I fh2_telemetry_check.py [--generated <dir>] [--baseline <dir>] [--cxx <clang++> --out <scratch>]
"""
import argparse
import difflib
import hashlib
import re
import subprocess
import tomllib
from pathlib import Path

HOOK, CONTROLLER = "Fh2TelemetryHandOff", "sub_8249A8E8"
VENDOR_SHA = "9DBE7E8B19106872DB10995E898B73609500A6F7CD99733E94AD74894394A7F9"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--generated", type=Path)
parser.add_argument("--baseline", type=Path)
parser.add_argument("--cxx")
parser.add_argument("--out", type=Path)
args = parser.parse_args()
windows = Path(__file__).resolve().parents[1]


def text(path):
    return (windows / path).read_text(encoding="utf-8").replace("\r\n", "\n")


# --- Source ------------------------------------------------------------------------------------------------------------
hooks = tomllib.loads(text("fh2_dbce_overrides.toml"))["midasm_hook"]
telemetry = {"address": 0x8249B3F0, "name": HOOK, "context": True}
assert hooks.count(telemetry) == 1 and len(hooks) == 4, f"hooks: {hooks}"
assert any(h.get("name") == "Fh2GearReadRefused" and h["address"] == 0x82D84260 for h in hooks), "refusal hook kept"
vendored = (windows / "src/vendor/forza_packet.h").read_bytes()
assert hashlib.sha256(vendored.replace(b"\r\n", b"\n")).hexdigest().upper() == VENDOR_SHA, \
    "vendored forza_packet.h differs from cf9e212 (aside from checkout line endings)"
assert VENDOR_SHA in text("src/vendor/README.md"), "vendor provenance"
cpp = text("src/fh2_telemetry.cpp")
assert 'REXCVAR_DEFINE_INT32(fh2_telemetry_port, 0, "FH2"' in cpp, "off by default"
assert "htonl(INADDR_LOOPBACK)" in cpp and not re.search(r"INADDR_ANY|inet_addr|inet_pton|getaddrinfo|bind\(", cpp), \
    "127.0.0.1 only, no other address and no listening socket"
assert "ioctlsocket(socket_, FIONBIO, &nonblocking)" in cpp, "nonblocking sends"
hook = cpp[cpp.index(f"void {HOOK}(PPCContext& ctx, uint8_t* base) {{"):]
assert hook.index("REXCVAR_GET(fh2_telemetry_port) <= 0) return;") < hook.index("Read(base"), "off: nothing is read"
assert "std::try_to_lock" in hook and "lock_guard" not in hook and "sendto" not in hook, "the game thread never blocks"
assert hook.index("if (!Read(base") < hook.index("g_sample = sample;") < hook.index("g_sampled = Clock::now();"), \
    "refused samples cannot replace the last accepted sample or refresh freshness"
main = text("src/main.cpp")
assert "fh2::telemetry::Start();" in main and main.index("fh2::telemetry::Stop();") < main.index("fh2::captura::Parar();")
cmake = text("CMakeLists.txt")
assert re.search(r"set\(FH2_SOURCES\b[^)]*\bsrc/fh2_telemetry\.cpp\b", cmake) and "target_link_libraries(fh2 PRIVATE ws2_32)" in cmake
for shared in sorted((windows.parent / "app").glob("*.toml")):
    assert "midasm_hook" not in shared.read_text(encoding="utf-8"), f"{shared.name}: the shared overrides stay hook-free"
print("source checks passed")


def function(tree, name):
    for path in sorted(tree.glob("fh2_recomp.*.cpp")):
        t = path.read_text(errors="replace")
        start = t.find(f"DEFINE_REX_FUNC({name}) {{")
        if start >= 0:
            return path, t, t[start:t.index("\n}\n", start) + 3]
    raise SystemExit(f"{name} is not in {tree}")


def code(body):
    return [s for s in (l.strip() for l in body.splitlines()) if s and not s.startswith("//")]


if args.generated:
    path, whole, body = function(args.generated, CONTROLLER)
    uses = {p.name: p.read_text(errors="replace").count(HOOK) for p in sorted(args.generated.glob("fh2_recomp.*.cpp"))}
    assert {k: v for k, v in uses.items() if v} == {path.name: 2}, f"the hook is used once, beside {CONTROLLER}: {uses}"
    assert f"extern void {HOOK}(PPCContext& ctx, uint8_t* base);" in whole[:whole.index(f"DEFINE_REX_FUNC({CONTROLLER})")]
    lines = code(body)
    at = lines.index(f"{HOOK}(ctx, base);")
    assert re.fullmatch(r"(ctx\.)?ctr\.u64 = ctx\.r11\.u64;", lines[at - 1]), f"after mtctr: {lines[at - 3:at]}"
    assert lines[at - 2] == "ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 80);" and lines[at - 4] == "ctx.r4.s64 = ctx.r1.s64 + 96;"
    assert lines[at + 1] == "ctx.lr = 0x8249B3F4;" and lines[at + 2].startswith("REX_CALL_INDIRECT_FUNC(") \
        and lines[at + 3] == "loc_8249B3F4:", f"the call and its continuation: {lines[at:at + 4]}"
    assert "case 0x8249B3F4: goto loc_8249B3F4;" in lines and "case 0x8249B3F0:" not in body, "continuation entry"
    print("generated hook checks passed")

if args.baseline:
    assert args.generated, "--baseline needs --generated"
    base_whole, base_body = function(args.baseline, CONTROLLER)[1:]
    assert HOOK not in base_whole, "the baseline must be generated without the telemetry hook"
    delta = [d for d in difflib.unified_diff(base_body.splitlines(), body.splitlines(), lineterm="", n=0)
             if not d.startswith(("---", "+++", "@@"))]
    assert [d.strip() for d in delta] == [f"+\t{HOOK}(ctx, base);".strip()], \
        f"{CONTROLLER} differs by more than the hook:\n" + "\n".join(delta)
    print(f"baseline comparison passed: {CONTROLLER} gains only the hook call")

if not args.cxx:
    raise SystemExit(0)
assert args.out, "--cxx needs --out"
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
harness = r'''// Generated by fh2_telemetry_check.py: fh2_telemetry.h on fake guest memory and its packets.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cmath>
#include <cstdio>
#include <limits>
#include <utility>
#include "fh2_telemetry.h"
using namespace fh2::telemetry;
static int checks = 0, failures = 0;
static void check(bool ok, const char* what) { ++checks; if (!ok) { ++failures; std::printf("FAIL %s\n", what); } }
static uint8_t* g;
static void put32(uint32_t a, uint32_t v) { v = __builtin_bswap32(v); std::memcpy(g + a, &v, 4); }
static void putf(uint32_t a, float f) { uint32_t v; std::memcpy(&v, &f, 4); put32(a, v); }
static float lef(const uint8_t* p, int o) { float f; std::memcpy(&f, p + o, 4); return f; }
static int32_t lei(const uint8_t* p, int o) { int32_t v; std::memcpy(&v, p + o, 4); return v; }
constexpr uint32_t kDyn = 0x40010000, kControls = 0x40020000;
static void Car(uint32_t vtable, uint8_t gear) {
  std::memset(g + kDyn, 0, kSpan + 64);
  put32(kDyn, vtable);
  putf(kDyn + kEngineSpeed, 400.f); putf(kDyn + kRedline, 700.f); putf(kDyn + kIdle, 80.f);
  g[kDyn + kGear] = gear; putf(kDyn + kSpeed, 31.25f);
  putf(kControls + 0, 0.5f); putf(kControls + 4, 1.0f); putf(kControls + 8, -0.25f);
  putf(kControls + 12, 0.0f); putf(kControls + 16, 2.0f);
}
int main() {
  g = static_cast<uint8_t*>(VirtualAlloc(nullptr, 0x100000000ull, MEM_RESERVE, PAGE_NOACCESS));
  if (!g || !VirtualAlloc(g + 0x40000000, 0x100000, MEM_COMMIT, PAGE_READWRITE)) return 2;
  Snapshot s;
  // Reads at the hand-over: either car-dynamics vtable, the controls and the five dynamics fields, big-endian.
  Car(kVtableA, 3);
  check(Read(g, kDyn, kControls, s), "vtable A is read");
  check(s.gas == 0.5f && s.brake == 1.0f && s.steer == -0.25f && s.clutch == 0.f && s.handbrake == 2.0f, "controls");
  check(s.engine == 400.f && s.redline == 700.f && s.idle == 80.f && s.speed == 31.25f && s.gear == 3, "dynamics");
  Car(kVtableB, 9);
  check(Read(g, kDyn, kControls, s) && s.gear == 9, "vtable B is read");
  // Refusals: another object, null, the MMIO window, a wrapping range; none of these is dereferenced.
  Car(0x82000000, 3);
  check(!Read(g, kDyn, kControls, s), "another vtable is refused");
  check(!Read(g, 0, kControls, s) && !Read(g, kDyn, 0, s), "null is refused");
  check(!Read(g, 0x7F000100, kControls, s) && !Read(g, kDyn, 0x7EFFFFF0, s), "the MMIO window is refused");
  check(!Read(g, 0xFFFFF800, kControls, s), "a wrapping range is refused");
  // Each sampled float: NaN and either infinity must fail before publication/byte conversion.
  const uint32_t fields[] = {kControls, kControls + 4, kControls + 8, kControls + 12, kControls + 16,
                             kDyn + kEngineSpeed, kDyn + kRedline, kDyn + kIdle, kDyn + kSpeed};
  for (uint32_t field : fields) {
    for (uint32_t bits : {0x7FC00000u, 0x7F800000u, 0xFF800000u}) {
      Car(kVtableA, 3); put32(field, bits);
      Snapshot rejected;
      check(!Read(g, kDyn, kControls, rejected), "nonfinite sampled float is refused");
    }
  }
  // Finite engine inputs can still overflow when converted to RPM, including stale constants.
  for (uint32_t field : {kDyn + kEngineSpeed, kDyn + kRedline, kDyn + kIdle}) {
    for (float value : {std::numeric_limits<float>::max(), -std::numeric_limits<float>::max()}) {
      Car(kVtableA, 3); putf(field, value);
      Snapshot rejected;
      check(!Read(g, kDyn, kControls, rejected), "nonfinite converted RPM is refused");
    }
  }
  // Packets through the vendored encoder.
  Car(kVtableA, 3); Read(g, kDyn, kControls, s);
  uint8_t p[324];
  check(Build(dbce::forza::FORZA_HORIZON_324, s, true, 1234, p, 324) == 324, "horizon is 324 bytes");
  check(lei(p, 0) == 1 && lei(p, 4) == 1234, "IsRaceOn 1 and the timestamp");
  check(std::fabs(lef(p, 8) - 700.f * kRadPerSecToRpm) < 0.01f && std::fabs(lef(p, 12) - 80.f * kRadPerSecToRpm) < 0.01f,
        "max = redline, idle, in RPM");
  check(std::fabs(lef(p, 16) - 400.f * kRadPerSecToRpm) < 0.01f, "current RPM");
  check(lef(p, dbce::forza::OFF_SPEED_HORIZON) == 31.25f, "speed in m/s");
  check(p[244 + 71] == 128 && p[244 + 72] == 255 && p[244 + 73] == 0 && p[244 + 74] == 255, "pedals 0..255, clamped");
  check(int8_t(p[dbce::forza::OFF_STEER_HORIZON]) == -31, "steer -127..127");
  check(p[dbce::forza::OFF_GEAR_HORIZON] == 3 && p[dbce::forza::OFF_SENTINEL_HORIZON] == 'F', "gear and sentinel");
  bool zero = true;
  for (int i = 20; i < 244 + 12; ++i) zero = zero && p[i] == 0;  // motion, wheels, identity, the Horizon insert, position
  for (int i = 244 + 16; i < 244 + 71; ++i) zero = zero && p[i] == 0;  // power .. race position
  check(zero && p[244 + 77] == 0 && p[244 + 78] == 0, "untraced fields stay zero");
  for (auto [guest, forza] : {std::pair{0, 0}, {1, 1}, {8, 8}, {9, 11}}) {
    s.gear = uint8_t(guest);
    Build(dbce::forza::FORZA_HORIZON_324, s, true, 0, p, 324);
    check(p[dbce::forza::OFF_GEAR_HORIZON] == forza, "gear 0 R, 1-8, 9 -> 11 N");
  }
  s.gear = 3;
  check(Build(dbce::forza::FORZA_FM7_DASH_311, s, true, 0, p, 324) == 311 && p[dbce::forza::OFF_GEAR_FM7] == 3, "fm7 is 311");
  // Stale: IsRaceOn 0, engine constants kept, gear N, the rest zero.
  check(Build(dbce::forza::FORZA_HORIZON_324, s, false, 99, p, 324) == 324 && lei(p, 0) == 0, "stale: IsRaceOn 0");
  check(lef(p, 8) > 0 && lef(p, 16) == 0 && lef(p, dbce::forza::OFF_SPEED_HORIZON) == 0, "stale: constants only");
  check(p[dbce::forza::OFF_GEAR_HORIZON] == 11 && p[244 + 71] == 0 && p[dbce::forza::OFF_STEER_HORIZON] == 0, "stale: gear N");
  check(Build(dbce::forza::FORZA_HORIZON_324, s, true, 0, p, 300) == 0, "a short buffer is refused");
  // Full pre-guard packet vectors for this sample: normal/clamped controls, both formats and stale state.
  for (auto layout : {dbce::forza::FORZA_HORIZON_324, dbce::forza::FORZA_FM7_DASH_311}) {
    for (bool fresh : {true, false}) {
      uint8_t expected[324]{};
      const uint32_t sled[] = {fresh ? 1u : 0u, 1234u, 0x45D0E40Fu, 0x443EFC66u, fresh ? 0x456EBB7Fu : 0u};
      std::memcpy(expected, sled, sizeof sled);
      const int dash = layout == dbce::forza::FORZA_HORIZON_324 ? 244 : 232;
      if (fresh) {
        const uint32_t speed = 0x41FA0000u;  // 31.25 m/s
        std::memcpy(expected + dash + 12, &speed, sizeof speed);
        expected[dash + 71] = 128; expected[dash + 72] = 255; expected[dash + 74] = 255;
        expected[dash + 76] = uint8_t(-31);
      }
      expected[dash + 75] = fresh ? 3 : 11;
      if (layout == dbce::forza::FORZA_HORIZON_324) expected[323] = 'F';
      check(Build(layout, s, fresh, 1234, p, 324) == int(layout) &&
            std::memcmp(p, expected, int(layout)) == 0, "valid packet bytes unchanged");
    }
  }
  // Finite out-of-range controls still clamp; finite speed and signed engine values are not normalized.
  Car(kVtableA, 3);
  putf(kControls, std::numeric_limits<float>::max());
  putf(kControls + 8, -std::numeric_limits<float>::max());
  putf(kDyn + kEngineSpeed, -400.f); putf(kDyn + kSpeed, std::numeric_limits<float>::max());
  check(Read(g, kDyn, kControls, s), "finite extreme controls, speed and signed RPM are accepted");
  Build(dbce::forza::FORZA_HORIZON_324, s, true, 0, p, 324);
  check(p[315] == 255 && int8_t(p[320]) == -127 && lef(p, 256) == std::numeric_limits<float>::max() &&
        lef(p, 16) < 0 && std::isfinite(lef(p, 16)), "finite values retain original clamp and serialization");
  std::printf("telemetry harness: %d checks, %d failures\n", checks, failures);
  return failures ? 1 : 0;
}
'''
(out / "harness.cpp").write_text(harness, encoding="utf-8")
exe = out / "harness.exe"
subprocess.run([args.cxx, "-std=c++23", "-fuse-ld=lld", "-O1", "-Wall", "-Wextra", "-Werror", "-I", str(windows / "src"),
                str(out / "harness.cpp"), "-o", str(exe)], check=True)
run = subprocess.run([str(exe)], capture_output=True, text=True)
print(run.stdout.strip())
assert run.returncode == 0 and ", 0 failures" in run.stdout, "telemetry harness"
print("telemetry harness passed")
