#!/usr/bin/env python3
"""Checks the multiscreen null-peer guard (the sub_82E81C20 hook in app/src/fh2_correcoes.cpp) without the game or a
build:
- the source: the original runs once, first, and the hook writes only holder+8, +52 and +53 and never ctx;
- the real fh2_correcoes.cpp, built with stub SDK headers on a fake guest (4 GB reserved, the holder and server pages
  committed), with a fake original that leaves a scripted multiscreen state. Each case runs unhooked and hooked: the
  default and client roles, a server that failed to allocate (with the side view on), a hosting server and one whose
  host failed (both with a peer) must come out byte-identical with nothing logged; the server without a peer must come
  out with holder+8, +52 and +53 cleared, the server's own fields untouched, and one error naming its state;
- a mutant without the peer test, which must change the two cases with a peer (so the check can see a guard that
  masks a failed host);
- with --generated, that game init sub_82493A58 is the setup's only caller and the holder getter returns 0x833F2D34.
A fake cannot show that a live run reaches the hook, or what the peer setup does on the host.

    python -I fh2_multiscreen_guard_check.py --cxx <clang++> --out <scratch folder> [--generated <windows/generated/default>]
"""
import argparse
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cxx", required=True)
parser.add_argument("--out", required=True, type=Path)
parser.add_argument("--generated", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)

# --- Source ---------------------------------------------------------------------------------------------------------
source = (root / "app/src/fh2_correcoes.cpp").read_text().replace("\r\n", "\n")
body = source[source.index("REX_HOOK_RAW(sub_82E81C20) {"):]
body = body[:body.index("\n}\n")]
lines = [l.strip() for l in body.split("\n")[1:]]
assert lines[1] == "__imp__sub_82E81C20(ctx, base);" and body.count("__imp__sub_82E81C20(ctx, base);") == 1, \
    "the original runs once, before anything else"
assert not re.search(r"ctx\.[\w.]+\s*(=[^=]|\+\+|--|[-+|&^]=)", body), "never writes ctx"
writes = re.findall(r"GuardarU32\(base, ([^,]+),|base\[([^\]]+)\]\s*=[^=]", body)
assert sorted(w[0] or w[1] for w in writes) == ["kHolder + 52", "kHolder + 53", "kHolder + 8"], writes
assert "if (server == 0 || CargarU32(base, server + 2100) != 0) {" in body, "only a server without a peer"
assert "fh2_correcoes.cpp" in (root / "windows/CMakeLists.txt").read_text(), "built into the Windows app"

if args.generated:
    gen = args.generated.resolve()
    code = "\n".join(p.read_text(errors="replace") for p in gen.glob("*.cpp"))
    callers = set()
    for m in re.finditer(r"DEFINE_REX_FUNC\((sub_[0-9A-F]+)\) \{(.*?)\n\}", code, re.S):
        if re.search(r"\bsub_82E81C20\(ctx, base\);", m.group(2)):
            callers.add(m.group(1))
    assert callers == {"sub_82493A58"}, callers
    getter = re.search(r"DEFINE_REX_FUNC\(sub_82E79D70\) \{(.*?)\n\}", code, re.S).group(1)
    assert "-2093023232" in getter and "11572" in getter, "sub_82E79D70 returns 0x833F2D34"

# --- Build on a fake guest ------------------------------------------------------------------------------------------
stub = out / "stub/rex"
(stub / "ppc").mkdir(parents=True, exist_ok=True)
(stub / "ppc/func.h").write_text(r"""#pragma once
#include <cstdint>
union PPCRegister { uint64_t u64; int64_t s64; uint32_t u32; int32_t s32; uint8_t u8; };
struct PPCContext { PPCRegister r3, r4, r5; uint64_t lr; };
#define REX_FUNC(x) void x([[maybe_unused]] PPCContext& ctx, uint8_t* base)
#define REX_EXTERN(x) extern "C" REX_FUNC(x)
""")
(stub / "hook.h").write_text('#pragma once\n#include "ppc/func.h"\n#define REX_HOOK_RAW(name) extern "C" REX_FUNC(name)\n')
(stub / "logging.h").write_text(r"""#pragma once
#include <format>
#include <string>
#include <vector>
inline std::vector<std::string>& FixtureLog() { static std::vector<std::string> log; return log; }
#define REXLOG_WARN(...) FixtureLog().push_back("W " + std::format(__VA_ARGS__))
#define REXLOG_ERROR(...) FixtureLog().push_back("E " + std::format(__VA_ARGS__))
""")
others = [m for m in re.findall(r"REX_EXTERN\(__imp__(sub_[0-9A-F]+)\);", source) if m != "sub_82E81C20"]
harness = r"""
#include <windows.h>
#include <cstdio>
#include <cstring>
#include "rex/ppc/func.h"
#include "rex/logging.h"
""" + "\n".join(f'extern "C" REX_FUNC(__imp__{n}) {{ (void)base; }}' for n in others) + r"""
extern "C" REX_FUNC(sub_82E81C20);
constexpr uint32_t kHolder = 0x833F2D34, kServer = 0x40001000, kPeer = 0x40003000, kClient = 0x40005000;
struct Script { const char* name; uint32_t client, server, state, peer; uint8_t active, side; };
Script g_script; int g_calls = 0;
void Store32(uint8_t* base, uint32_t p, uint32_t v) { v = __builtin_bswap32(v); memcpy(base + p, &v, 4); }
extern "C" REX_FUNC(__imp__sub_82E81C20) {
  ++g_calls;
  Store32(base, kHolder + 4, g_script.client);
  Store32(base, kHolder + 8, g_script.server);
  base[kHolder + 52] = g_script.active;
  base[kHolder + 53] = g_script.side;
  if (g_script.server) { Store32(base, g_script.server + 2096, g_script.state); Store32(base, g_script.server + 2100, g_script.peer); }
  ctx.r3.u64 = 0x1234;
}
struct Run { uint8_t holder[4096], server[4096]; PPCContext ctx; size_t logs; int calls; std::string log; };
void Fresh(uint8_t* base) {
  memset(base + (kHolder & ~0xFFFu), 0xA5, 4096); memset(base + kServer, 0x5A, 4096);
  FixtureLog().clear(); g_calls = 0;
}
Run Go(uint8_t* base, bool hooked) {
  Fresh(base);
  PPCContext ctx{}; ctx.r3.u64 = 1; ctx.r4.u64 = 2; ctx.r5.u64 = 3; ctx.lr = 0x82493B00;
  if (hooked) sub_82E81C20(ctx, base); else __imp__sub_82E81C20(ctx, base);
  Run r; memcpy(r.holder, base + (kHolder & ~0xFFFu), 4096); memcpy(r.server, base + kServer, 4096); r.ctx = ctx;
  r.logs = FixtureLog().size(); r.calls = g_calls; r.log = r.logs ? FixtureLog()[0] : "";
  return r;
}
int main() {
  auto* base = static_cast<uint8_t*>(VirtualAlloc(nullptr, 0x100000000ull, MEM_RESERVE, PAGE_NOACCESS));
  if (!base || !VirtualAlloc(base + (kHolder & ~0xFFFu), 4096, MEM_COMMIT, PAGE_READWRITE) ||
      !VirtualAlloc(base + kServer, 4096, MEM_COMMIT, PAGE_READWRITE)) { puts("FATAL alloc"); return 2; }
  const Script cases[] = {
    {"default", 0, 0, 0, 0, 0, 0},
    {"client", kClient, 0, 0, 0, 1, 1},
    {"no-server-side-view", 0, 0, 0, 0, 0, 1},
    {"hosting", 0, kServer, 2, kPeer, 1, 1},
    {"host-failed", 0, kServer, 1, kPeer, 1, 1},
    {"no-peer", 0, kServer, 0, 0, 1, 1},
  };
  for (const Script& s : cases) {
    g_script = s;
    Run plain = Go(base, false), hooked = Go(base, true);
    std::string diff;
    for (int i = 0; i < 4096; ++i) if (plain.holder[i] != hooked.holder[i]) diff += " h+" + std::to_string(int(((kHolder & ~0xFFFu) + i) - kHolder));
    for (int i = 0; i < 4096; ++i) if (plain.server[i] != hooked.server[i]) diff += " s+" + std::to_string(i);
    if (memcmp(&plain.ctx, &hooked.ctx, sizeof(PPCContext)) != 0) diff += " ctx";
    printf("%s calls=%d logs=%zu diff=[%s] cleared=%d log=%s\n", s.name, hooked.calls, hooked.logs, diff.c_str(),
           hooked.holder[(kHolder & 0xFFF) + 8] == 0 && hooked.holder[(kHolder & 0xFFF) + 9] == 0 &&
           hooked.holder[(kHolder & 0xFFF) + 10] == 0 && hooked.holder[(kHolder & 0xFFF) + 11] == 0 &&
           hooked.holder[(kHolder & 0xFFF) + 52] == 0 && hooked.holder[(kHolder & 0xFFF) + 53] == 0, hooked.log.c_str());
  }
}
"""
(out / "harness.cpp").write_text(harness)


def build_and_run(label, text):
    unit = out / f"{label}.cpp"
    unit.write_text(text)
    exe = out / f"{label}.exe"
    subprocess.run([args.cxx, "-std=c++20", "-Wall", "-Wextra", "-Werror", "-I", str(out / "stub"), str(unit),
                    str(out / "harness.cpp"), "-o", str(exe)], check=True)
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return {line.split()[0]: line for line in result.stdout.splitlines()}


checks = 0
def check(passed, why):
    global checks
    checks += 1
    assert passed, why

real = build_and_run("guard", source)
for name in ("default", "client", "no-server-side-view", "hosting", "host-failed"):
    check(f"{name} calls=1 logs=0 diff=[]" in real[name], f"{name} left as it is: {real[name]}")
f1 = real["no-peer"]
changed = set(re.search(r"diff=\[(.*?)\]", f1).group(1).split())
check("calls=1 logs=1" in f1 and "cleared=1" in f1 and {"h+52", "h+53"} <= changed <= {"h+8", "h+9", "h+10", "h+11", "h+52", "h+53"},
      f"server without a peer: only holder+8..+11, +52 and +53 change, and all are cleared: {f1}")
check("E [fh2] multiscreen server without a network peer (state 0)" in f1, f"one error with the state: {f1}")
mutant = source.replace("if (server == 0 || CargarU32(base, server + 2100) != 0) {", "if (server == 0) {")
assert mutant != source
masked = build_and_run("mutant", mutant)
check("diff=[]" not in masked["hosting"] and "diff=[]" not in masked["host-failed"],
      "a guard without the peer test changes the cases with a peer, and this check sees it")
check("diff=[]" in masked["default"] and "diff=[]" in masked["client"], "the mutant still leaves the roles without a server alone")
print(f"{checks} guard checks passed (real fh2_correcoes.cpp on a fake guest; 6 cases unhooked vs hooked; mutant caught)"
      + (" plus the generated caller and holder" if args.generated else ""))
