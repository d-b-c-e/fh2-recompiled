"""Invoked by fh2_multiscreen_guard_check.py --lifetime-only; reuses its extraction and SDK stub.

Generated control flow, with fake allocation/events/provider completion and empty leaf containers.
This checks sequencing, not real synchronization, thread completion, or cleanup-hook admission.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

names = """831FBD58 8321D8E8 8321BE00 8321BEC8 831F9268 831F88C8 83201C00 8321BFB0
831FA3A0 832138F8 831FA300 831F9210 83201D50 8321C170 83218998 8321BF98 8321BE88
82E7F528 82E7F028 82E7EBA8 82E77BF0 82E81800 82E78DD8 82E78DE0
82E849A8 82E84820 82E83488 82E833A0 82E82750 82E7AF58 82E7A1C8
82E7F698 82E79F18 82E7FB38 82E7FA90 82E7EF48""".split()
bodies = {"sub_" + n: generated["sub_" + n] for n in names}
(out / "lifetime_manifest.json").write_text(json.dumps({
    n: hashlib.sha256(t.encode()).hexdigest() for n, t in bodies.items()}, indent=2))

# Extend only this mode's generated stub; the original guard/Initialise modes are unchanged.
header = (stub / "ppc/func.h").read_text()
header = header.replace("uint8_t u8;", "uint8_t u8; int8_t s8; uint16_t u16; float f32; double f64;")
header = header.replace("double f[32];", "double f[32]; PPCRegister " + ", ".join(f"f{i}" for i in range(32)) +
                        "; PPCRegister reserved; uint32_t msr; struct { void disableFlushMode() {} } fpscr;")
(stub / "ppc/func.h").write_text(header)
harness = Path(__file__).with_name("fh2_lifetime_fixture.cpp").read_text()
calls = set(re.findall(r"\b((?:sub_|__imp__|__savegprlr_|__restgprlr_)\w+)\(ctx, base\)", "\n".join(bodies.values())))
calls.update(re.findall(r"REX_TAIL_CALL\((\w+)\)", "\n".join(bodies.values())))
decls = '#include "rex/ppc/func.h"\n' + "\n".join(f"REX_EXTERN({n});" for n in sorted(calls | bodies.keys()))
implemented = set(re.findall(r"REX_EXTERN\((\w+)\)\s*\{", harness))
helpers = []
for n in sorted(calls - bodies.keys() - implemented):
    if n.startswith(("__savegprlr_", "__restgprlr_")):
        first = int(n.rsplit("_", 1)[1])
        save = n.startswith("__save")
        lines = [f"REX_EXTERN({n}) {{"]
        for i in range(first, 32):
            address = f"ctx.r1.u32 - {8 * (32 - i) + 8}"
            lines.append(f"  REX_STACK_STORE_U64({address}, ctx.r{i}.u64);" if save else
                         f"  ctx.r{i}.u64 = REX_STACK_LOAD_U64({address});")
        lines.append("  REX_STACK_STORE_U32(ctx.r1.u32 - 8, ctx.r12.u32);" if save else
                     "  ctx.lr = REX_STACK_LOAD_U32(ctx.r1.u32 - 8);")
        helpers.append("\n".join(lines) + "\n}")
    else:
        helpers.append(f'REX_EXTERN({n}) {{ Fail("unmodeled helper: {n}"); }}')

variants = {"lifetime": bodies}
early = dict(bodies)
anchor = "loc_8321C24C:\n"
assert early["sub_8321C170"].count(anchor) == 1
early["sub_8321C170"] = early["sub_8321C170"].replace(anchor, anchor + "\tgoto loc_8321C338;\n")
variants["lifetime_skip_drain"] = early
retained = dict(bodies)
anchor = "if (!cr6.eq) goto loc_831FA3F8;"
assert retained["sub_831FA3A0"].count(anchor) == 1
retained["sub_831FA3A0"] = retained["sub_831FA3A0"].replace(anchor, "/* mutant: destroy retained peer */")
variants["lifetime_retained_free"] = retained
listener = dict(bodies)
anchor = "\tsub_82E7A1C8(ctx, base);"
assert listener["sub_82E833A0"].count(anchor) == 2
# Remove just the final server-array erase; leave the per-connection erase intact.
head, tail = listener["sub_82E833A0"].rsplit(anchor, 1)
listener["sub_82E833A0"] = head + "\t/* mutant: keep server listener */" + tail
variants["lifetime_keep_listener"] = listener

cases = {"lifetime": ["retained", "release", "drain", "stall-busy", "stall-list40", "stall-list48",
                       "incomplete", "server", "server-connection", "server-queue"],
         "lifetime_skip_drain": ["drain"], "lifetime_retained_free": ["retained"],
         "lifetime_keep_listener": ["server"]}
expected_failure = {"lifetime_skip_drain": "provider close before drain",
                    "lifetime_retained_free": "destroy retained peer",
                    "lifetime_keep_listener": "listener still registered"}
for label, selected in variants.items():
    unit, exe = out / f"{label}.cpp", out / f"{label}.exe"
    unit.write_text(decls + "\n" + harness + "\n" + "\n".join(helpers) + "\n" + "\n".join(selected.values()))
    subprocess.run([args.cxx, *FLAGS, str(unit), "-o", str(exe)], check=True, timeout=60)
    for case in cases[label]:
        run = subprocess.run([str(exe), case], capture_output=True, text=True, timeout=10)
        (out / f"{label}-{case}.txt").write_text(run.stdout + run.stderr)
        expected = 0 if label == "lifetime" else 1
        assert run.returncode == expected, f"{label}/{case}: exit {run.returncode}\n{run.stdout}\n{run.stderr}"
        assert ("PASS " + case) in run.stdout if expected == 0 else expected_failure[label] in run.stdout, run.stdout
        print(f"{label}/{case}: {run.stdout.strip()}")
print("10 lifecycle cases passed; 3 mutants rejected. Scripted completion only; real concurrency remains unqualified.")
