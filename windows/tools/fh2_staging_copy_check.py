"""Check the two closed cached-vector writers against a byte-copy/64-bit-OR oracle.

Retains prior ordering and culling evidence. No cached-bank consumer, command
writer, allocator, submission, SDK DLL, game or device path executes.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("order_fixture", Path(__file__).with_name("fh2_order_leaf_check.py"))
order = importlib.util.module_from_spec(spec)
spec.loader.exec_module(order)
camera = order.camera
camera.ALLOWED |= {"sub_82445C78", "sub_82445B18"}

HELPERS = order.output.HELPERS + r'''
constexpr uint32_t cached=0x400C0000,stageSource=0x400D0000;
void Qword(uint32_t a,uint64_t v){Bits(a,uint32_t(v>>32));Bits(a+4,uint32_t(v));}
void ExpectedQword(std::vector<uint8_t>& bytes,unsigned offset,uint64_t v){for(unsigned i=0;i<8;++i)bytes[offset+i]=uint8_t(v>>(56-8*i));}
void Stage(bool second,unsigned index,unsigned count,unsigned alignment,uint64_t dirty,PPCContext& c){
 c=Context();c.r3.u32=cached;c.r4.u32=index;c.r5.u32=stageSource+alignment;c.r6.u32=count;c.r7.u64=dirty;
 if(second)sub_82445B18(c,memory);else sub_82445C78(c,memory);
}
'''
STAGING = r'''
 std::printf(",\"staging\":{");unsigned stagingCases=0;
 for(bool second:{false,true})for(unsigned index:{0u,1u,127u,128u,235u,255u})for(unsigned count:{0u,1u,3u,4u,5u,21u,32u}){
  if(index+count>256)continue;
  for(unsigned alignment:{0u,1u,3u,4u,7u,15u})for(uint64_t dirty:{0ull,0x00000000FC000000ull,0x8000000000000001ull}){
   std::memset(memory+cached-32,0xA5,10176);Qword(cached,0x0123456789ABCDEFull);Qword(cached+8,0xFEDCBA9876543210ull);
   std::memset(memory+stageSource-16,0x5A,608);for(unsigned i=0;i<512;++i)memory[stageSource+alignment+i]=uint8_t(i*37+alignment*11+count);
   uint8_t sourceBefore[608];std::memcpy(sourceBefore,memory+stageSource-16,608);
   std::vector<uint8_t> expected(memory+cached-32,memory+cached-32+10176);
   const unsigned destination=16*(index+(second?376:120));
   std::memcpy(expected.data()+32+destination,memory+stageSource+alignment,16*count);
   ExpectedQword(expected,32+(second?8:0),(second?0xFEDCBA9876543210ull:0x0123456789ABCDEFull)|dirty);
   PPCContext c;Stage(second,index,count,alignment,dirty,c);
   Check(std::memcmp(expected.data(),memory+cached-32,10176)==0,"staging matches byte-copy/64-bit-OR oracle with whole-owner guards");
   Check(std::memcmp(sourceBefore,memory+stageSource-16,608)==0,"staging preserves source and surrounding bytes");
   Check(c.r1.u32==stack&&c.lr==0x823F1234&&c.r31.u64==0x123456789ABCDEF0,"staging preserves SP LR and nonvolatile sentinel");
   Stage(second,index,count,alignment,dirty,c);Check(std::memcmp(expected.data(),memory+cached-32,10176)==0,"identical staging/dirty OR is byte-exact idempotent");++stagingCases;
  }
 }
 std::printf("\"cases\":%u,\"helpers\":2,\"sourceAlignments\":6,\"dirtyMasks\":3,\"validIndexCountPairs\":36}",stagingCases);
'''


def main():
    marker = ' std::printf("],\\\"checks\\\":%d,'
    if camera.HARNESS.count(marker) != 1:
        raise ValueError("Camera fixture output marker changed")
    camera.HARNESS = camera.HARNESS.replace("#include <cstdint>", "#include <algorithm>\n#include <array>\n#include <cstdint>")
    camera.HARNESS = camera.HARNESS.replace("int main(int argc,char** argv){", HELPERS+"int main(int argc,char** argv){")
    camera.HARNESS = camera.HARNESS.replace(marker, order.output.visibility.VISIBILITY+order.output.OUTPUT+order.ORDER+STAGING+marker.replace('("],', '(",'))
    status = camera.main()
    out = Path(sys.argv[sys.argv.index("--out")+1])
    record = json.loads((out / "result.json").read_text())
    if record["staging"]["cases"] != 1296 or record["checks"] != 9037 or record["projectionPlaneDisagreements"] != 12:
        raise ValueError("Staging cases or retained negatives changed")
    summary = {"status":"closed-staging-copy-pass-culling-held","newChecks":5184,"combinedChecks":record["checks"],
               "cases":1296,"alignedDestination":True,"sourceAlignments":[0,1,3,4,7,15],"zeroCountDirtyOrChecked":True,
               "kind1AabbRejections":sum(v["kind1Result"] == 0 for v in record["aabbCases"]),
               "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
               "dependencySha256":{Path(m.__file__).name:hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest().upper()
                                   for m in (order,order.output,order.output.visibility)},
               "consumerResultSha256":hashlib.sha256((out / "result.json").read_bytes()).hexdigest().upper(),
               "bankConsumerExecuted":False,"commandWriterExecuted":False,"submissionExecuted":False,"cullingAdmitted":False}
    (out / "staging-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("5184 closed staging-copy checks PASS; prior3853 checks/12 negatives retained")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
