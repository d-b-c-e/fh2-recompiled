"""Execute the existing guest asymmetric extent setter and projection builder only.

Generated bodies/image/output remain private. No SDK runtime, native hook,
game, graphics/input/device initialization or installation is performed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess

IMAGE_SHA = "3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244"
WANTED = {"sub_823F2FF0", "sub_82F43678", "sub_82F43618", "sub_823FF818"}
TRACE_NAMES = {"sub_8262CC40", "sub_8262D298", "sub_8262D0F0", "sub_82F45078", "sub_82F45060",
               "sub_82F44CC0", "sub_82F44CA8"}
HARNESS = r'''
#include <cstdint>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>
#include <rex/ppc/context.h>
#include <rex/ppc/intrinsics.h>
#include "fh2_macros.h"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
namespace rex::ppc { std::atomic<bool> g_fixed_fp_mode{false}; }
@FUNCTIONS@
void Put(uint8_t* b,uint32_t a,float x){uint32_t v;std::memcpy(&v,&x,4);v=__builtin_bswap32(v);std::memcpy(b+a,&v,4);}
float Get(uint8_t* b,uint32_t a){uint32_t v;std::memcpy(&v,b+a,4);v=__builtin_bswap32(v);float x;std::memcpy(&x,&v,4);return x;}
int main(int argc,char** argv){
 if(argc!=2)return 2;
 std::ifstream file(argv[1],std::ios::binary);std::vector<uint8_t> image((std::istreambuf_iterator<char>(file)),{});
 if(image.size()!=0x1700000)return 3;
 auto* base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
 if(!base||!VirtualAlloc(base+0x40000000,0x100000,MEM_COMMIT,PAGE_READWRITE)||!VirtualAlloc(base+0x82000000,image.size(),MEM_COMMIT,PAGE_READWRITE))return 4;
 std::memcpy(base+0x82000000,image.data(),image.size());constexpr uint32_t camera=0x40010000,stack=0x40080000;
 struct Rect{float l,t,r,b;};struct Clips{float n,f;};bool first=true;int cases=0;
 for(uint32_t flag:{0u,1u,2u,255u,256u,257u,0xFFFFFFFFu,0x80000000u}){
  std::memset(base+camera,0xA7,512);base[camera+480]=0;uint8_t expected[512];std::memcpy(expected,base+camera,512);expected[272]=uint8_t(flag);
  PPCContext ctx{};ctx.r1.u32=stack;ctx.r3.u32=camera;ctx.r4.u32=flag;sub_82F43618(ctx,base);
  if(std::memcmp(expected,base+camera,512)||ctx.r1.u32!=stack)return 8;
  sub_823FF818(ctx,base);if(ctx.r3.u32!=uint8_t(flag)||std::memcmp(expected,base+camera,512))return 9;
 }
 std::printf("[");
 for(bool fixed:{false,true})for(int mode:{0,1})for(int flip:{0,1})
 for(Clips c:{Clips{.05f,1000.f},Clips{.5f,20.f},Clips{2.f,2.1f}})
 for(Rect r:{Rect{-.1f,.1f,.1f,-.1f},Rect{-.15f,.2f,.3f,-.1f},Rect{.1f,.4f,.35f,.05f},Rect{-.3f,-.05f,.1f,-.2f},Rect{-1,2,3,-4}}){
  rex::ppc::g_fixed_fp_mode.store(fixed);std::memset(base+camera,0x5A,512);uint8_t pose[64];std::memcpy(pose,base+camera+16,64);
  PPCContext ctx{};ctx.r1.u32=stack;ctx.r3.u32=camera;ctx.f1.f64=r.l;ctx.f2.f64=r.t;ctx.f3.f64=r.r;ctx.f4.f64=r.b;
  sub_823F2FF0(ctx,base);
  if(Get(base,camera+240)!=r.l||Get(base,camera+244)!=r.t||Get(base,camera+248)!=r.r||Get(base,camera+252)!=r.b||base[camera+480]!=1)return 5;
  Put(base,camera+208,c.n);Put(base,camera+212,c.f);ctx.r4.u32=flip;sub_82F43618(ctx,base);ctx.r4.u32=mode;
  sub_82F43678(ctx,base);
  if(ctx.r1.u32!=stack||std::memcmp(pose,base+camera+16,64)||base[camera+480]!=1||base[camera+8]||base[camera+9]||base[camera+10]||base[camera+11]!=1||
     base[camera+12]||base[camera+13]||base[camera+14]||base[camera+15]!=mode)return 6;
  std::printf("%s{\"fixedFp\":%s,\"mode\":%d,\"flag272\":%d,\"near\":%.9g,\"far\":%.9g,\"extents\":[%.9g,%.9g,%.9g,%.9g],\"matrix\":[",first?"":",",fixed?"true":"false",mode,flip,c.n,c.f,r.l,r.t,r.r,r.b);first=false;
  for(int i=0;i<16;++i){float v=Get(base,camera+80+4*i);std::printf("%s",i?",":"");if(std::isfinite(v))std::printf("%.9g",v);else std::printf("null");}
  std::printf("],\"matrixBits\":[");for(int i=0;i<16;++i){float v=Get(base,camera+80+4*i);uint32_t bits;std::memcpy(&bits,&v,4);std::printf("%s\"%08X\"",i?",":"",bits);}std::printf("]}");++cases;
 }
 std::printf("]\n");VirtualFree(base,0,MEM_RELEASE);return cases==120?0:7;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("generated", "sdk", "image", "cxx", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    raw = args.image.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != IMAGE_SHA:
        raise ValueError("Wrong title image")
    slots = {44: 0x82F46988, 48: 0x82F43678, 76: 0x823F2FF0, 80: 0x82F43618, 84: 0x823FF818}
    for slot, target in slots.items():
        if struct.unpack_from(">I", raw, 0x8224FBDC - 0x82000000 + slot)[0] != target:
            raise ValueError("Base camera vtable changed")
    found, trace = {}, {}
    for path in args.generated.glob("*.cpp"):
        text = path.read_text(encoding="utf-8-sig")
        matches = list(re.finditer(r"DEFINE_REX_FUNC\((\w+)\)", text))
        for i, match in enumerate(matches):
            if match[1] not in WANTED | TRACE_NAMES:
                continue
            body = text[match.start():matches[i + 1].start() if i + 1 < len(matches) else None]
            if match[1] in TRACE_NAMES:
                if match[1] in trace:
                    raise ValueError("Duplicate static trace function")
                trace[match[1]] = body
                continue
            if match[1] in found or re.search(r"\b(?:sub_[0-9A-F]{8}|__\w+)\(ctx, base\);|REX_CALL_INDIRECT|REX_TAIL_CALL", body):
                raise ValueError("Expected unique leaf math/setter/getter functions")
            found[match[1]] = body
    if set(found) != WANTED or set(trace) != TRACE_NAMES:
        raise ValueError("Missing native extent setter/builder")
    comments = {name: re.findall(r"\t// (.+)", body) for name, body in trace.items()}
    sequence = ["lwz r3,40(r31)", "mr r4,r29", "lwz r11,0(r3)", "lwz r11,80(r11)", "mtctr r11", "bctrl ",
                "lwz r3,40(r31)", "li r4,0", "lwz r11,0(r3)", "lwz r11,44(r11)", "mtctr r11", "bctrl "]
    if comments["sub_8262CC40"][60:72] != sequence or comments["sub_8262CC40"][7] != "mr r29,r4":
        raise ValueError("Camera feed no longer propagates flag then selects symmetric mode0")
    for name, index in (("sub_8262D0F0", 15), ("sub_8262D298", 11)):
        if comments[name][index:index+3] != ["li r4,1", "mr r3,r31", "bl 0x8262cc40"]:
            raise ValueError("Known camera feed caller no longer supplies flag1")
    if comments["sub_82F45078"][13] != "stb r30,4(r3)" or comments["sub_82F45060"] != ["lwz r11,0(r3)", "lbz r4,4(r4)", "lwz r11,80(r11)", "mtctr r11", "bctr "]:
        raise ValueError("Deferred flag byte contract changed")
    if comments["sub_82F44CC0"][13] != "stw r30,4(r3)" or comments["sub_82F44CA8"] != ["lwz r11,0(r3)", "lwz r4,4(r4)", "lwz r11,44(r11)", "mtctr r11", "bctr "]:
        raise ValueError("Deferred symmetric mode word contract changed")
    words = {0x8262CD3C: 0x816B0050, 0x8262CD4C: 0x38800000, 0x8262CD54: 0x816B002C,
             0x8262D12C: 0x38800001, 0x8262D2C4: 0x38800001,
             0x82F43618: 0x98830110, 0x823FF818: 0x88630110}
    for address, expected in words.items():
        if struct.unpack_from(">I", raw, address-0x82000000)[0] != expected:
            raise ValueError(f"Static image instruction changed at {address:08X}")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    macros, keep = [], False
    for line in (args.generated / "fh2_pch.h").read_text().splitlines():
        if line.lstrip().startswith("#") and not line.lstrip().startswith("#include"):
            keep = True
        if keep:
            macros.append(line)
        keep = keep and line.rstrip().endswith("\\")
    (out / "fh2_macros.h").write_text("\n".join(macros) + "\n")
    (out / "offaxis.cpp").write_text(HARNESS.replace("@FUNCTIONS@", "\n".join(found.values())))
    exe = out / "offaxis.exe"
    command = [str(args.cxx), "-std=c++23", "-fuse-ld=lld", "-O1", "-msse4.1", "-I", str(args.sdk / "include"), "-I", str(args.sdk / "thirdparty/simde"), "-I", str(out), str(out / "offaxis.cpp"), "-o", str(exe)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (out / "compile.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    result = subprocess.run([str(exe), str(args.image.resolve())], capture_output=True, text=True, timeout=15)
    (out / "run.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    cases = json.loads(result.stdout)
    checks, unflipped_checks = 0, 0
    for c in cases:
        n, f = c["near"], c["far"]
        l, t, r, b = c["extents"]
        q = 1 if c["mode"] == 0 else -1
        if c["flag272"]:
            l, r, b = -l, -r, -b
            if c["mode"] == 0:
                t = -t  # mode1/nonzero flag leaves top unchanged in actual guest code
        expected = [2*n/(r-l), 0, 0, 0, 0, 2*n/(t-b) if t != b else None, 0, 0,
                    -q*(r+l)/(r-l), -q*(t+b)/(t-b) if t != b else None, q*f/(f-n), q, 0, 0, -n*f/(f-n), 0]
        for actual, want in zip(c["matrix"], expected):
            if (want is None and actual is not None) or (want is not None and (actual is None or not math.isclose(actual, want, rel_tol=3e-6, abs_tol=3e-6))):
                raise ValueError(f"Native off-axis convention mismatch: {c}")
            checks += 1
            unflipped_checks += not c["flag272"]
        if t == b:
            continue  # explicitly classified nonfinite matrices are never used for corners
        matrix = c["matrix"]
        for z, depth in ((n, 0), (f, 1)):
            for x, sign_x in ((l, -1), (r, 1)):
                for y, sign_y in ((b, -1), (t, 1)):
                    point = (x*z/n, y*z/n, q*z, 1)
                    clip = [sum(point[i]*matrix[i*4+j] for i in range(4)) for j in range(4)]
                    for actual, want in zip((v/clip[3] for v in clip[:3]), (sign_x, sign_y, depth)):
                        if not math.isclose(actual, want, rel_tol=3e-6, abs_tol=3e-6):
                            raise ValueError("Native asymmetric frustum corner/depth failed")
                        checks += 1
                        unflipped_checks += not c["flag272"]
    report = {"imageSha256": IMAGE_SHA, "observedUtc": datetime.now(timezone.utc).isoformat(), "cases": cases,
              "conventionalMatrixChecks": unflipped_checks, "allFlagAlgebraChecks": checks,
              "flagSetterGetterStateCases": 8, "nonfiniteSurveyCases": sum(None in c["matrix"] for c in cases),
              "baseVtable": "8224FBDC", "vtableSlots": {str(k): f"{v:08X}" for k, v in slots.items()},
              "staticFunctionSha256": {k: hashlib.sha256(v.encode()).hexdigest().upper() for k, v in trace.items()},
              "staticInstructionWords": {f"{k:08X}": f"{v:08X}" for k, v in words.items()},
              "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
              "functionSha256": {k: hashlib.sha256(v.encode()).hexdigest().upper() for k, v in found.items()},
              "contextSha256": hashlib.sha256((args.sdk / "include/rex/ppc/context.h").read_bytes()).hexdigest().upper(),
              "intrinsicsSha256": hashlib.sha256((args.sdk / "include/rex/ppc/intrinsics.h").read_bytes()).hexdigest().upper(),
              "macrosSha256": hashlib.sha256((out / "fh2_macros.h").read_bytes()).hexdigest().upper(),
              "executableSha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
              "gameLaunched": False, "sdkDllLoaded": False, "devicesInitialized": False,
              "nativeHookAdded": False, "sceneCutEstablished": False, "runtimeUnitsEstablished": False}
    (out / "oracle.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {checks} all-flag algebra/corner/depth checks ({unflipped_checks} unflipped), 8 flag state cases; {len(cases)} survey cases, {report['nonfiniteSurveyCases']} nonfinite (not admitted)")


if __name__ == "__main__":
    main()
