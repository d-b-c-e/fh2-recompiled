"""Exercise closed visibility mask and AABB helpers on synthetic guest memory.

Retains the parent camera fixture's culling HOLD. Never runs the dispatcher,
worker, resource traversal, virtual instance methods or output-list allocator.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("camera_fixture", Path(__file__).with_name("fh2_camera_consumer_check.py"))
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)
camera.ALLOWED |= {"sub_8244EEE8", "sub_8244DFA8", "sub_8244EF08", "sub_82451138", "sub_824513C0"}

HELPERS = r'''
constexpr uint32_t instance=0x40060000,boxMin=0x40061000,boxMax=boxMin+16,planes=boxMin+32;
void Bits(uint32_t a,uint32_t w){w=__builtin_bswap32(w);std::memcpy(memory+a,&w,4);}
void Box(float x,float y,float z,float e){
 const float v[]={x,y,z};for(int i=0;i<3;++i){Put(boxMin+4*i,v[i]-e);Put(boxMax+4*i,v[i]+e);}Put(boxMin+12,1);Put(boxMax+12,1);
}
// 8244ED60 negates/swaps Z bounds before calling82451138.
void ConsumerBox(float x,float y,float z,float e){Box(x,y,-z,e);}
uint32_t Aabb(uint32_t record){
 auto c=Context();c.r3.u32=record;
 simde_mm_store_si128((simde__m128i*)c.v1.u8,simde_mm_shuffle_epi8(simde_mm_load_si128((simde__m128i*)(memory+boxMin)),simde_mm_load_si128((simde__m128i*)VectorMaskL)));
 simde_mm_store_si128((simde__m128i*)c.v2.u8,simde_mm_shuffle_epi8(simde_mm_load_si128((simde__m128i*)(memory+boxMax)),simde_mm_load_si128((simde__m128i*)VectorMaskL)));
 sub_82451138(c,memory);return c.r3.u32;
}
void SetVisible(unsigned id,unsigned value){auto c=Context();c.r3.u32=instance;c.r4.u32=id;c.r5.u32=value;sub_8244EF08(c,memory);}
bool OnlyVisibilityBytesChanged(const uint8_t* before,unsigned id){
 for(unsigned i=0;i<160;++i)if(i!=54&&i!=76+id&&!(i>=108&&i<112)&&before[i]!=memory[instance+i])return false;return true;
}
'''
VISIBILITY = r'''
 std::printf("],\"aabbCases\":[");first=true;
 for(bool fixed:{false,true})for(int flag:{0,1})for(Config p:{Config{.5f,20,60,1.5f},Config{1,50,90,1},Config{.05f,1000,100,2}}){
  rex::ppc::g_fixed_fp_mode.store(fixed);const float z=(p.n+p.f)*.25f,e=p.n*.001f;
  Init(p.n,p.f,p.fov,p.aspect,flag);Sym();Consume();
  uint8_t before[512];std::memcpy(before,memory+camera,512);
  ConsumerBox(0,0,z,e);const auto forward=Aabb(camera+288);Check(forward!=0,"ordinary AABB accepts symmetric interior");
  ConsumerBox(0,0,-z,e);Check(Aabb(camera+288)==0,"ordinary AABB rejects behind");
  ConsumerBox(0,0,p.f+1,e);Check(Aabb(camera+288)==0,"ordinary AABB rejects beyond far");
  Check(std::memcmp(before,memory+camera,512)==0,"ordinary AABB leaves camera record unchanged");
  Init(p.n,p.f,p.fov,p.aspect,flag);Sym();Asym(p.n);Consume();ConsumerBox(flag?-z:z,0,z,e);
  const auto asymmetric=Aabb(camera+288);
  std::printf("%s{\"fixedFp\":%s,\"flag272\":%d,\"near\":%.9g,\"symmetricResult\":%u,\"kind1Result\":%u}",first?"":",",fixed?"true":"false",flag,p.n,forward,asymmetric);first=false;
 }
 // The mask reader and byte setter own distinct storage. Restrict IDs to0..31.
 for(unsigned id=0;id<32;++id){
  std::memset(memory+instance,0xA5,160);std::memset(memory+instance+76,0,32);memory[instance+54]=0;Bits(instance+108,0);
  Bits(instance+68,0xA5A5A5A5);Bits(instance+72,0x5A5A5A5A);
  auto c=Context();c.r3.u32=instance;c.r4.u32=id;sub_8244EEE8(c,memory);Check(c.r3.u32==((0xA5A5A5A5u>>id)&1),"allowed mask bit");
  c=Context();c.r3.u32=instance;c.r4.u32=id;sub_8244DFA8(c,memory);Check(c.r3.u32==((0x5A5A5A5Au>>id)&1),"second mask bit");
  uint8_t before[160];std::memcpy(before,memory+instance,160);SetVisible(id,1);
  Check(memory[instance+76+id]==1&&memory[instance+54]==1&&Word(instance+108)==1,"false to true increments count and dirties");
  Check(OnlyVisibilityBytesChanged(before,id),"true setter preserves neighbor bytes and masks");
  memory[instance+54]=0;std::memcpy(before,memory+instance,160);SetVisible(id,1);Check(std::memcmp(before,memory+instance,160)==0,"same true is byte-exact no-op");
  SetVisible(id,0);Check(memory[instance+76+id]==0&&memory[instance+54]==1&&Word(instance+108)==0,"true to false decrements count and dirties");
  Check(OnlyVisibilityBytesChanged(before,id),"false setter preserves neighbor bytes and masks");
  memory[instance+54]=0;std::memcpy(before,memory+instance,160);SetVisible(id,0);Check(std::memcmp(before,memory+instance,160)==0,"same false is byte-exact no-op");
 }
 // Independent closed support-plane helper: x<=1, touching and crossing survive.
 for(bool fixed:{false,true}){
  rex::ppc::g_fixed_fp_mode.store(fixed);Put(planes,1);Put(planes+4,0);Put(planes+8,0);Put(planes+12,-1);
  for(int test=0;test<4;++test){
   Box(test==0?0:test==1?1:test==2?1.5f:2,0,0,.5f);
   auto c=Context();c.r3.u32=boxMin;c.r4.u32=boxMax;c.r5.u32=planes;c.r6.u32=1;sub_824513C0(c,memory);
   Check((c.r3.u32!=0)==(test<3),"support-plane accept/touch/cross/outside");
  }
  Box(2,0,0,.5f);auto c=Context();c.r3.u32=boxMin;c.r4.u32=boxMax;c.r5.u32=planes;c.r6.u32=0;sub_824513C0(c,memory);Check(c.r3.u32==1,"zero planes accept");
 }
'''


def main():
    marker = ' std::printf("],\\\"checks\\\":%d,'
    if camera.HARNESS.count(marker) != 1:
        raise ValueError("Camera fixture output marker changed")
    camera.HARNESS = camera.HARNESS.replace("int main(int argc,char** argv){", HELPERS+"int main(int argc,char** argv){")
    camera.HARNESS = camera.HARNESS.replace(marker, VISIBILITY+marker)
    status = camera.main()
    out = Path(sys.argv[sys.argv.index("--out")+1])
    record = json.loads((out / "result.json").read_text())
    if len(record["aabbCases"]) != 12 or record["projectionPlaneDisagreements"] != 12:
        raise ValueError("Visibility cases or retained negatives changed")
    summary = {"status":"isolated-visibility-helpers-pass-culling-held", "visibilityChecks":record["checks"]-368,
               "combinedChecks":record["checks"], "maskViewIds":32, "aabbCases":record["aabbCases"],
               "kind1AabbRejections":sum(v["kind1Result"] == 0 for v in record["aabbCases"]),
               "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
               "consumerResultSha256":hashlib.sha256((out / "result.json").read_bytes()).hexdigest().upper(),
               "dispatcherExecuted":False,"workerExecuted":False,"resourceTraversalExecuted":False,"cullingAdmitted":False}
    (out / "visibility-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(f"{summary['visibilityChecks']} visibility-helper checks PASS; kind1 AABB rejections {summary['kind1AabbRejections']}/12; original12 disagreements retained")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
