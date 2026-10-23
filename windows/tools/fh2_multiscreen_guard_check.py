#!/usr/bin/env python3
"""Checks the multiscreen null-peer guard (the sub_82E81C20 hook in app/src/fh2_correcoes.cpp, cvar
fh2_multiscreen_null_peer_guard, off by default) without the game or a build.
- The source: off by default; the original runs once, first; off, nothing else runs; the hook never writes ctx and
  writes only settings+25, holder+8, +52, +53 and the gate global.
- The real fh2_correcoes.cpp, built with stub SDK headers on a fake guest (4 GB reserved; only the holder, gate and
  server pages committed, so guest page 0 is unmapped and any null access ends the run). A fake original leaves a
  scripted multiscreen state and sets registers. Each state runs unhooked and hooked, with the full context compared:
    off: all six states byte-identical, the server without a peer included, nothing logged;
    on:  the default and client roles, a server that failed to allocate, a hosting server and one whose host failed
         are byte-identical with nothing logged; the server without a peer changes in exactly settings+25 (one byte),
         holder+8..+11 (one word), +52 and +53 (one byte each) and the gate word, with no neighbour, no server byte
         and no ctx change, and one error naming its state.
- The direct consumers that read this state without the server getter, compiled from their generated bodies
  (--generated): the role predicates sub_82E79170/79198/791C8 (called with the settings, as their callers pass them)
  and the holder readers sub_82E797C8, 78CC0, 78CE0 and 78D00. After the guarded setup of a server without a peer, each
  must run without touching page 0 and come back "no role" / "no server". A mutant that only clears the holder (the
  earlier e7c0766 behaviour) must crash in sub_82E79198, which writes server+2280 through holder+8: guest 0x8E8.
- A mutant without the peer test must change the two states with a peer.
- The setup's only caller is game init sub_82493A58, the holder getter returns 0x833F2D34, the settings getter
  0x833F2D88, and the application's methods and camera gate test the gate global 0x8342B5DC first.
A fake cannot show that a live run reaches the hook, what the peer setup does on the host, or that the peer's own
callbacks (which get the raw server, not this state) are contained; this guard does not claim the last.

    python -I fh2_multiscreen_guard_check.py --cxx <clang++> --out <scratch folder> --generated <windows/generated/default>
"""
import argparse
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cxx", required=True)
parser.add_argument("--out", required=True, type=Path)
parser.add_argument("--generated", required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)

# --- Source ---------------------------------------------------------------------------------------------------------
source = (root / "app/src/fh2_correcoes.cpp").read_text().replace("\r\n", "\n")
assert 'REXCVAR_DEFINE_BOOL(fh2_multiscreen_null_peer_guard, false, "FH2",' in source, "off by default"
body = source[source.index("REX_HOOK_RAW(sub_82E81C20) {"):]
body = body[:body.index("\n}\n")]
lines = [l.strip() for l in body.split("\n")[1:]]
assert lines[0] == "constexpr uint32_t kHolder = 0x833F2D34, kSettings = 0x833F2D88, kGate = 0x8342B5DC;", lines[0]
assert lines[1:5] == ["__imp__sub_82E81C20(ctx, base);", "if (!REXCVAR_GET(fh2_multiscreen_null_peer_guard)) {",
                      "return;", "}"], "the original first; off, nothing else"
assert body.count("__imp__sub_82E81C20(ctx, base);") == 1, "the original runs once"
assert not re.search(r"ctx\.[\w.]+\s*(=[^=]|\+\+|--|[-+|&^]=)", body), "never writes ctx"
writes = re.findall(r"GuardarU32\(base, ([^,]+),|base\[([^\]]+)\]\s*=[^=]", body)
assert sorted(w[0] or w[1] for w in writes) == ["kGate", "kHolder + 52", "kHolder + 53", "kHolder + 8", "kSettings + 25"], writes
assert "if (server == 0 || CargarU32(base, server + 2100) != 0) {" in body, "only a server without a peer"
assert "fh2_correcoes.cpp" in (root / "windows/CMakeLists.txt").read_text(), "built into the Windows app"

generated = {}
for p in args.generated.resolve().glob("*.cpp"):
    for m in re.finditer(r"DEFINE_REX_FUNC\((sub_[0-9A-F]+)\) \{.*?\n\}", p.read_text(errors="replace"), re.S):
        generated[m.group(1)] = m.group(0)
callers = {n for n, t in generated.items() if re.search(r"\bsub_82E81C20\(ctx, base\);", t)}
assert callers == {"sub_82493A58"}, callers
assert "-2093023232" in generated["sub_82E79D70"] and "11572" in generated["sub_82E79D70"], "holder 0x833F2D34"
assert "-2093023232" in generated["sub_82E790B8"] and "11656" in generated["sub_82E790B8"], "settings 0x833F2D88"
for name in ("sub_825C96E0", "sub_825C8A68", "sub_825C83F0"):
    text = generated[name]
    first = text.index("REX_LOAD_U32(ctx.r11.u32 + -18980)")
    assert "ctx.r11.s64 = -2092761088;" in text[:first] and "sub_82E79D70(ctx, base);" not in text[:first], \
        f"{name} tests the gate global before anything else"
CONSUMERS = ["sub_82E79170", "sub_82E79198", "sub_82E791C8", "sub_82E797C8", "sub_82E78CC0", "sub_82E78CE0", "sub_82E78D00"]
for name in CONSUMERS:
    assert not re.search(r"\bsub_[0-9A-F]+\(ctx, base\);", generated[name]), f"{name} calls nothing the fixture lacks"

# --- Build on a fake guest ------------------------------------------------------------------------------------------
stub = out / "stub/rex"
(stub / "ppc").mkdir(parents=True, exist_ok=True)
gprs = ", ".join(f"r{i}" for i in range(32))
(stub / "ppc/func.h").write_text(r"""#pragma once
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
union PPCRegister { uint64_t u64; int64_t s64; uint32_t u32; int32_t s32; uint8_t u8; };
struct PPCXERRegister { uint32_t so, ov, ca; };
struct PPCCRRegister {
  bool lt, gt, eq, so;
  template <class T> void compare(T a, T b, const PPCXERRegister&) { lt = a < b; gt = a > b; eq = a == b; }
};
struct PPCContext { PPCRegister """ + gprs + r"""; PPCCRRegister cr0, cr1, cr2, cr3, cr4, cr5, cr6, cr7;
  double f[32]; uint64_t lr; uint32_t dispatch_address; };
#define REX_FUNC(x) void x([[maybe_unused]] PPCContext& ctx, [[maybe_unused]] uint8_t* base)
#define REX_EXTERN(x) extern "C" REX_FUNC(x)
#define DEFINE_REX_FUNC(name) extern "C" REX_FUNC(name)
#define REX_FUNC_PROLOGUE() ((void)0)
inline uint32_t FixtureLoad32(const uint8_t* b, uint32_t p) { uint32_t v; memcpy(&v, b + p, 4); return __builtin_bswap32(v); }
inline void FixtureStore32(uint8_t* b, uint32_t p, uint32_t v) { v = __builtin_bswap32(v); memcpy(b + p, &v, 4); }
#define REX_LOAD_U8(a) (base[uint32_t(a)])
#define REX_LOAD_U32(a) FixtureLoad32(base, uint32_t(a))
#define REX_STORE_U32(a, v) FixtureStore32(base, uint32_t(a), uint32_t(v))
#define REX_CALL_INDIRECT_FUNC(x) do { std::printf("INDIRECT %08X\n", unsigned(x)); std::fflush(stdout); std::exit(7); } while (0)
""")
(stub / "hook.h").write_text('#pragma once\n#include "ppc/func.h"\n#define REX_HOOK_RAW(name) extern "C" REX_FUNC(name)\n')
(stub / "cvar.h").write_text(r"""#pragma once
#define REXCVAR_DEFINE_BOOL(name, default_val, category, desc) \
  bool& FLAGS_##name##_storage_() { static bool storage = (default_val); return storage; }
#define REXCVAR_GET(name) (FLAGS_##name##_storage_())
""")
(stub / "logging.h").write_text(r"""#pragma once
#include <format>
#include <string>
#include <vector>
inline std::vector<std::string>& FixtureLog() { static std::vector<std::string> log; return log; }
#define REXLOG_WARN(...) FixtureLog().push_back("W " + std::format(__VA_ARGS__))
#define REXLOG_ERROR(...) FixtureLog().push_back("E " + std::format(__VA_ARGS__))
""")
(out / "consumers.cpp").write_text('#include "rex/ppc/func.h"\n' + "\n".join(generated[n] for n in CONSUMERS) + "\n")
others = [m for m in re.findall(r"REX_EXTERN\(__imp__(sub_[0-9A-F]+)\);", source) if m != "sub_82E81C20"]
harness = r"""
#include <windows.h>
#include <string>
#include "rex/ppc/func.h"
#include "rex/logging.h"
""" + "\n".join(f'extern "C" REX_FUNC(__imp__{n}) {{}}' for n in others) + "\n" + \
    "\n".join(f'extern "C" REX_FUNC({n});' for n in CONSUMERS) + r"""
extern "C" REX_FUNC(sub_82E81C20);
bool& FLAGS_fh2_multiscreen_null_peer_guard_storage_();
constexpr uint32_t kHolder = 0x833F2D34, kSettings = 0x833F2D88, kGate = 0x8342B5DC;
// Every byte of the server, the peer and the gate value is non-zero, so a cleared word shows in all four bytes.
constexpr uint32_t kServer = 0x41424344, kPeer = 0x45464748, kClient = 0x41424C00, kGateOn = 0x11223344;
constexpr uint32_t kPages[] = {kHolder & ~0xFFFu, kGate & ~0xFFFu, kServer & ~0xFFFu};
struct Script { const char* name; uint8_t role, client_role; uint32_t client, server, state, peer, gate; uint8_t active, side; };
Script g_script; int g_calls = 0;
extern "C" REX_FUNC(__imp__sub_82E81C20) {
  ++g_calls;
  base[kSettings + 25] = g_script.role;
  FixtureStore32(base, kSettings + 40, g_script.client_role);
  FixtureStore32(base, kHolder + 4, g_script.client);
  FixtureStore32(base, kHolder + 8, g_script.server);
  base[kHolder + 52] = g_script.active;
  base[kHolder + 53] = g_script.side;
  FixtureStore32(base, kGate, g_script.gate);
  if (g_script.server) { FixtureStore32(base, g_script.server + 2096, g_script.state); FixtureStore32(base, g_script.server + 2100, g_script.peer); }
  ctx.r3.u64 = 0x1234; ctx.r4.u64 = 0x5678; ctx.r11.u64 = 0x9ABC; ctx.f[1] = 2.5; ctx.cr0.eq = true;
}
struct Run { uint8_t pages[3][4096]; PPCContext ctx; size_t logs; int calls; std::string log; };
void Fresh(uint8_t* base) {
  memset(base + kPages[0], 0xA5, 4096); memset(base + kPages[1], 0xC3, 4096); memset(base + kPages[2], 0x5A, 4096);
  FixtureLog().clear(); g_calls = 0;
}
Run Go(uint8_t* base, bool hooked) {
  Fresh(base);
  PPCContext ctx; memset(&ctx, 0x3C, sizeof ctx); ctx.lr = 0x82493B00;
  if (hooked) sub_82E81C20(ctx, base); else __imp__sub_82E81C20(ctx, base);
  Run r; for (int p = 0; p < 3; ++p) memcpy(r.pages[p], base + kPages[p], 4096);
  r.ctx = ctx; r.logs = FixtureLog().size(); r.calls = g_calls; r.log = r.logs ? FixtureLog()[0] : "";
  return r;
}
const Script kStates[] = {
  {"default", 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {"client", 1, 1, kClient, 0, 0, 0, kGateOn, 1, 1},
  {"no-server-side-view", 1, 0, 0, 0, 0, 0, kGateOn, 0, 1},
  {"hosting", 1, 0, 0, kServer, 2, kPeer, kGateOn, 1, 1},
  {"host-failed", 1, 0, 0, kServer, 1, kPeer, kGateOn, 1, 1},
  {"no-peer", 1, 0, 0, kServer, 0, 0, kGateOn, 1, 1},
};
int main(int argc, char** argv) {
  auto* base = static_cast<uint8_t*>(VirtualAlloc(nullptr, 0x100000000ull, MEM_RESERVE, PAGE_NOACCESS));
  for (uint32_t page : kPages) if (!base || !VirtualAlloc(base + page, 4096, MEM_COMMIT, PAGE_READWRITE)) { puts("FATAL alloc"); return 2; }
  if (argc > 1 && std::string(argv[1]) == "consumers") {
    // The guarded setup of a server without a peer, then each direct consumer of that state.
    FLAGS_fh2_multiscreen_null_peer_guard_storage_() = true;
    g_script = kStates[5]; Fresh(base);
    PPCContext ctx; memset(&ctx, 0, sizeof ctx);
    sub_82E81C20(ctx, base);
    struct { const char* name; void (*fn)(PPCContext&, uint8_t*); bool settings; } calls[] = {
      {"sub_82E79170", sub_82E79170, true}, {"sub_82E79198", sub_82E79198, true}, {"sub_82E791C8", sub_82E791C8, true},
      {"sub_82E797C8", sub_82E797C8, false}, {"sub_82E78CC0", sub_82E78CC0, false}, {"sub_82E78CE0", sub_82E78CE0, false},
      {"sub_82E78D00", sub_82E78D00, false}};
    for (auto& c : calls) {
      printf("call %s\n", c.name); fflush(stdout);
      PPCContext x; memset(&x, 0, sizeof x); x.r3.u64 = c.settings ? kSettings : 0x77777777u;
      c.fn(x, base);
      printf("done %s r3=%08X server+2280=%08X\n", c.name, unsigned(x.r3.u32), unsigned(FixtureLoad32(base, kServer + 2280)));
    }
    printf("consumers finished settings25=%u gate=%08X\n", unsigned(base[kSettings + 25]), unsigned(FixtureLoad32(base, kGate)));
    return 0;
  }
  for (bool on : {false, true}) {
    FLAGS_fh2_multiscreen_null_peer_guard_storage_() = on;
    for (const Script& s : kStates) {
      g_script = s;
      Run plain = Go(base, false), hooked = Go(base, true);
      std::string diff;
      const char* tag[] = {"h+", "g+", "s+"};
      const uint32_t origin[] = {kHolder, kGate, kServer & ~0xFFFu};
      for (int p = 0; p < 3; ++p)
        for (int i = 0; i < 4096; ++i)
          if (plain.pages[p][i] != hooked.pages[p][i]) diff += std::string(" ") + tag[p] + std::to_string(int(kPages[p] + i - origin[p]));
      if (memcmp(&plain.ctx, &hooked.ctx, sizeof(PPCContext)) != 0) diff += " ctx";
      printf("%s %s calls=%d logs=%zu diff=[%s] log=%s\n", on ? "on" : "off", s.name, hooked.calls, hooked.logs, diff.c_str(), hooked.log.c_str());
    }
  }
}
"""
(out / "harness.cpp").write_text(harness)
FLAGS = ["-std=c++20", "-Wall", "-Wextra", "-Werror", "-Wno-unused-variable", "-Wno-unused-but-set-variable",
         "-Wno-unused-label", "-Wno-unused-parameter", "-I", str(out / "stub")]


def build(label, text):
    unit = out / f"{label}.cpp"
    unit.write_text(text)
    exe = out / f"{label}.exe"
    subprocess.run([args.cxx, *FLAGS, str(unit), str(out / "consumers.cpp"), str(out / "harness.cpp"), "-o", str(exe)], check=True)
    return exe


def states(exe):
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"{exe.name} ended early: {result.returncode}\n{result.stdout}"
    return {" ".join(line.split()[:2]): line for line in result.stdout.splitlines()}


checks = 0
def check(passed, why):
    global checks
    checks += 1
    assert passed, why

names = ("default", "client", "no-server-side-view", "hosting", "host-failed", "no-peer")
guard = build("guard", source)
real = states(guard)
for name in names:
    check("calls=1 logs=0 diff=[]" in real[f"off {name}"], f"off, {name} as unhooked: {real[f'off {name}']}")
for name in names[:-1]:
    check("calls=1 logs=0 diff=[]" in real[f"on {name}"], f"on, {name} as unhooked: {real[f'on {name}']}")
f1 = real["on no-peer"]
check("calls=1 logs=1 diff=[ h+8 h+9 h+10 h+11 h+52 h+53 h+109 g+0 g+1 g+2 g+3] log=" in f1,
      f"on, a server without a peer: exactly holder+8 (word), +52, +53, settings+25 (holder+109) and the gate word: {f1}")
check("E [fh2] multiscreen server without a network peer (state 0)" in f1, f"one error with the state: {f1}")

run = subprocess.run([str(guard), "consumers"], capture_output=True, text=True, timeout=60)
check(run.returncode == 0 and "consumers finished settings25=0 gate=00000000" in run.stdout,
      f"after the guard every direct consumer runs without touching page 0:\n{run.stdout}")
for name in ("sub_82E79170", "sub_82E797C8", "sub_82E78CC0", "sub_82E78CE0"):
    check(f"done {name} r3=00000000" in run.stdout, f"{name} answers no role / no server:\n{run.stdout}")
check("done sub_82E79198 r3=" in run.stdout and "done sub_82E791C8 r3=" in run.stdout and "INDIRECT" not in run.stdout,
      f"the role writers return early and the queue send makes no peer call:\n{run.stdout}")

holder_only = source.replace("  base[kSettings + 25] = 0;\n", "").replace("  GuardarU32(base, kGate, 0);\n", "")
assert holder_only != source
crash = subprocess.run([str(build("holder_only", holder_only)), "consumers"], capture_output=True, text=True, timeout=60)
check(crash.returncode != 0 and crash.stdout.rstrip().splitlines()[-1] == "call sub_82E79198",
      f"clearing only the holder (e7c0766) faults in sub_82E79198's write through null holder+8:\n{crash.returncode}\n{crash.stdout}")

no_peer_test = source.replace("if (server == 0 || CargarU32(base, server + 2100) != 0) {", "if (server == 0) {")
masked = states(build("no_peer_test", no_peer_test))
check("diff=[]" not in masked["on hosting"] and "diff=[]" not in masked["on host-failed"],
      "a guard without the peer test changes the states with a peer, and this check sees it")
print(f"{checks} guard checks passed (real fh2_correcoes.cpp and generated consumers on a fake guest with page 0 unmapped; "
      "6 states x off/on, full context; holder-only and no-peer-test mutants caught)")
