"""Qualify closed special-AABB and bucket-query helpers, retaining culling HOLD.

No packet publisher, allocator, sort, submission, SDK DLL or device route runs.
Private generated code and image are required, with the parent's image guard.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("visibility_fixture", Path(__file__).with_name("fh2_visibility_check.py"))
visibility = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visibility)
camera = visibility.camera
camera.ALLOWED |= {"sub_8244FB10", "sub_82EDBE28", "sub_82EE7A10"}

HELPERS = visibility.HELPERS + r'''
constexpr uint32_t extraPlanes=0x40062000,tagOut=extraPlanes+64,poolOwner=0x40090000,pool=poolOwner+56888;
void ExtraPlane(unsigned index,float d){const auto a=extraPlanes+16*index;Put(a,1);Put(a+4,0);Put(a+8,0);Put(a+12,d);}
uint32_t Special(unsigned count){
 auto c=Context();c.r3.u32=camera+288;c.r4.u32=extraPlanes;c.r5.u32=count;c.r6.u32=0;c.r7.u32=tagOut;
 simde_mm_store_si128((simde__m128i*)c.v1.u8,simde_mm_shuffle_epi8(simde_mm_load_si128((simde__m128i*)(memory+boxMin)),simde_mm_load_si128((simde__m128i*)VectorMaskL)));
 simde_mm_store_si128((simde__m128i*)c.v2.u8,simde_mm_shuffle_epi8(simde_mm_load_si128((simde__m128i*)(memory+boxMax)),simde_mm_load_si128((simde__m128i*)VectorMaskL)));
 sub_8244FB10(c,memory);return c.r3.u32;
}
bool TagGuard(){for(int i=-16;i<20;++i)if(!(i>=0&&i<4)&&memory[tagOut+i]!=0xA5)return false;return true;}
bool HasRecords(unsigned view,unsigned category){auto c=Context();c.r3.u32=poolOwner;c.r4.u32=view;c.r5.u32=category;sub_82EDBE28(c,memory);return c.r3.u32!=0;}
'''
OUTPUT = r'''
 std::printf("],\"specialCases\":[");first=true;
 const float planeOffsets[]={-1,0,1}; // box x[-e,e]: inside, crossing, outside
 const unsigned singleTags[]={8,0,2};
 const unsigned doubleTags[3][3]={{32,40,8},{32,0,10},{2,2,2}};
 for(bool fixed:{false,true})for(int flag:{0,1})for(Config p:{Config{.5f,20,60,1.5f},Config{1,50,90,1},Config{.05f,1000,100,2}}){
  rex::ppc::g_fixed_fp_mode.store(fixed);const float z=(p.n+p.f)*.25f,e=p.n*.001f;
  Init(p.n,p.f,p.fov,p.aspect,flag);Sym();Consume();ConsumerBox(0,0,z,e);
  const auto ordinary=Aabb(camera+288);Check(ordinary==2,"special control has fully inside parent frustum");
  uint8_t cameraBefore[512];std::memcpy(cameraBefore,memory+camera,512);
  for(unsigned count:{1u,2u})for(unsigned a=0;a<3;++a)for(unsigned b=0;b<(count==1?1u:3u);++b){
   ExtraPlane(0,planeOffsets[a]);ExtraPlane(1,planeOffsets[b]);std::memset(memory+tagOut-16,0xA5,36);
   const auto result=Special(count),tag=Word(tagOut),expected=count==1?singleTags[a]:doubleTags[a][b];
   Check(result==ordinary,"supplemental planes retain parent classification");
   Check(tag==expected,"supplemental classification tag table");Check(TagGuard(),"special output owns only four tag bytes");
   std::printf("%s{\"fixedFp\":%s,\"flag272\":%d,\"near\":%.9g,\"planeCount\":%u,\"firstClass\":%u,\"secondClass\":%u,\"result\":%u,\"tag\":%u}",first?"":",",fixed?"true":"false",flag,p.n,count,a,b,result,tag);first=false;
  }
  Check(std::memcmp(cameraBefore,memory+camera,512)==0,"special helper leaves parent frustum unchanged");
  ConsumerBox(0,0,-z,e);Bits(tagOut,0x12345678);Check(Special(2)==0&&Word(tagOut)==0x12345678,"parent rejection returns zero without writing tag");
 }
 // Pool constructor leaves the fourth header word and following owner bytes alone.
 std::memset(memory+pool-16,0xA5,2672);auto c=Context();c.r3.u32=pool;sub_82EE7A10(c,memory);
 bool headers=true;for(unsigned i=0;i<160;++i)headers=headers&&Word(pool+16*i)==0&&Word(pool+16*i+4)==0&&Word(pool+16*i+8)==0&&Word(pool+16*i+12)==0xA5A5A5A5;
 Check(headers,"160 pool headers clear three pointer words and preserve fourth word");
 bool extents=true;for(unsigned i=0;i<16;++i)extents=extents&&Word(pool+2560+4*i)==Word(i%2?0x82000ACC:0x82000AC8);
 Check(extents,"pool initializes two groups of four min/max pairs from image constants");
 bool guard=true;for(int i=-16;i<0;++i)guard=guard&&memory[pool+i]==0xA5;for(int i=2624;i<2656;++i)guard=guard&&memory[pool+i]==0xA5;
 Check(guard,"pool constructor preserves preceding and following bytes including field2624");
 for(unsigned view=0;view<32;++view)for(unsigned category=0;category<5;++category){
  const auto header=pool+16*(5*view+category);Bits(header,0x400A0000);
  for(unsigned count:{0u,1u,3u}){
   Bits(header+4,0x400A0000+20*count);uint8_t before[16];std::memcpy(before,memory+header,16);
   Check(HasRecords(view,category)==(count!=0),"bucket query uses selected view/category and twenty-byte records");
   Check(std::memcmp(before,memory+header,16)==0,"bucket query is read-only");
  }
  Bits(header,0);Bits(header+4,0);
 }
'''


def main():
    marker = ' std::printf("],\\\"checks\\\":%d,'
    if camera.HARNESS.count(marker) != 1:
        raise ValueError("Camera fixture output marker changed")
    camera.HARNESS = camera.HARNESS.replace("int main(int argc,char** argv){", HELPERS+"int main(int argc,char** argv){")
    camera.HARNESS = camera.HARNESS.replace(marker, visibility.VISIBILITY+OUTPUT+marker)
    status = camera.main()
    out = Path(sys.argv[sys.argv.index("--out")+1])
    record = json.loads((out / "result.json").read_text())
    if len(record["specialCases"]) != 144 or len(record["aabbCases"]) != 12 or record["projectionPlaneDisagreements"] != 12:
        raise ValueError("Special cases or retained negatives changed")
    summary = {"status":"closed-output-helpers-pass-culling-held", "newChecks":record["checks"]-790,
               "combinedChecks":record["checks"], "specialCases":144,"bucketQueries":480,
               "kind1AabbRejections":sum(v["kind1Result"] == 0 for v in record["aabbCases"]),
               "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
               "visibilityScriptSha256":hashlib.sha256(Path(visibility.__file__).read_bytes()).hexdigest().upper(),
               "consumerResultSha256":hashlib.sha256((out / "result.json").read_bytes()).hexdigest().upper(),
               "allocatorExecuted":False,"sortExecuted":False,"submissionExecuted":False,"cullingAdmitted":False}
    (out / "output-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(f"{summary['newChecks']} closed output-helper checks PASS; prior790 checks/12 negatives retained")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
