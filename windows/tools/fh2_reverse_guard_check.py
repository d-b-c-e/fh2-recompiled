#!/usr/bin/env python3
"""Checks the H-shifter reverse speed limit (windows/src/fh2_reverse_guard.{h,cpp}, fh2_dbce_overrides.toml) without
the game:
- source: the two context hooks at the H-gate block labels beside the refusal hook, the stock paddle constants, and
  non_volatile_as_local left off (the hook reads r31 from ctx);
- with --generated: the hook emitted at each block label, before the block's first read of B+6696, in Manual
  (sub_82EBC460) and ManualWithClutch (sub_82EBCAD8); with --baseline, each handler gains only that line;
- with --cxx and --sdk: both generated gate blocks (label to the B+5826 store, verbatim) on fake guest memory, hooked
  and, with --baseline, unhooked: refused and allowed reverse, the exact limit, reversing, NaN, neutral, forward gears,
  no request, and a held R engaging once slow. Compare the guard dot to the pinned SDK vector instruction for
  three-axis, overflow and subnormal cases. The unhooked blocks must show reverse engaging at speed.

    python -I fh2_reverse_guard_check.py [--generated <dir>] [--baseline <dir>] [--cxx <clang++> --sdk <sdk> --out <dir>]
"""
import argparse
import difflib
import re
import subprocess
import tomllib
from pathlib import Path

HOOK = "Fh2GateReverseGuard"
BLOCKS = {"manual": ("sub_82EBC460", "loc_82EBC658", "ctx.r11.u64 = REX_LOAD_U8(ctx.r31.u32 + 6696);"),
          "clutch": ("sub_82EBCAD8", "loc_82EBCCC0", "ctx.r9.u64 = REX_LOAD_U8(ctx.r31.u32 + 6696);")}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--generated", type=Path)
parser.add_argument("--baseline", type=Path)
parser.add_argument("--cxx")
parser.add_argument("--sdk", type=Path)
parser.add_argument("--out", type=Path)
args = parser.parse_args()
windows = Path(__file__).resolve().parents[1]


def text(path):
    return (windows / path).read_text(encoding="utf-8").replace("\r\n", "\n")


# --- Source ------------------------------------------------------------------------------------------------------------
hooks = tomllib.loads(text("fh2_dbce_overrides.toml"))["midasm_hook"]
for address in (0x82EBC658, 0x82EBCCC0):
    assert hooks.count({"address": address, "name": HOOK, "context": True}) == 1, f"hook at {address:#x}: {hooks}"
assert sum(h.get("name") == HOOK for h in hooks) == 2, "two guard hooks"
assert any(h.get("name") == "Fh2GearReadRefused" and h["address"] == 0x82D84260 for h in hooks), "refusal hook kept"
assert tomllib.loads(text("fh2_manifest.toml"))["entrypoint"]["non_volatile_as_local"] is False, "r31 lives in ctx"
header = text("src/fh2_reverse_guard.h")
for needle in ("kRequest = 6696", "kVelocity = 192", "kForward = 144", "kLimitMph = 0x835FE378u + 360",
               "kMphToMps = 0x8200590Cu", "kNoRequest = 10", "simde_mm_vmsum_narrow_result((p[0] + p[2]) + p[1])",
               "!(double(forward) < double(limit))"):
    assert needle in header, f"fh2_reverse_guard.h: {needle}"
assert "void Fh2GateReverseGuard(PPCContext& ctx, uint8_t* base) { fh2::reverse_guard::Apply(base, ctx.r31.u32); }" \
    in text("src/fh2_reverse_guard.cpp"), "hook body"
assert re.search(r"set\(FH2_SOURCES\b[^)]*\bsrc/fh2_reverse_guard\.cpp\b", text("CMakeLists.txt")), "CMake entry"
for shared in sorted((windows.parent / "app").glob("*.toml")):
    assert "midasm_hook" not in shared.read_text(encoding="utf-8"), f"{shared.name}: the shared overrides stay hook-free"
print("source checks passed")


def function(tree, name):
    for path in sorted(tree.glob("fh2_recomp.*.cpp")):
        t = path.read_text(errors="replace")
        start = t.find(f"DEFINE_REX_FUNC({name}) {{")
        if start >= 0:
            return t, t[start:t.index("\n}\n", start) + 3]
    raise SystemExit(f"{name} is not in {tree}")


def code(body):
    return [s for s in (l.strip() for l in body.splitlines()) if s and not s.startswith("//")]


bodies, base_bodies = {}, {}
if args.generated:
    calls = sum(p.read_text(errors="replace").count(f"\t{HOOK}(ctx, base);") for p in args.generated.glob("fh2_recomp.*.cpp"))
    assert calls == 2, f"two hook calls in the tree, got {calls}"
    for mode, (name, label, first) in BLOCKS.items():
        whole, body = function(args.generated, name)
        assert f"extern void {HOOK}(PPCContext& ctx, uint8_t* base);" in whole[:whole.index(f"DEFINE_REX_FUNC({name})")]
        lines = code(body)
        at = lines.index(f"{label}:")
        assert lines[at + 1:at + 3] == [f"{HOOK}(ctx, base);", first], f"{mode}: {lines[at:at + 4]}"
        assert body.count(f"{HOOK}(ctx, base);") == 1, f"{mode}: one hook"
        bodies[mode] = body
    print("generated hook checks passed")
if args.baseline:
    assert args.generated, "--baseline needs --generated"
    for mode, (name, label, first) in BLOCKS.items():
        base_whole, base_body = function(args.baseline, name)
        assert HOOK not in base_whole, "the baseline must be generated without the guard"
        delta = [d for d in difflib.unified_diff(base_body.splitlines(), bodies[mode].splitlines(), lineterm="", n=0)
                 if not d.startswith(("---", "+++", "@@"))]
        assert [d.strip() for d in delta] == [f"+\t{HOOK}(ctx, base);".strip()], f"{mode} differs:\n" + "\n".join(delta)
        base_bodies[mode] = base_body
    print("baseline comparison passed: each handler gains only the hook call")

if not args.cxx:
    raise SystemExit(0)
assert args.generated and args.sdk and args.out, "the fixture needs --generated, --sdk and --out"
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)

macros, keep = [], False  # the generated header's preprocessor lines only, as in fh2_gear_refusal_check.py
for line in (args.generated / "fh2_pch.h").read_text().splitlines():
    if line.lstrip().startswith("#") and not line.lstrip().startswith("#include"):
        keep = True
    if keep:
        macros.append(line)
    keep = keep and line.rstrip().endswith("\\")
(out / "fh2_macros.h").write_text("\n".join(macros) + "\n", encoding="utf-8")


def block(body, mode, fn):
    """The gate block from its label to the B+5826 store, verbatim, as a function with the handler's locals and the
    constant registers it was entered with."""
    name, label, _ = BLOCKS[mode]
    src = body.splitlines()
    start = src.index(f"{label}:")
    stop = next(i for i in range(start, len(src)) if "REX_STORE_U8(ctx.r31.u32 + 5826, " in src[i])
    piece = src[start:stop + 1]
    defined = {l.strip()[:-1] for l in piece if re.fullmatch(r"\s*loc_[0-9A-F]{8}:", l)}
    assert set(re.findall(r"goto (loc_[0-9A-F]{8});", "\n".join(piece))) <= defined, f"{mode}: gotos stay inside"
    assert set(re.findall(r"\b(sub_[0-9A-F]{8})\(ctx, base\);", "\n".join(piece))) <= {"sub_82EBC3F0"}, f"{mode}: callees"
    prologue = src.index("\tREX_FUNC_PROLOGUE();")
    locals_ = []
    for line in src[prologue + 1:]:
        if line.strip().startswith(("const uint32_t rex_dispatch_address", "ctx.dispatch_address", "switch")):
            break
        locals_.append(line)
    regs = {}
    for line in src[:start]:  # the constant registers the block uses, as last set before it
        m = re.match(r"\s*ctx\.(r2[5-9])\.s64 = (-?\d+);", line)
        if m:
            regs[m.group(1)] = int(m.group(2))
    setup = "".join(f"\tctx.{r}.s64 = {v};\n" for r, v in sorted(regs.items()))
    return f'extern "C" REX_FUNC({fn}) {{\n\tREX_FUNC_PROLOGUE();\n' + "\n".join(locals_) + "\n" + setup + \
        "\n".join(piece) + "\n\treturn;\n}\n", regs


parts, info = [], {}
for mode in BLOCKS:
    piece, regs = block(bodies[mode], mode, f"gate_{mode}")
    parts.append(piece)
    info[mode] = regs
    if args.baseline:
        parts.append(block(base_bodies[mode], mode, f"stock_{mode}")[0])
print("block registers:", info)

harness = r'''// Generated by fh2_reverse_guard_check.py: the generated H-gate blocks on fake guest memory.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <string_view>
#include <rex/ppc/context.h>
#include "fh2_macros.h"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "fh2_reverse_guard.h"
static int g_events = 0, g_event[3];
extern "C" REX_FUNC(sub_82EBC3F0) { ++g_events; g_event[0] = ctx.r4.s32; g_event[1] = ctx.r5.s32; g_event[2] = ctx.r6.s32; }
void Fh2GateReverseGuard(PPCContext& ctx, uint8_t* base);
@BLOCKS@
using Block = void (*)(PPCContext&, uint8_t*);
static uint8_t* g;
constexpr uint32_t B = 0x40010000;
static void put32(uint32_t a, uint32_t v) { v = __builtin_bswap32(v); std::memcpy(g + a, &v, 4); }
static void putf(uint32_t a, float f) { uint32_t v; std::memcpy(&v, &f, 4); put32(a, v); }
static uint32_t get32(uint32_t a) { uint32_t v; std::memcpy(&v, g + a, 4); return __builtin_bswap32(v); }
struct Result { int target, state, events, prev, request; };
static Result Step(Block block, int request, int prev, int state, int current, float forward,
                   float y = 0, float z = 0, float ax = 1, float ay = 0, float az = 0) {
  std::memset(g + B, 0, 0x2000);
  g[B + 6696] = uint8_t(request); g[B + 5826] = uint8_t(prev); put32(B + 6700, uint32_t(state));
  g[B + 5008] = uint8_t(current); put32(B + 5036, 6); g[B + 5009] = 0xEE;
  putf(B + 192, forward); putf(B + 196, y); putf(B + 200, z);    // velocity, m/s
  putf(B + 144, ax); putf(B + 148, ay); putf(B + 152, az);       // forward axis
  putf(fh2::reverse_guard::kLimitMph, 15.0f); putf(fh2::reverse_guard::kMphToMps, 0.44704f);
  PPCContext ctx{};
  ctx.r31.u64 = B; ctx.r1.u64 = 0x40080000;
  g_events = 0;
  block(ctx, g);
  return {g[B + 5009], int(get32(B + 6700)), g_events, g[B + 5826], g[B + 6696]};
}
static int checks = 0, failures = 0, hazards = 0;
static void check(bool ok, const char* mode, const char* what) {
  ++checks;
  if (!ok) { ++failures; std::printf("FAIL %s: %s\n", mode, what); }
}
static bool DotMatchesSdk() {
  const auto velocity = simde_mm_set_ps(fh2::reverse_guard::LoadF32(g, B + 192),
                                        fh2::reverse_guard::LoadF32(g, B + 196),
                                        fh2::reverse_guard::LoadF32(g, B + 200), 0);
  const auto axis = simde_mm_set_ps(fh2::reverse_guard::LoadF32(g, B + 144),
                                    fh2::reverse_guard::LoadF32(g, B + 148),
                                    fh2::reverse_guard::LoadF32(g, B + 152), 0);
  const float stock = simde_mm_cvtss_f32(rex::ppc::simde_mm_vmsum3fp128(velocity, axis));
  const float guard = fh2::reverse_guard::ForwardVelocity(g, B);
  uint32_t stock_bits, guard_bits;
  std::memcpy(&stock_bits, &stock, 4); std::memcpy(&guard_bits, &guard, 4);
  return stock_bits == guard_bits;
}
static void Mode(const char* mode, Block block, bool fixed) {
  const float limit = float(15.0 * double(0.44704f));
  // Reverse requested while driving forward at 20 m/s from 3rd, idle state: refused with the fix.
  Result r = Step(block, 0, 3, 0, 3, 20.f);
  if (r.target == 0) ++hazards;
  if (!fixed) { check(r.target == 0 && r.state == 3 && r.events == 1, mode, "stock: reverse engages at speed"); return; }
  check(r.target == 0xEE && r.state == 0 && r.events == 0, mode, "R at 20 m/s: no target, no state, no event");
  check(r.prev == 10 && r.request == 10, mode, "R at 20 m/s: no request this step, remembered as 10");
  r = Step(block, 0, 3, 0, 3, 5.f);
  check(r.target == 0 && r.state == 3 && r.events == 1 && g_event[0] == 0 && g_event[1] == 3 && g_event[2] == 3, mode,
        "R at 5 m/s: engages as stock");
  check(Step(block, 0, 3, 0, 3, limit).target == 0xEE, mode, "R at exactly the limit: refused");
  check(Step(block, 0, 3, 0, 3, std::nextafter(limit, 0.f)).target == 0, mode, "R just below the limit: allowed");
  check(Step(block, 0, 3, 0, 3, -20.f).target == 0, mode, "R while rolling backwards: allowed");
  r = Step(block, 0, 3, 0, 3, -std::numeric_limits<float>::max(),
           -std::numeric_limits<float>::max(), 0, 0.70710677f, 0.70710677f, 0);
  check(r.target == 0xEE && r.events == 0, mode, "finite negative overflow: refused");
  check(DotMatchesSdk() && std::isnan(fh2::reverse_guard::ForwardVelocity(g, B)), mode,
        "finite negative overflow: SDK NaN dot bits");
  r = Step(block, 0, 3, 0, 3, 9.f, -4.f, 3.f, 0.8f, -0.2f, 0.1f);
  check(r.target == 0xEE && DotMatchesSdk(), mode, "three-axis dot: SDK bits and refusal");
  r = Step(block, 0, 3, 0, 3, -std::numeric_limits<float>::min(), 0, 0, 0.5f);
  const float tiny = fh2::reverse_guard::ForwardVelocity(g, B);
  check(r.target == 0 && tiny == 0 && std::signbit(tiny) && DotMatchesSdk(), mode,
        "signed subnormal: SDK negative zero dot and allowed reverse");
  check(Step(block, 0, 3, 0, 3, std::numeric_limits<float>::quiet_NaN()).target == 0xEE, mode, "NaN: refused, as stock");
  r = Step(block, 9, 3, 0, 3, 20.f);
  check(r.target == 9 && r.state == 3 && r.events == 0, mode, "neutral at speed: as stock");
  for (int gear = 1; gear <= 8; ++gear) {
    r = Step(block, gear, 9, 0, 9, 20.f);
    check(r.target == (gear < 6 ? gear : 5) && r.state == 3 && r.events == 1, mode, "forward gears at speed: as stock");
  }
  r = Step(block, 10, 3, 0, 3, 20.f);
  check(r.target == 0xEE && r.state == 0 && r.events == 0 && r.prev == 10, mode, "no request: nothing");
  // A held R: refused while fast (remembered 10), then the intake restores 0 and the car is slow: it engages.
  Step(block, 0, 3, 0, 3, 20.f);
  r = Step(block, 0, 10, 0, 3, 5.f);
  check(r.target == 0 && r.state == 3 && r.events == 1, mode, "held R engages once below the limit");
}
int main() {
  g = static_cast<uint8_t*>(VirtualAlloc(nullptr, 0x100000000ull, MEM_RESERVE, PAGE_NOACCESS));
  if (!g || !VirtualAlloc(g + 0x40000000, 0x100000, MEM_COMMIT, PAGE_READWRITE) ||
      !VirtualAlloc(g + 0x82000000, 0x10000, MEM_COMMIT, PAGE_READWRITE) ||
      !VirtualAlloc(g + 0x835F0000, 0x20000, MEM_COMMIT, PAGE_READWRITE)) return 2;
  Mode("manual", gate_manual, true);
  Mode("clutch", gate_clutch, true);
  const int fixed_hazards = hazards;
#ifdef HAVE_STOCK
  hazards = 0;
  Mode("manual stock", stock_manual, false);
  Mode("clutch stock", stock_clutch, false);
  std::printf("stock blocks: %d of 2 engage reverse at speed\n", hazards);
#endif
  std::printf("reverse guard: %d checks, %d failures, %d refused-speed reverses engaged with the fix\n", checks,
              failures, fixed_hazards);
  return failures ? 1 : 0;
}
'''
src = harness.replace("@BLOCKS@", ("#define HAVE_STOCK 1\n" if args.baseline else "") + "\n".join(parts))
(out / "harness.cpp").write_text(src, encoding="utf-8")
exe = out / "harness.exe"
subprocess.run([args.cxx, "-std=c++23", "-fuse-ld=lld", "-O1", "-msse4.1", "-Wno-unused-variable", "-Wno-unused-label",
                "-I", str(out), "-I", str(windows / "src"), "-I", str(args.sdk / "include"),
                "-I", str(args.sdk / "thirdparty/simde"), str(out / "harness.cpp"),
                str(windows / "src/fh2_reverse_guard.cpp"), "-o", str(exe)], check=True)
run = subprocess.run([str(exe)], capture_output=True, text=True)
print(run.stdout.strip())
assert run.returncode == 0 and "0 failures, 0 refused-speed reverses engaged with the fix" in run.stdout, "the guard"
assert not args.baseline or "stock blocks: 2 of 2 engage reverse at speed" in run.stdout, "negative control"
print("reverse guard fixture passed; the stock blocks engage reverse at speed")
