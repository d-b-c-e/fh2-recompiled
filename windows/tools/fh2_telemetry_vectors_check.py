"""Trace/execute isolated FH2 dynamics vector copies; does not publish new wire fields.

Generated source, expanded image and outputs must remain private. No SDK DLL,
game, graphics, input or physical device startup is linked or invoked.
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
EDGES = {
    "sub_832C51F0": set(),
    "__savegprlr_29": set(), "__restgprlr_29": set(),
    "sub_82EAAAD8": {"__savegprlr_29", "__restgprlr_29"},
    "sub_82EB3F58": set(), "sub_82EB3FB0": set(),
    "sub_82EB5F48": {"sub_82EB3C88"}, "sub_82EB3C88": set(),
    "sub_82EA8340": set(),
}
SLOTS = {316: 0x82EB3F58, 328: 0x82EB5F48, 344: 0x82EA8340, 356: 0x82EB3FB0}

HARNESS = r'''
#include <cstdint>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <cstdlib>
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
@DECLARATIONS@
@FUNCTIONS@
int checks=0;
void Check(bool ok) { ++checks;if(!ok){std::fprintf(stderr,"check %d failed\n",checks);std::exit(10);} }
void Put(uint8_t* b,uint32_t a,float x) { uint32_t v;std::memcpy(&v,&x,4);v=__builtin_bswap32(v);std::memcpy(b+a,&v,4); }
float Get(uint8_t* b,uint32_t a) { uint32_t v;std::memcpy(&v,b+a,4);v=__builtin_bswap32(v);float x;std::memcpy(&x,&v,4);return x; }
void Vec(uint8_t* b,uint32_t a,const float* v){for(int i=0;i<4;++i)Put(b,a+4*i,v[i]);}
void Same(uint8_t* b,uint32_t a,uint32_t c){Check(std::memcmp(b+a,b+c,16)==0);}
PPCContext Context(uint32_t stack) {
 PPCContext c{};c.r1.u32=stack;c.r29.u64=0x123456789ABCDEF0;c.r30.u64=0xFEDCBA9876543210;c.r31.u64=0x8877665544332211;c.lr=0x823F1234;return c;
}
int main(int argc,char** argv) {
 if(argc!=2)return 2;
 std::ifstream file(argv[1],std::ios::binary);std::vector<uint8_t> image((std::istreambuf_iterator<char>(file)),{});
 if(image.size()!=0x1700000)return 3;
 auto* base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
 if(!base||!VirtualAlloc(base+0x40000000,0x100000,MEM_COMMIT,PAGE_READWRITE)||
    !VirtualAlloc(base+0x82000000,image.size(),MEM_COMMIT,PAGE_READWRITE))return 4;
 std::memcpy(base+0x82000000,image.data(),image.size());
 constexpr uint32_t dyn=0x40010000,input=0x40030000,out=0x40040000,stack=0x40080000;
 // The image's mask is BSS. Execute its actual pure leaf initializer, not game startup.
 auto init=Context(stack);sub_832C51F0(init,base);
 for(int i=0;i<4;++i)Check(__builtin_bswap32(*reinterpret_cast<uint32_t*>(base+0x835FDB30+4*i))==(i==3?0xFFFFFFFFu:0));
 const float position[]={123.25f,-45.5f,6.75f,777.f},aux[]={.25f,-.5f,.75f,888.f};
 const float velocities[][4]={{0,0,0,333},{3,4,12,444},{-3,4,-12,555},{.125f,.25f,.5f,666},{100,200,300,777}};
 std::printf("{\"cases\":[");bool first=true;
 for(bool fixed:{false,true})for(const auto& velocity:velocities){
  rex::ppc::g_fixed_fp_mode.store(fixed);std::memset(base+dyn-4096,0xCD,8192);
  Vec(base,input,position);Vec(base,input+16,velocity);Vec(base,input+32,aux);
  const float basis[][4]={{0,1,0,111},{-1,0,0,222},{0,0,1,333}};
  for(int i=0;i<3;++i)Vec(base,input+48+i*16,basis[i]);
  auto c=Context(stack);c.r3.u32=dyn;c.r4.u32=input;sub_82EAAAD8(c,base);
  Check(c.r1.u32==stack&&c.lr==0x823F1234&&c.r29.u64==0x123456789ABCDEF0&&c.r30.u64==0xFEDCBA9876543210&&c.r31.u64==0x8877665544332211);
  for(int i=0;i<3;++i)Check(Get(base,dyn-2592+4*i)==position[i]);
  Check(Get(base,dyn-2592+12)==1);Same(base,dyn-2576,input+16);Same(base,dyn-2560,input+32);
  for(int i=0;i<3;++i){for(int j=0;j<3;++j)Check(Get(base,dyn-2656+i*16+j*4)==basis[i][j]);Check(Get(base,dyn-2656+i*16+12)==0);}
  const double expected=std::sqrt(double(velocity[0])*velocity[0]+double(velocity[1])*velocity[1]+double(velocity[2])*velocity[2]);
  const float speed=Get(base,dyn+3128);Check(std::abs(speed-expected)<=2e-6*std::fmax(1.,expected));
  uint8_t before[8192];std::memcpy(before,base+dyn-4096,sizeof before);
  for(int getter:{316,328,356}){
   std::memset(base+out-16,0xA5,48);c=Context(stack);c.r3.u32=out;c.r4.u32=dyn;c.r5.u32=1;
   if(getter==316)sub_82EB3F58(c,base);else if(getter==328)sub_82EB5F48(c,base);else sub_82EB3FB0(c,base);
   Same(base,out,dyn+(getter==316?-2592:getter==328?-2576:-2560));
   for(int i=0;i<16;++i){Check(base[out-16+i]==0xA5);Check(base[out+16+i]==0xA5);}
   Check(c.r1.u32==stack&&c.lr==0x823F1234);
   Check(std::memcmp(before,base+dyn-4096,sizeof before)==0);
  }
  c=Context(stack);c.r3.u32=dyn;sub_82EA8340(c,base);Check(float(c.f1.f64)==speed);
  Check(std::memcmp(before,base+dyn-4096,sizeof before)==0);
  std::printf("%s{\"fixedFp\":%s,\"velocity\":[%.9g,%.9g,%.9g],\"speed\":%.9g}",first?"":",",fixed?"true":"false",velocity[0],velocity[1],velocity[2],speed);first=false;
 }
 std::printf("],\"checks\":%d}\n",checks);VirtualFree(base,0,MEM_RELEASE);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("generated", "sdk", "image", "cxx", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    raw = args.image.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != IMAGE_SHA:
        raise SystemExit("Wrong title image; refusing address assumptions")
    for table in (0x82003CFC, 0x8224624C):
        for slot, expected in SLOTS.items():
            if struct.unpack_from(">I", raw, table - 0x82000000 + slot)[0] != expected:
                raise ValueError("Dynamics vtable changed")
    found = {}
    trace = {}
    for path in args.generated.glob("*.cpp"):
        source = path.read_text(encoding="utf-8-sig")
        matches = list(re.finditer(r"DEFINE_REX_FUNC\((\w+)\)", source))
        for i, match in enumerate(matches):
            name = match[1]
            if name not in EDGES and name != "sub_82EC63A0":
                continue
            body = source[match.start():matches[i + 1].start() if i + 1 < len(matches) else None]
            if name in trace:
                raise ValueError("Duplicate generated function")
            trace[name] = {"sha256": hashlib.sha256(body.encode()).hexdigest().upper(),
                           "executed": name in EDGES,
                           "instructionCount": len(re.findall(r"\t// ", body))}
            if name not in EDGES:
                continue
            calls = set(re.findall(r"\b((?:sub_[0-9A-F]{8}|__\w+))\(ctx, base\);", body))
            calls |= set(re.findall(r"REX_TAIL_CALL\((\w+)\)", body))
            if calls != EDGES[name] or "REX_CALL_INDIRECT" in body:
                raise ValueError("Vector fixture no longer has the expected closed copy/math call graph")
            found[name] = body
    if set(found) != set(EDGES) or "sub_82EC63A0" not in trace:
        raise ValueError("Missing generated dynamics function")
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
    declarations = "\n".join(f"REX_EXTERN({name});" for name in found)
    (output / "vectors.cpp").write_text(HARNESS.replace("@DECLARATIONS@", declarations).replace("@FUNCTIONS@", "\n".join(found.values())))
    exe = output / "vectors.exe"
    command = [str(args.cxx), "-std=c++23", "-fuse-ld=lld", "-O1", "-msse4.1", "-I", str(args.sdk / "include"),
               "-I", str(args.sdk / "thirdparty/simde"), "-I", str(output), str(output / "vectors.cpp"), "-o", str(exe)]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (output / "compile.log").write_text(compiled.stdout + compiled.stderr)
    compiled.check_returncode()
    run = subprocess.run([str(exe), str(args.image.resolve())], capture_output=True, text=True, timeout=15)
    (output / "run.log").write_text(run.stdout + run.stderr)
    run.check_returncode()
    result = json.loads(run.stdout)
    if len(result["cases"]) != 10:
        raise ValueError("Incomplete vector cases")
    result.update({"observedUtc": datetime.now(timezone.utc).isoformat(), "imageSha256": IMAGE_SHA,
                   "functions": trace, "vtableSlots": {str(k): f"{v:08X}" for k, v in SLOTS.items()},
                   "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
                   "contextSha256": hashlib.sha256((args.sdk / "include/rex/ppc/context.h").read_bytes()).hexdigest().upper(),
                   "intrinsicsSha256": hashlib.sha256((args.sdk / "include/rex/ppc/intrinsics.h").read_bytes()).hexdigest().upper(),
                   "macrosSha256": hashlib.sha256((output / "fh2_macros.h").read_bytes()).hexdigest().upper(),
                   "executableSha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
                   "gameLaunched": False, "sdkDllLoaded": False, "devicesInitialized": False,
                   "newWireFields": False, "wireAxisMappingEstablished": False})
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"PASS: {result['checks']} actual dynamics copy/speed checks; wire vector fields remain unchanged")


if __name__ == "__main__":
    main()
