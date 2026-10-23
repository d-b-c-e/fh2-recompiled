#!/usr/bin/env python3
"""Checks the H-shifter refused-read fix (windows/fh2_dbce_overrides.toml, windows/src/fh2_wheel_gear.cpp) without
the game:
- the source: one Windows-only hook at 0x82D84260, the manifest include, the host function and its CMake entry, the
  disc-revision word check, and ../app with no hook;
- with --generated (windows/generated/default after codegen): the hook emitted in sub_82D841A0 and nowhere else,
  before `li r3,-1`, the accepted exit and the continuation entries as before; with --baseline (a tree generated
  without the hook), the reader differs only by the hook and the sampler sub_824972C0 not at all;
- with --cxx and --sdk: the generated reader and the sampler's gate slice, compiled from --generated against the SDK's
  PPCContext and the generated macros, on fake guest memory with the cached pad state set directly (the poll that
  fills it is not run). Each refusal x 16 raw values gives 10 and gear byte 10 (no new gate request); accepted reads
  map as before; the continuation entries resume with r1/LR/r31 back; with --baseline, a seeded differential
  requires the whole PPCContext and the committed guest memory to match the unhooked reader except r3 of a refused
  read. Negative controls (no hook effect, the withdrawn post-call comparison, the --baseline reader) must show the
  hazard.

    python -I fh2_gear_refusal_check.py [--generated <dir>] [--baseline <dir>]
        [--cxx <clang++> --sdk <shiftglue-sdk> --out <scratch>] [--emit-only]
"""
import argparse
import difflib
import re
import subprocess
import tomllib
from pathlib import Path

READER, SAMPLER, HOOK = "sub_82D841A0", "sub_824972C0", "Fh2GearReadRefused"
HOOK_BLOCK = [f"if ({HOOK}(ctx.r3)) {{", "goto loc_82D84264;", "}", "else {", "}", "ctx.r3.s64 = -1;"]
ENTRIES = ("0x82D841A0", "0x82D84214", "0x82D84228", "0x82D84258")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--generated", type=Path)
parser.add_argument("--baseline", type=Path)
parser.add_argument("--cxx")
parser.add_argument("--sdk", type=Path)
parser.add_argument("--out", type=Path)
parser.add_argument("--emit-only", action="store_true", help="write the fixture sources without compiling them")
args = parser.parse_args()
windows = Path(__file__).resolve().parents[1]
repo = windows.parent

# --- Source ------------------------------------------------------------------------------------------------------------
dbce = tomllib.loads((windows / "fh2_dbce_overrides.toml").read_text())
assert dbce == {"midasm_hook": [{"address": 0x82D84260, "name": HOOK, "registers": ["r3"],
                                 "jump_address_on_true": 0x82D84264}]}, f"fh2_dbce_overrides.toml: {dbce}"
manifest = tomllib.loads((windows / "fh2_manifest.toml").read_text())
assert manifest["entrypoint"]["includes"] == ["../app/overrides.toml", "fh2_dbce_overrides.toml"], "manifest include"
assert all("fh2_dbce" not in str(m.get("includes")) for m in manifest["modules"]), "the facades are not hooked"
for shared in sorted((repo / "app").glob("*.toml")):
    assert "midasm_hook" not in shared.read_text(), f"{shared.name}: the shared overrides stay hook-free"
host = (windows / "src/fh2_wheel_gear.cpp").read_text().replace("\r\n", "\n")
assert f"bool {HOOK}(PPCRegister& r3) {{\n  r3.s64 = 10;\n  return true;\n}}" in host, "host function"
assert host.count(HOOK) == 1 and "#include <rex/ppc/context.h>" in host, "one definition, the SDK register type"
cmake = (windows / "CMakeLists.txt").read_text()
assert re.search(r"set\(FH2_SOURCES\b[^)]*\bsrc/fh2_wheel_gear\.cpp\b", cmake), "CMake source entry"
disc = (windows / "tools/Test-DiscRevision.ps1").read_text()
assert "@{ a = 0x82D84258L; w = @('A861005C','48000008','3860FFFF','38210070');" in disc, "disc revision words"
print("source checks passed")


def function(tree, name):
    """The generated file holding `name`, its text, and the function's lines (stripped, comments dropped)."""
    for path in sorted(tree.glob("fh2_recomp.*.cpp")):
        text = path.read_text(errors="replace")
        start = text.find(f"DEFINE_REX_FUNC({name}) {{")
        if start >= 0:
            end = text.index("\n}\n", start) + 3
            return path, text, text[start:end]
    raise SystemExit(f"{name} is not in {tree}")


def code(body):
    return [s for s in (line.strip() for line in body.splitlines()) if s and not s.startswith("//")]


def after(lines, label):
    return lines[lines.index(label) + 1:]


reader = sampler = None
if args.generated:
    path, text, reader = function(args.generated, READER)
    sampler = function(args.generated, SAMPLER)[2]
    uses = {p.name: p.read_text(errors="replace").count(HOOK) for p in sorted(args.generated.glob("fh2_recomp.*.cpp"))}
    uses = {k: v for k, v in uses.items() if v}
    assert uses == {path.name: 2}, f"the hook is used once, only beside {READER}: {uses}"
    assert f"extern bool {HOOK}(PPCRegister& r3);" in text[:text.index(f"DEFINE_REX_FUNC({READER})")], "hook declaration"
    lines = code(reader)
    tail = after(lines, "loc_82D84260:")
    assert tail[:len(HOOK_BLOCK)] == HOOK_BLOCK and tail[len(HOOK_BLOCK)] == "loc_82D84264:", f"hook block: {tail[:8]}"
    accepted = after(lines, "loc_82D84258:")[:3]
    assert re.fullmatch(r"ctx\.r3\.s64 = int16_t\(REX_(STACK_)?LOAD_U16\(ctx\.r1\.u32 \+ 92\)\);", accepted[0]), accepted
    assert accepted[1:] == ["goto loc_82D84264;", "loc_82D84260:"], f"accepted exit: {accepted}"
    for entry in ENTRIES[1:]:
        assert f"case {entry}: goto loc_{entry[2:]};" in lines, f"continuation {entry}"
    assert "case 0x82D84260:" not in reader, "no entry at the refusal block"
    for table in ("fh2_register.cpp", "fh2_init.cpp"):
        found = re.findall(r"\{\s*(0x82D84[0-9A-F]{3}),\s*sub_82D841A0\s*\}", (args.generated / table).read_text())
        assert sorted(found) == sorted(ENTRIES), f"{table}: {found}"
    # The sampler's gate slice: flag test, then the read of action 7 for the device in r30.
    s = code(sampler)
    flag = s.index("sub_82D80388(ctx, base);")
    call = s.index(f"{READER}(ctx, base);")
    assert flag < call and {"ctx.r5.s64 = 7;", "ctx.r4.s64 = 0;", "ctx.r3.u64 = ctx.r30.u64;"} <= set(s[flag:call]), "slice"
    print("generated hook and entry checks passed")

if args.baseline:
    assert args.generated, "--baseline needs --generated"
    base_text, base_reader = function(args.baseline, READER)[1:]
    assert HOOK not in base_text, "the baseline must be generated without the hook"
    assert function(args.baseline, SAMPLER)[2] == sampler, "the sampler changed"
    delta = [d for d in difflib.unified_diff(base_reader.splitlines(), reader.splitlines(), lineterm="", n=0)
             if not d.startswith(("---", "+++", "@@"))]
    assert all(d.startswith("+") for d in delta) and [d[1:].strip() for d in delta] == HOOK_BLOCK[:-1], \
        "the reader differs by more than the hook:\n" + "\n".join(delta)
    print("baseline comparison passed: the reader gains only the hook, the sampler is unchanged")

# --- Semantic fixture ---------------------------------------------------------------------------------------------------
if not (args.cxx or args.emit_only):
    raise SystemExit(0)
assert args.generated and args.out and (args.sdk or args.emit_only), "the fixture needs --generated, --out and --sdk"
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)

# Only the generated header's preprocessor lines: its macros, without the SDK includes or inline helpers.
macros, keep = [], False
for line in (args.generated / "fh2_pch.h").read_text().splitlines():
    if line.lstrip().startswith("#") and not line.lstrip().startswith("#include"):
        keep = True
    if keep:
        macros.append(line)
    keep = keep and line.rstrip().endswith("\\")
(out / "fh2_macros.h").write_text("\n".join(macros) + "\n")


def callees(body):
    return set(re.findall(r"\b(sub_[0-9A-F]{8})\(ctx, base\);", body)) | set(re.findall(r"REX_TAIL_CALL\((\w+)\)", body))


frame = ["ctx.r12.u64 = ctx.lr;", "REX_STACK_STORE_U32(ctx.r1.u32 + -8, ctx.r12.u32);",
         "REX_STACK_STORE_U64(ctx.r1.u32 + -16, ctx.r31.u64);", "ea = -112 + ctx.r1.u32;"]
epilogue = ["ctx.r1.s64 = ctx.r1.s64 + 112;", "ctx.r12.u64 = REX_STACK_LOAD_U32(ctx.r1.u32 + -8);"]


def reader_source(body, name):
    lines = code(body)
    assert all(f in lines for f in frame + epilogue), f"{name}: the frame the continuation cases emulate"
    assert callees(body) == {"sub_82D82C30", "sub_82D801F0", "sub_82D915D0"}, f"{name}: callees {callees(body)}"
    return body


s_lines = sampler.splitlines()
first = next(i for i, l in enumerate(s_lines) if l.strip() == "ctx.r11.s64 = 10;")
flag_at = next(i for i, l in enumerate(s_lines) if "sub_82D80388(ctx, base);" in l)
end = re.search(r"goto (loc_[0-9A-F]{8});", next(l for l in s_lines[flag_at:] if "if (cr0.eq) goto" in l)).group(1)
stop = next(i for i, l in enumerate(s_lines) if l.strip() == f"{end}:")
assert first < flag_at < stop, "slice bounds"
slice_lines = s_lines[first:stop]
defined = {l.strip()[:-1] for l in slice_lines if re.fullmatch(r"\s*loc_[0-9A-F]{8}:", l)} | {end}
assert set(re.findall(r"goto (loc_[0-9A-F]{8});", "\n".join(slice_lines))) <= defined, "slice gotos stay inside"
assert callees("\n".join(slice_lines)) == {"sub_82D80388", READER}, "slice callees"
prologue = s_lines.index("\tREX_FUNC_PROLOGUE();")
locals_ = []
for line in s_lines[prologue + 1:]:
    if line.strip().startswith(("const uint32_t rex_dispatch_address", "ctx.dispatch_address", "switch")):
        break
    locals_.append(line)
assert locals_ and all(re.fullmatch(r"\s*(PPC\w+|uint32_t) \w+( = ctx\.\w+|\{\});", l) for l in locals_), locals_
slice_src = "\n".join(locals_ + slice_lines + [f"{end}:", "\treturn;"])

harness = r'''// Generated by fh2_gear_refusal_check.py: the generated H-shifter gate read and the sampler's gate slice on
// fake guest memory. MODE 0: the fix (src/fh2_wheel_gear.cpp linked). MODE 1: the hook has no effect. MODE 2: the
// withdrawn post-call comparison. MODE 3: the baseline reader, generated without the hook.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string_view>
#include <rex/ppc/context.h>
#include "fh2_macros.h"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

static uint32_t g_binding_code = 24, g_chord = 1, g_flag = 1;
static int g_reader_calls = 0;
constexpr uint32_t kDevice = 0x40001000, kFocus = 0x40003000, kListener = 0x40003100, kTable = 0x40003200,
                   kMasks = 0x40003300, kBinding = 0x40003400, kOut = 0x40004000, kStack = 0x40080000;
static uint8_t* g_base;

extern "C" REX_FUNC(sub_82D82C30) { ctx.r3.u64 = kBinding; }          // the action's first binding
extern "C" REX_FUNC(sub_82D801F0) { ctx.r3.u64 = g_chord; }           // its chord codes hold
extern "C" REX_FUNC(sub_82D915D0) { std::memmove(base + ctx.r3.u32, base + ctx.r4.u32, ctx.r5.u32); }  // memcpy
extern "C" REX_FUNC(sub_82D80388) { ctx.r3.u64 = g_flag; }            // Wheel class with a shifter

#if MODE == 1 || MODE == 2
bool Fh2GearReadRefused(PPCRegister&) { return false; }
#endif
@READER@
#if MODE == 2
static void Withdrawn(PPCContext& ctx, uint8_t* base) {
  const uint32_t device = ctx.r3.u32;
  sub_82D841A0(ctx, base);
  uint16_t raw;
  std::memcpy(&raw, base + device + 152, 2);
  if (ctx.r3.s32 == -1 && int16_t(__builtin_bswap16(raw)) != -1) ctx.r3.s64 = 10;
}
#define sub_82D841A0(c, b) (++g_reader_calls, Withdrawn(c, b))
#else
#define sub_82D841A0(c, b) (++g_reader_calls, sub_82D841A0(c, b))
#endif
extern "C" REX_FUNC(gear_slice) {
  REX_FUNC_PROLOGUE();
@SLICE@
}
#undef sub_82D841A0

static int checks = 0, failures = 0;
static void check(bool ok, const char* what, long long got) {
  ++checks;
  if (!ok) { ++failures; std::printf("FAIL %s (got %lld)\n", what, got); }
}
static void put32(uint32_t a, uint32_t v) { v = __builtin_bswap32(v); std::memcpy(g_base + a, &v, 4); }
static void put16(uint32_t a, uint16_t v) { v = __builtin_bswap16(v); std::memcpy(g_base + a, &v, 2); }
enum Refusal { kNone, kFocus_, kCode, kChord, kClass, kNoFlag };
static void Setup(Refusal refusal, int raw) {
  std::memset(g_base + kDevice, 0, 0x2000);
  std::memset(g_base + kFocus, 0, 0x1000);
  put32(kDevice + 40, kFocus); put32(kDevice + 52, 0);
  put32(kFocus, kListener); put32(kListener + 4, kTable); put32(kListener + 8, 1); put32(kTable, kMasks);
  put32(kMasks, refusal == kFocus_ ? 0x2 : 0x3);                     // bit 0 is context 0
  g_base[kDevice + 6] = refusal == kClass ? 0 : 1;
  g_base[kDevice + 15] = refusal == kNoFlag ? 0 : 1;
  put16(kDevice + 152, uint16_t(int16_t(raw)));                       // sThumbRX of the cached XINPUT_STATE
  g_binding_code = refusal == kCode ? 25 : 24;
  put32(kBinding + 8, g_binding_code);
  g_chord = refusal == kChord ? 0 : 1;
  g_flag = 1;
}
static PPCContext Fresh() {
  PPCContext ctx{};
  ctx.r1.u64 = kStack; ctx.lr = 0x82497350; ctx.r31.u64 = 0x5151;
  return ctx;
}
static int32_t Read(PPCContext& ctx) {
  ctx.r3.u64 = kDevice; ctx.r4.u64 = 0; ctx.r5.u64 = 7;
  sub_82D841A0(ctx, g_base);
  check(ctx.r1.u32 == kStack && ctx.lr == 0x82497350 && ctx.r31.u64 == 0x5151, "r1/LR/r31 restored", ctx.r1.u32);
  check(ctx.dispatch_address == 0, "dispatch address cleared", ctx.dispatch_address);
  return ctx.r3.s32;
}
static int Gear(Refusal refusal, int raw) {
  Setup(refusal, raw);
  PPCContext ctx = Fresh();
  ctx.r30.u64 = kDevice; ctx.r31.u64 = kOut; g_base[kOut + 24] = 0xEE;
  gear_slice(ctx, g_base);
  return g_base[kOut + 24];
}
static int32_t Resume(uint32_t entry, Refusal refusal, int raw, uint64_t r3) {
  Setup(refusal, raw);
  PPCContext ctx = Fresh();
  // The frame the prologue built: LR at old r1 - 8, r31 at old r1 - 16, back chain at the new r1.
  put32(kStack - 8, 0x82497350);
  uint64_t r31 = __builtin_bswap64(0x5151ull); std::memcpy(g_base + kStack - 16, &r31, 8);
  put32(kStack - 112, kStack);
  put16(kStack - 112 + 92, uint16_t(int16_t(raw)));                   // the state copy the memcpy made
  ctx.r1.u64 = kStack - 112; ctx.r31.u64 = kDevice; ctx.r3.u64 = r3; ctx.lr = 0; ctx.dispatch_address = entry;
  sub_82D841A0(ctx, g_base);
  check(ctx.r1.u32 == kStack && ctx.lr == 0x82497350 && ctx.r31.u64 == 0x5151, "resume restores r1/LR/r31", entry);
  return ctx.r3.s32;
}

#ifdef HAVE_BASE
// Seeded differential against the baseline reader: the whole PPCContext and the committed guest memory must match,
// except r3 of a refused read (10 against -1).
static void Seed(PPCContext& c, uint32_t s) {
  auto* p = reinterpret_cast<uint8_t*>(&c);
  for (size_t i = 0; i < sizeof c; ++i) { s = s * 1103515245u + 12345u; p[i] = uint8_t(s >> 16); }
  c.r1.u64 = kStack; c.r3.u64 = kDevice; c.r4.u64 = 0; c.r5.u64 = 7; c.dispatch_address = 0;
}
static int Differential(Refusal refusal, int raw, uint32_t seed) {
  static uint8_t before[0x100000], after_fix[0x100000];
  Setup(refusal, raw);
  for (uint32_t a = kStack - 0x400; a < kStack; a += 4) put32(a, seed ^ a);   // the frame below r1
  std::memcpy(before, g_base + 0x40000000, sizeof before);
  alignas(64) static PPCContext fixed, base;
  Seed(fixed, seed); std::memcpy(&base, &fixed, sizeof base);
  sub_82D841A0(fixed, g_base);
  std::memcpy(after_fix, g_base + 0x40000000, sizeof after_fix);
  std::memcpy(g_base + 0x40000000, before, sizeof before);
  base_sub_82D841A0(base, g_base);
  const bool memory = std::memcmp(after_fix, g_base + 0x40000000, sizeof after_fix) == 0;
  bool r3 = fixed.r3.s64 == base.r3.s64;
  if (refusal != kNone) { r3 = fixed.r3.s64 == 10 && base.r3.s64 == -1; fixed.r3 = base.r3; }
  return memory && r3 && std::memcmp(&fixed, &base, sizeof fixed) == 0;
}
#endif

int main() {
  g_base = static_cast<uint8_t*>(VirtualAlloc(nullptr, 0x100000000ull, MEM_RESERVE, PAGE_NOACCESS));
  if (!g_base || !VirtualAlloc(g_base + 0x40000000, 0x100000, MEM_COMMIT, PAGE_READWRITE)) return 2;
  const Refusal refusals[] = {kFocus_, kCode, kChord, kClass, kNoFlag};
  const char* names[] = {"", "focus", "code", "chord", "class", "flag"};
  const int raws[] = {-32768, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 255, 256, 32767};
  char what[96];
  const int fixed = MODE == 0 ? 10 : -1;     // what a refused read returns in this build
  for (Refusal r : refusals)
    for (int raw : raws) {
      Setup(r, raw); PPCContext ctx = Fresh();
      std::snprintf(what, sizeof what, "refused (%s) read, raw %d", names[r], raw);
      check(Read(ctx) == fixed, what, ctx.r3.s32);
    }
  // Accepted reads keep the raw value, big-endian; the sampler maps it as before: -1 -> 0, 0 -> 9, 1..8 as is,
  // 9 and above stay 10, below -1 its low byte.
  for (int raw : raws) {
    Setup(kNone, raw); PPCContext ctx = Fresh();
    std::snprintf(what, sizeof what, "accepted read, raw %d", raw);
    check(Read(ctx) == raw, what, ctx.r3.s32);
    const int expected = raw == -1 ? 0 : raw == 0 ? 9 : raw >= 9 ? 10 : raw < -1 ? uint8_t(raw) : raw;
    const int gear = Gear(kNone, raw);
    std::snprintf(what, sizeof what, "accepted gear, raw %d", raw);
    check(gear == expected, what, gear);
  }
  Setup(kNone, 0); put16(kDevice + 152, 0x0100);
  { PPCContext ctx = Fresh(); check(Read(ctx) == 256, "bytes 01 00 read as 256 (big-endian)", ctx.r3.s32); }
  check(Gear(kNone, 1) == 1, "bytes 00 01 read as gear 1", Gear(kNone, 1));
  Setup(kNone, 3); g_flag = 0; g_reader_calls = 0;
  { PPCContext ctx = Fresh(); ctx.r30.u64 = kDevice; ctx.r31.u64 = kOut; g_base[kOut + 24] = 0xEE; gear_slice(ctx, g_base);
    check(g_base[kOut + 24] == 10 && g_reader_calls == 0, "no shifter: no read, gear 10", g_base[kOut + 24]); }
  // Refused reads through the sampler (the flag test passes, the reader refuses): the fix gives 10 everywhere; without
  // it, and with the withdrawn comparison when the cached raw is -1, the gear byte is 0, reverse.
  int hazards = 0;
  for (Refusal r : refusals)
    for (int raw : raws) {
      const int gear = Gear(r, raw);
      const int expected = MODE == 0 ? 10 : MODE == 2 ? (raw == -1 ? 0 : 10) : 0;
      std::snprintf(what, sizeof what, "refused (%s) gear, raw %d", names[r], raw);
      check(gear == expected, what, gear);
      hazards += gear == 0;
    }
#ifdef HAVE_BASE
  int cases = 0;
  for (Refusal r : {kNone, kFocus_, kCode, kChord, kClass, kNoFlag})
    for (int raw : raws)
      for (uint32_t seed : {1u, 0x9E3779B9u, 0xDEADBEEFu}) {
        std::snprintf(what, sizeof what, "differential (%s), raw %d, seed %08X", r ? names[r] : "accepted", raw, seed);
        check(Differential(r, raw, seed), what, 0);
        ++cases;
      }
  std::printf("differential against the baseline reader: %d seeded cases\n", cases);
#endif
  // Continuation entries: after the binding walk (r3 = binding), after the chord test (r3 = result), after the copy.
  check(Resume(0x82D84214, kNone, 5, kBinding) == 5, "resume 0x82D84214 accepted", 0);
  check(Resume(0x82D84214, kCode, 5, kBinding) == fixed, "resume 0x82D84214 refused (code)", 0);
  check(Resume(0x82D84228, kNone, 6, 1) == 6, "resume 0x82D84228 accepted", 0);
  check(Resume(0x82D84228, kNone, 6, 0) == fixed, "resume 0x82D84228 refused (chord)", 0);
  check(Resume(0x82D84258, kNone, 3, 0) == 3, "resume 0x82D84258 reads the copy", 0);
  check(Resume(0x82D84258, kNone, -1, 0) == -1, "resume 0x82D84258 keeps a held REVERSE", 0);
  std::printf("MODE %d: %d checks, %d failures, %d refused reads became reverse\n", MODE, checks, failures, hazards);
  return failures ? 1 : 0;
}
'''

builds = [("fix", 0, reader, True), ("no-effect", 1, reader, False), ("withdrawn", 2, reader, False)]
if args.baseline:
    builds.append(("baseline", 3, base_reader, False))
results = {}
for name, mode, body, link_hook in builds:
    folder = out / name
    folder.mkdir(exist_ok=True)
    primary = (f"extern bool {HOOK}(PPCRegister& r3);\n" if HOOK in body else "") + reader_source(body, name)
    if mode == 0 and args.baseline:   # the unhooked reader beside the fix, renamed, for the seeded differential
        primary += "\n#define HAVE_BASE 1\n" + reader_source(base_reader, "baseline").replace(READER, f"base_{READER}")
    src = harness.replace("@READER@", primary).replace("@SLICE@", slice_src)
    (folder / "harness.cpp").write_text(src)
    if args.emit_only:
        continue
    exe = folder / "harness.exe"
    sources = [folder / "harness.cpp"] + ([windows / "src/fh2_wheel_gear.cpp"] if link_hook else [])
    subprocess.run([args.cxx, "-std=c++20", "-O1", "-msse4.1", f"-DMODE={mode}", "-Wno-unused-variable",
                    "-Wno-unused-label", "-I", str(out), "-I", str(args.sdk / "include"),
                    "-I", str(args.sdk / "thirdparty/simde"), *map(str, sources), "-o", str(exe)], check=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    print(run.stdout.strip())
    results[name] = (run.returncode, run.stdout)
if args.emit_only:
    print(f"fixture sources written to {out}")
    raise SystemExit(0)
assert results["fix"][0] == 0 and "0 failures, 0 refused reads became reverse" in results["fix"][1], "the fix"
assert not args.baseline or "differential against the baseline reader: 288 seeded cases" in results["fix"][1], "differential"
for control in [n for n in results if n != "fix"]:
    code_, text = results[control]
    hazards = int(re.search(r"(\d+) refused reads became reverse", text).group(1))
    assert code_ == 0 and hazards > 0, f"negative control {control} did not show the hazard"
print("semantic fixture passed; every negative control shows the hazard")
