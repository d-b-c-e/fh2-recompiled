"""Check two closed 20-byte ordering leaves against an unsigned stable oracle.

Retains all earlier negative culling observations. No recursive ordering,
submission/state emitter, allocator, SDK DLL, game or device route executes.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("output_fixture", Path(__file__).with_name("fh2_output_consumer_check.py"))
output = importlib.util.module_from_spec(spec)
spec.loader.exec_module(output)
camera = output.camera
camera.ALLOWED |= {"sub_82479CE8", "sub_82480298"}

ORDER = r'''
 std::printf("],\"ordering\":{");
 constexpr uint32_t records=0x400B0000;unsigned orderCases=0;
 using Record=std::array<uint32_t,5>;
 for(bool descending:{false,true})for(unsigned pattern=0;pattern<6;++pattern)for(unsigned n=0;n<=32;++n){
  std::memset(memory+records-32,0xA5,704);std::vector<Record> expected;
  for(unsigned i=0;i<n;++i){
   const uint32_t edge[]={0,0x80000000,0x7FC00001,0xFFFFFFFF,0x7FFFFFFF,0xFF800000,0x3F800000,0};
   const uint32_t key=pattern==0?i:pattern==1?n-1-i:pattern==2?42:pattern==3?i%4:pattern==4?edge[i%8]:(i*1664525u+1013904223u)%11;
   Record r={0x12340000u+i,0xABC00000u^i,key,0x76540000u+i,0xD0C0B000u^i};expected.push_back(r);
   for(unsigned w=0;w<5;++w)Bits(records+20*i+4*w,r[w]);
  }
  std::stable_sort(expected.begin(),expected.end(),[descending](const Record& a,const Record& b){return descending?a[2]>b[2]:a[2]<b[2];});
  auto c=Context();c.r3.u32=records;c.r4.u32=records+20*n;
  if(descending)sub_82480298(c,memory);else sub_82479CE8(c,memory);
  bool exact=true;for(unsigned i=0;i<n;++i)for(unsigned w=0;w<5;++w)exact=exact&&Word(records+20*i+4*w)==expected[i][w];
  Check(exact,"order matches stable unsigned oracle with all twenty payload bytes");
  bool guards=true;for(int i=-32;i<0;++i)guards=guards&&memory[records+i]==0xA5;for(unsigned i=20*n;i<672;++i)guards=guards&&memory[records+i]==0xA5;
  Check(guards,"ordering leaves preserve prefix and unused/following record bytes");
  Check(c.r1.u32==stack&&c.lr==0x823F1234&&c.r31.u64==0x123456789ABCDEF0,"ordering leaf preserves stack LR and nonvolatile sentinel");
  uint8_t once[704];std::memcpy(once,memory+records-32,704);c=Context();c.r3.u32=records;c.r4.u32=records+20*n;
  if(descending)sub_82480298(c,memory);else sub_82479CE8(c,memory);
  Check(std::memcmp(once,memory+records-32,704)==0,"ordering twice is byte-exact idempotent");++orderCases;
 }
 std::printf("\"cases\":%u,\"patterns\":6,\"minimumCount\":0,\"maximumCount\":32,\"directions\":2}",orderCases);
'''


def main():
    marker = ' std::printf("],\\\"checks\\\":%d,'
    if camera.HARNESS.count(marker) != 1:
        raise ValueError("Camera fixture output marker changed")
    camera.HARNESS = camera.HARNESS.replace("#include <cstdint>", "#include <algorithm>\n#include <array>\n#include <cstdint>")
    camera.HARNESS = camera.HARNESS.replace("int main(int argc,char** argv){", output.HELPERS+"int main(int argc,char** argv){")
    camera.HARNESS = camera.HARNESS.replace(marker, output.visibility.VISIBILITY+output.OUTPUT+ORDER+marker.replace('("],', '(",'))
    status = camera.main()
    out = Path(sys.argv[sys.argv.index("--out")+1])
    record = json.loads((out / "result.json").read_text())
    if record["ordering"]["cases"] != 396 or record["checks"] != 3853 or record["projectionPlaneDisagreements"] != 12:
        raise ValueError("Ordering cases or retained negative controls changed")
    summary = {"status":"closed-order-leaves-pass-culling-held","newChecks":1584,
               "combinedChecks":record["checks"],"cases":396,"patterns":6,"countRange":[0,32],
               "kind1AabbRejections":sum(v["kind1Result"] == 0 for v in record["aabbCases"]),
               "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
               "outputScriptSha256":hashlib.sha256(Path(output.__file__).read_bytes()).hexdigest().upper(),
               "visibilityScriptSha256":hashlib.sha256(Path(output.visibility.__file__).read_bytes()).hexdigest().upper(),
               "consumerResultSha256":hashlib.sha256((out / "result.json").read_bytes()).hexdigest().upper(),
               "recursiveOrderExecuted":False,"allocatorExecuted":False,"submissionExecuted":False,"cullingAdmitted":False}
    (out / "order-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("1584 closed ordering-leaf checks PASS; prior2269 checks/12 negatives retained")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
