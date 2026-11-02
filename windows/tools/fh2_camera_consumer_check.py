"""Check camera overwrite survival and the actual lazy frustum consumer offline.

Generated guest source/image and outputs stay private. No SDK runtime DLL,
queue, scene traversal, game, graphics/input/device initialization or install.
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
ROOTS = {"sub_82408998", "sub_82F46988", "sub_82F43678", "sub_823F2FF0", "sub_82F43618", "sub_823F5920", "sub_824153F8", "sub_823F2568", "sub_823F1D80"}
ALLOWED = ROOTS | {"sub_82C023A0", "sub_82E43690", "sub_82E431E0", "sub_823FB1B0", "sub_82402C80", "sub_82422D80",
                   "sub_82C009E0", "sub_82468C00", "sub_82487C30", "sub_8240EA50", "sub_82401038",
                   "__savegprlr_23", "__savegprlr_22", "__restgprlr_22", "__restgprlr_23",
                   "__savefpr_27", "__savefpr_28", "__restfpr_27", "__restfpr_28"}
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
uint8_t* memory=nullptr;int checks=0;
constexpr uint32_t camera=0x40010000,stack=0x40080000,point=0x40040000;
void Check(bool ok,const char* label){++checks;if(!ok){std::fprintf(stderr,"check%d: %s\n",checks,label);std::exit(10);}}
void Put(uint32_t a,float x){uint32_t v;std::memcpy(&v,&x,4);v=__builtin_bswap32(v);std::memcpy(memory+a,&v,4);}
uint32_t Word(uint32_t a){uint32_t v;std::memcpy(&v,memory+a,4);return __builtin_bswap32(v);}
PPCContext Context(){PPCContext c{};c.r1.u32=stack;c.r3.u32=camera;c.r31.u64=0x123456789ABCDEF0;c.lr=0x823F1234;return c;}
void Init(float near_,float far_,float fov,float aspect,int flag){
 std::memset(memory+camera,0x5A,512);
 for(int i=0;i<16;++i)Put(camera+16+4*i,(i%5)==0?1.f:0.f);
 Put(camera+208,near_);Put(camera+212,far_);Put(camera+256,aspect);Put(camera+260,fov);
 auto c=Context();c.r4.u32=flag;sub_82F43618(c,memory);
}
void Sym(){auto c=Context();c.r4.u32=0;sub_82F46988(c,memory);Check(Word(camera+8)==0&&memory[camera+480]==1,"symmetric commit kind/dirty");}
void Asym(float near_){auto c=Context();c.f1.f64=.4f*near_;c.f2.f64=.6f*near_;c.f3.f64=1.6f*near_;c.f4.f64=-.6f*near_;sub_823F2FF0(c,memory);c.r3.u32=camera;c.r4.u32=0;sub_82F43678(c,memory);Check(Word(camera+8)==1&&memory[camera+480]==1,"asymmetric commit kind/dirty");}
void Consume(){
 uint8_t before[512];std::memcpy(before,memory+camera,512);auto c=Context();sub_823F5920(c,memory);
 Check(c.r3.u32==camera+288&&c.r1.u32==stack&&c.lr==0x823F1234&&c.r31.u64==0x123456789ABCDEF0,"actual plane getter ABI");
 Check(memory[camera+480]==0,"cache clears dirty");
 bool same=true;for(int i=0;i<512;++i)if((i<288||i>480)&&memory[camera+i]!=before[i])same=false;
 Check(same,"consumer only changes plane/aux cache and dirty");
}
bool Inside(float x,float y,float z){
 Put(point,x);Put(point+4,y);Put(point+8,z);Put(point+12,1);
 auto c=Context();c.r3.u32=camera+288;c.f1.f64=0;
 simde_mm_store_si128((simde__m128i*)c.v1.u8,simde_mm_shuffle_epi8(simde_mm_load_si128((simde__m128i*)(memory+point)),simde_mm_load_si128((simde__m128i*)VectorMaskL)));
 sub_824153F8(c,memory);return c.r3.u32!=0;
}
int main(int argc,char** argv){
 if(argc!=2)return 2;
 std::ifstream file(argv[1],std::ios::binary);std::vector<uint8_t> image((std::istreambuf_iterator<char>(file)),{});if(image.size()!=0x1700000)return 3;
 memory=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
 if(!memory||!VirtualAlloc(memory+0x40000000,0x100000,MEM_COMMIT,PAGE_READWRITE)||!VirtualAlloc(memory+0x82000000,image.size(),MEM_COMMIT,PAGE_READWRITE))return 4;
 std::memcpy(memory+0x82000000,image.data(),image.size());
 struct Config{float n,f,fov,aspect;};bool first=true;int mismatches=0,baselineMissing=0;std::printf("{\"cases\":[");
 for(bool fixed:{false,true})for(int flag:{0,1})for(Config p:{Config{.5f,20,60,1.5f},Config{1,50,90,1},Config{.05f,1000,100,2}}){
  rex::ppc::g_fixed_fp_mode.store(fixed);
  const float z=(p.n+p.f)*.25f;
  Init(p.n,p.f,p.fov,p.aspect,flag);Sym();uint8_t symMatrix[64],symPlanes[192];std::memcpy(symMatrix,memory+camera+80,64);Consume();std::memcpy(symPlanes,memory+camera+288,192);
  const bool symForward=Inside(0,0,z),symBackward=Inside(0,0,-z);baselineMissing+=!symForward&&!symBackward;
  Init(p.n,p.f,p.fov,p.aspect,flag);Asym(p.n);Sym();Consume();
  Check(std::memcmp(symMatrix,memory+camera+80,64)==0&&std::memcmp(symPlanes,memory+camera+288,192)==0,"early asymmetric update lost to later symmetric commit");
  Init(p.n,p.f,p.fov,p.aspect,flag);Sym();Asym(p.n);uint8_t asymMatrix[64],asymPlanes[192];std::memcpy(asymMatrix,memory+camera+80,64);Consume();std::memcpy(asymPlanes,memory+camera+288,192);
  Check(Word(camera+8)==1&&std::memcmp(asymMatrix,memory+camera+80,64)==0,"late asymmetric matrix survives consumer");
  Check(std::memcmp(symMatrix,asymMatrix,64)!=0&&std::memcmp(symPlanes,asymPlanes,192)!=0,"late matrix and derived planes both differ from symmetric");
  const float x=flag?-z:z;double clip[4]{};const double v[]={x,0,z,1};
  for(int i=0;i<4;++i)for(int j=0;j<4;++j){uint32_t w=Word(camera+80+i*16+j*4);float f;std::memcpy(&f,&w,4);clip[j]+=v[i]*f;}
  const bool projectedInside=clip[3]>0&&std::abs(clip[0])<clip[3]&&std::abs(clip[1])<clip[3]&&clip[2]>0&&clip[2]<clip[3];
  Check(projectedInside,"test point is strictly inside actual asymmetric projection");
  const bool planesInside=Inside(x,0,z);mismatches+=projectedInside!=planesInside;
  float planeValues[24];for(int i=0;i<24;++i){uint32_t w=Word(camera+288+4*i);std::memcpy(&planeValues[i],&w,4);}
  uint8_t cached[512];std::memcpy(cached,memory+camera,512);Consume();Check(std::memcmp(cached,memory+camera,512)==0,"clean consumer reuses current planes without writes");
  // A raw matrix-only patch deliberately leaves symmetric kind/clean cache.
  Init(p.n,p.f,p.fov,p.aspect,flag);Sym();Consume();std::memcpy(memory+camera+80,asymMatrix,64);Consume();
  Check(Word(camera+8)==0&&std::memcmp(symPlanes,memory+camera+288,192)==0&&std::memcmp(asymMatrix,memory+camera+80,64)==0,"matrix-only patch leaves stale symmetric planes");
  std::printf("%s{\"fixedFp\":%s,\"flag272\":%d,\"near\":%.9g,\"far\":%.9g,\"fov\":%.9g,\"aspect\":%.9g,\"symmetricPositiveZInside\":%s,\"symmetricNegativeZInside\":%s,\"point\":[%.9g,0,%.9g],\"projectedInside\":%s,\"planesInside\":%s,\"planes\":[",first?"":",",fixed?"true":"false",flag,p.n,p.f,p.fov,p.aspect,symForward?"true":"false",symBackward?"true":"false",x,z,projectedInside?"true":"false",planesInside?"true":"false");
  for(int i=0;i<24;++i){if(!std::isfinite(planeValues[i]))return 11;std::printf("%s%.9g",i?",":"",planeValues[i]);}std::printf("]}");first=false;
 }
 // The only source-backed extent producer found selects kind2, not kind1.
 std::printf("],\"orthographicControls\":[");first=true;
 for(bool fixed:{false,true}){
  rex::ppc::g_fixed_fp_mode.store(fixed);Init(.1f,7.5f,90,1,0);
  auto c=Context();c.f1.f64=-4;c.f2.f64=4;c.f3.f64=4;c.f4.f64=-4;sub_823F2FF0(c,memory);
  c.r3.u32=camera;c.r4.u32=0;sub_823F2568(c,memory);
  Check(Word(camera+8)==2&&memory[camera+480]==1,"source-backed orthographic kind/dirty");
  Consume();const bool center=Inside(0,0,3.8f),left=Inside(-5,0,3.8f),right=Inside(5,0,3.8f),behind=Inside(0,0,-1),beyond=Inside(0,0,8);
  // Report observed containment; retain the kind1 HOLD independently.
  std::printf("%s{\"fixedFp\":%s,\"centerInside\":%s,\"leftOutsideRejected\":%s,\"rightOutsideRejected\":%s,\"behindRejected\":%s,\"beyondRejected\":%s}",first?"":",",fixed?"true":"false",center?"true":"false",!left?"true":"false",!right?"true":"false",!behind?"true":"false",!beyond?"true":"false");first=false;
 }
 std::printf("],\"checks\":%d,\"projectionPlaneDisagreements\":%d,\"baselineMissingInterior\":%d}\n",checks,mismatches,baselineMissing);VirtualFree(memory,0,MEM_RELEASE);return 0;
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
    found = {}
    for path in args.generated.glob("*.cpp"):
        source = path.read_text(encoding="utf-8-sig")
        matches = list(re.finditer(r"DEFINE_REX_FUNC\((\w+)\)", source))
        for i, match in enumerate(matches):
            if match[1] not in ALLOWED:
                continue
            body = source[match.start():matches[i+1].start() if i+1 < len(matches) else None]
            calls = set(re.findall(r"\b(\w+)\(ctx, base\);", body)) | set(re.findall(r"REX_TAIL_CALL\((\w+)\)", body))
            if match[1] in found or calls - ALLOWED or "REX_CALL_INDIRECT" in body:
                raise ValueError("Camera consumer closure changed; trace before executing")
            found[match[1]] = body
    if set(found) != ALLOWED:
        raise ValueError("Missing closed camera consumer function")
    comments = re.findall(r"\t// (.+)", found["sub_82F46988"])
    if comments[130:138] != ["stvx128 v61,r11,r8", "stvx128 v62,r11,r7", "stvx128 v63,r0,r11", "li r11,0", "stw r30,12(r31)", "stw r11,8(r31)", "stb r10,480(r31)", "addi r1,r1,256"]:
        raise ValueError("Symmetric commit/epilogue boundary changed")
    words = {0x82F46BA8: 0x995F01E0, 0x82F46BAC: 0x38210100, 0x824089A8: 0x896301E0}
    for address, word in words.items():
        if struct.unpack_from(">I", raw, address-0x82000000)[0] != word:
            raise ValueError(f"Commit/consumer image word changed at{address:08X}")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    macros, keep = [], False
    for line in (args.generated / "fh2_pch.h").read_text().splitlines():
        if line.lstrip().startswith("#") and not line.lstrip().startswith("#include"):
            keep = True
        if keep:
            macros.append(line)
        keep = keep and line.rstrip().endswith("\\")
    (out / "fh2_macros.h").write_text("\n".join(macros)+"\n")
    declarations = "\n".join(f"REX_EXTERN({name});" for name in found)
    (out / "consumer.cpp").write_text(HARNESS.replace("@DECLARATIONS@", declarations).replace("@FUNCTIONS@", "\n".join(found.values())))
    exe = out / "consumer.exe"
    command = [str(args.cxx), "-std=c++23", "-O1", "-fuse-ld=lld", "-msse4.1", "-I", str(args.sdk / "include"), "-I", str(args.sdk / "thirdparty/simde"), "-I", str(out), str(out / "consumer.cpp"), "-o", str(exe)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    (out / "compile.log").write_text(result.stdout+result.stderr)
    result.check_returncode()
    result = subprocess.run([str(exe), str(args.image.resolve())], capture_output=True, text=True, timeout=30)
    (out / "run.log").write_text(result.stdout+result.stderr)
    result.check_returncode()
    record = json.loads(result.stdout)
    if len(record["cases"]) != 12 or len(record["orthographicControls"]) != 2:
        raise ValueError("Incomplete survival cases")
    hold = bool(record["projectionPlaneDisagreements"] or record["baselineMissingInterior"])
    record.update({"status": "hold-culling-contract" if hold else "pass", "orderingChecksPassed": True,
                   "fixtureContainmentConsistent": not hold, "cullingAdmitted": False,
                   "observedUtc": datetime.now(timezone.utc).isoformat(), "imageSha256": IMAGE_SHA,
                   "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
                   "functionSha256": {k: hashlib.sha256(v.encode()).hexdigest().upper() for k,v in found.items()},
                   "contextSha256": hashlib.sha256((args.sdk / "include/rex/ppc/context.h").read_bytes()).hexdigest().upper(),
                   "intrinsicsSha256": hashlib.sha256((args.sdk / "include/rex/ppc/intrinsics.h").read_bytes()).hexdigest().upper(),
                   "macrosSha256": hashlib.sha256((out / "fh2_macros.h").read_bytes()).hexdigest().upper(),
                   "executableSha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
                   "staticInstructionWords": {f"{k:08X}": f"{v:08X}" for k,v in words.items()},
                   "gameLaunched": False, "sdkDllLoaded": False, "devicesInitialized": False, "queueExecuted": False,
                   "hookAdded": False, "sceneReplayEstablished": False, "runtimeReceiverEstablished": False})
    (out / "result.json").write_text(json.dumps(record, indent=2)+"\n")
    print(f"ORDERING PASS: {record['checks']} actual camera overwrite/cache checks,12 cases,26 guest functions; CULLING {'HOLD' if hold else 'PASS'} ({record['projectionPlaneDisagreements']} projection/plane disagreements, {record['baselineMissingInterior']} missing baseline interiors); no game/device/queue")
    return 2 if hold else 0


if __name__ == "__main__":
    raise SystemExit(main())
