"""Execute only the pure generated camera projection builder/math on synthetic memory.

No game process, SDK DLL, graphics/input/device initialization or guest image
execution. Generated guest C++/image and fixture outputs remain private.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

IMAGE_SHA = "3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244"


def functions(generated):
    wanted = {"sub_82468C00", "sub_82F46988"}
    found = {}
    constructor = None
    for path in generated.glob("*.cpp"):
        text = path.read_text(encoding="utf-8-sig")
        matches = list(re.finditer(r"DEFINE_REX_FUNC\((sub_[0-9A-F]+)\)", text))
        for index, match in enumerate(matches):
            if match[1] == "sub_82F46838":
                constructor = text[match.start():matches[index + 1].start() if index + 1 < len(matches) else None]
            if match[1] in wanted:
                if match[1] in found:
                    raise ValueError("Duplicate generated function")
                found[match[1]] = text[match.start():matches[index + 1].start() if index + 1 < len(matches) else None]
    if set(found) != wanted:
        raise ValueError("Missing generated projection/math function")
    for name, body in found.items():
        expected = {"sub_82468C00"} if name == "sub_82F46988" else set()
        actual = set(re.findall(r"\b(sub_[0-9A-F]{8})\(ctx, base\);", body))
        if actual != expected or "REX_CALL_INDIRECT" in body or "REX_TAIL_CALL" in body:
            raise ValueError("Projection oracle is no longer a closed math-only call graph")
    if constructor is None or any(x not in constructor for x in
        ["// lfs f12,2780(r11)", "// stfs f12,208(r3)", "// lfs f11,2904(r10)", "// stfs f11,212(r3)"]):
        raise ValueError("Default camera clip-field constructor changed")
    return found, constructor


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
// The runtime's only referenced global: x64 SDK default false; both policies are exercised.
namespace rex::ppc { std::atomic<bool> g_fixed_fp_mode{false}; }
@FUNCTIONS@
void Put(uint8_t* b,uint32_t a,float x) { uint32_t v;std::memcpy(&v,&x,4);v=__builtin_bswap32(v);std::memcpy(b+a,&v,4); }
float Get(uint8_t* b,uint32_t a) { uint32_t v;std::memcpy(&v,b+a,4);v=__builtin_bswap32(v);float x;std::memcpy(&x,&v,4);return x; }
int main(int argc,char** argv) {
 if(argc!=2)return 2;
 std::ifstream file(argv[1],std::ios::binary);std::vector<uint8_t> image((std::istreambuf_iterator<char>(file)),{});
 if(image.size()!=0x1700000)return 3;
 auto* base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
 if(!base||!VirtualAlloc(base+0x40000000,0x100000,MEM_COMMIT,PAGE_READWRITE)||
    !VirtualAlloc(base+0x82000000,image.size(),MEM_COMMIT,PAGE_READWRITE))return 4;
 std::memcpy(base+0x82000000,image.data(),image.size());constexpr uint32_t camera=0x40010000,stack=0x40080000;
 struct Clips {float n,f;};bool first=true;int count=0;std::printf("[");
 for(bool fixed:{false,true})for(int mode:{0,1})for(int flip:{0,1})
 for(float fov:{30.f,60.f,90.f,120.f})for(float aspect:{1.f,16.f/9.f,32.f/9.f})
 for(Clips clip: {Clips{.05f,1000.f},Clips{.5f,20.f},Clips{2.f,2.1f}}) {
  rex::ppc::g_fixed_fp_mode.store(fixed);std::memset(base+camera,0x5A,512);
  Put(base,camera+208,clip.n);Put(base,camera+212,clip.f);Put(base,camera+256,aspect);Put(base,camera+260,fov);base[camera+272]=uint8_t(flip);
  uint8_t pose[64];std::memcpy(pose,base+camera+16,64);
  PPCContext ctx{};ctx.r1.u32=stack;ctx.r3.u32=camera;ctx.r4.u32=mode;ctx.r30.u64=0x123456789ABCDEF0;ctx.r31.u64=0xFEDCBA9876543210;
  sub_82F46988(ctx,base);
  if(ctx.r1.u32!=stack||ctx.r30.u64!=0x123456789ABCDEF0||ctx.r31.u64!=0xFEDCBA9876543210||
     base[camera+480]!=1||base[camera+8]||base[camera+9]||base[camera+10]||base[camera+11]||
     base[camera+12]||base[camera+13]||base[camera+14]||base[camera+15]!=mode||
     std::memcmp(pose,base+camera+16,64))return 5;
  std::printf("%s{\"fixedFp\":%s,\"mode\":%d,\"negateClipXY\":%s,\"fovDegrees\":%.9g,\"aspect\":%.9g,\"nearMetres\":%.9g,\"farMetres\":%.9g,\"matrix\":[",
   first?"":",",fixed?"true":"false",mode,flip?"true":"false",fov,aspect,clip.n,clip.f);first=false;
  for(int i=0;i<16;++i){float v=Get(base,camera+80+i*4);if(!std::isfinite(v))return 6;std::printf("%s%.9g",i?",":"",v);}
  std::printf("]}");++count;
 }
 std::printf("]\n");VirtualFree(base,0,MEM_RELEASE);return count==288?0:7;
}
'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["generated", "sdk", "image", "cxx", "out"]:
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    image = args.image.resolve(strict=True)
    raw_image = image.read_bytes()
    if hashlib.sha256(raw_image).hexdigest().upper() != IMAGE_SHA:
        raise SystemExit("Wrong title image; refusing address assumptions")
    found, constructor = functions(args.generated)
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    macros, keep = [], False
    for line in (args.generated / "fh2_pch.h").read_text().splitlines():
        if line.lstrip().startswith("#") and not line.lstrip().startswith("#include"):
            keep = True
        if keep:
            macros.append(line)
        keep = keep and line.rstrip().endswith("\\")
    (output / "fh2_macros.h").write_text("\n".join(macros) + "\n")
    (output / "oracle.cpp").write_text(HARNESS.replace("@FUNCTIONS@", found["sub_82468C00"] + "\n" + found["sub_82F46988"]))
    exe = output / "oracle.exe"
    command = [str(args.cxx), "-std=c++23", "-fuse-ld=lld", "-O1", "-msse4.1", "-I", str(args.sdk / "include"),
               "-I", str(args.sdk / "thirdparty/simde"), "-I", str(output), str(output / "oracle.cpp"), "-o", str(exe)]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (output / "compile.log").write_text(compiled.stdout + compiled.stderr)
    compiled.check_returncode()
    result = subprocess.run([str(exe), str(image)], capture_output=True, text=True, timeout=15)
    (output / "run.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    cases = json.loads(result.stdout)
    assert len(cases) == 288
    report = {"imageSha256": IMAGE_SHA, "observedUtc": datetime.now(timezone.utc).isoformat(),
              "gameLaunched": False, "sdkDllLoaded": False, "graphicsInitialized": False,
              "physicalDevicesInitialized": False, "sceneCutEstablished": False,
              "runtimeUnitsEstablished": False, "syntheticInputUnits": "metres assigned by fixture; builder is unit-agnostic",
              "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
              "sdkContextSha256": hashlib.sha256((args.sdk / "include/rex/ppc/context.h").read_bytes()).hexdigest().upper(),
              "sdkIntrinsicsSha256": hashlib.sha256((args.sdk / "include/rex/ppc/intrinsics.h").read_bytes()).hexdigest().upper(),
              "generatedMacrosSha256": hashlib.sha256((output / "fh2_macros.h").read_bytes()).hexdigest().upper(),
              "constructor": {"address": "82F46838", "executed": False,
                  "sha256": hashlib.sha256(constructor.encode()).hexdigest().upper(),
                  "field208Default": struct.unpack_from(">f", raw_image, 0xADC)[0],
                  "field212Default": struct.unpack_from(">f", raw_image, 0xB58)[0]},
              "functionSha256": {k: hashlib.sha256(v.encode()).hexdigest().upper() for k, v in found.items()},
              "executableSha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(), "cases": cases}
    (output / "oracle.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: 288 actual generated projection matrices; state/frame preserved; no game/GPU/device")
