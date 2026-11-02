"""Exercise isolated packet frustum/metadata math without a packet publisher.

Retains the camera fixture's twelve negative culling cases and HOLD exit code.
Only closed generated math functions run on synthetic guest memory.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("camera_fixture", Path(__file__).with_name("fh2_camera_consumer_check.py"))
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)
camera.ALLOWED |= {"sub_82F47188", "sub_82F42C50", "sub_82475C80", "sub_82478900", "__savegprlr_28", "__restgprlr_28"}

HELPER = r'''
float FloatAt(uint32_t a){uint32_t w=Word(a);float f;std::memcpy(&f,&w,4);return f;}
bool InsideRecord(uint32_t record,float x,float y,float z){
 Put(point,x);Put(point+4,y);Put(point+8,z);Put(point+12,1);
 auto c=Context();c.r3.u32=record;c.f1.f64=0;
 simde_mm_store_si128((simde__m128i*)c.v1.u8,simde_mm_shuffle_epi8(simde_mm_load_si128((simde__m128i*)(memory+point)),simde_mm_load_si128((simde__m128i*)VectorMaskL)));
 sub_824153F8(c,memory);return c.r3.u32!=0;
}
'''
PACKET = r'''
 std::printf("],\"packetCases\":[");first=true;
 constexpr uint32_t packet=0x40050000,meta=0x40060000;
 const float axes[6][3]={{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}};
 for(bool fixed:{false,true}){
  rex::ppc::g_fixed_fp_mode.store(fixed);std::memset(memory+packet,0xA5,14000);
  Put(packet+9304,90);Put(packet+9308,1);Put(packet+9312,.1f);Put(packet+9316,100);
  Put(packet+9328,2);Put(packet+9332,3);Put(packet+9336,4);Put(packet+9340,1);
  for(int face=0;face<6;++face)Put(packet+8096+32*face+20,100);
  uint8_t before[14000];std::memcpy(before,memory+packet,14000);
  auto c=Context();c.r3.u32=packet;sub_82F47188(c,memory);
  bool unchanged=true;for(int i=0;i<14000;++i)if(!((i>=1440&&i<2592)||(i>=8096&&i<8288))&&before[i]!=memory[packet+i])unchanged=false;
  Check(unchanged,"isolated packet math writes only six frustum/metadata ranges");
  for(int face=0;face<6;++face){
   const uint32_t record=packet+1440+192*face,m=packet+8096+32*face;
   const auto& a=axes[face];const float farClip=face==3?2.5f:100.f;
   Check(InsideRecord(record,2+a[0],3+a[1],4+a[2]),"axial frustum accepts its forward interior");
   Check(!InsideRecord(record,2-a[0],3-a[1],4-a[2]),"axial frustum rejects its backward point");
   Check(!InsideRecord(record,2+a[0]*(farClip+1),3+a[1]*(farClip+1),4+a[2]*(farClip+1)),"axial frustum respects per-face far clip");
   Check(std::abs(FloatAt(m)-2)<1e-4&&std::abs(FloatAt(m+4)-3)<1e-4&&std::abs(FloatAt(m+8)+4)<1e-4,"metadata copies origin and flips Z");
   Check(std::abs(FloatAt(m+16)-3)<1e-4,"90 versus60 degree FOV squared scale is3");
   Check(FloatAt(m+20)==100,"metadata preserves incoming distance field");
   std::printf("%s{\"fixedFp\":%s,\"face\":%d,\"forward\":[%.0f,%.0f,%.0f],\"far\":%.9g,\"fovWeight\":%.9g}",first?"":",",fixed?"true":"false",face,a[0],a[1],a[2],farClip,FloatAt(m+16));first=false;
  }
  // A negative incoming distance takes the explicit metadata fallback.
  std::memset(memory+meta,0xA5,64);Put(meta+20,-1);uint8_t guard[32];std::memcpy(guard,memory+meta+32,32);
  c=Context();c.r3.u32=meta;c.r4.u32=packet+1440;c.f1.f64=60;c.f2.f64=90;sub_82F42C50(c,memory);
  Check(std::memcmp(memory+meta,memory+0x82001130,16)==0&&FloatAt(meta+16)==1&&FloatAt(meta+24)==1,"negative distance metadata fallback");
  Check(FloatAt(meta+20)==-1&&std::memcmp(guard,memory+meta+32,32)==0,"metadata fallback preserves distance and following32bytes");
 }
'''


def main():
    marker = ' std::printf("],\\\"checks\\\":%d,'
    if camera.HARNESS.count(marker) != 1:
        raise ValueError("Camera fixture output marker changed")
    camera.HARNESS = camera.HARNESS.replace("int main(int argc,char** argv){", HELPER+"int main(int argc,char** argv){")
    camera.HARNESS = camera.HARNESS.replace(marker, PACKET+marker)
    status = camera.main()
    out = Path(sys.argv[sys.argv.index("--out")+1])
    record = json.loads((out / "result.json").read_text())
    if len(record["packetCases"]) != 12 or record["checks"] != 446 or record["projectionPlaneDisagreements"] != 12:
        raise ValueError("Packet checks or retained negative cases changed")
    summary = {"status":"isolated-packet-math-pass-culling-held", "packetChecks":78,
               "combinedChecks":record["checks"], "caseCount":12,
               "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
               "consumerResultSha256":hashlib.sha256((out / "result.json").read_bytes()).hexdigest().upper(),
               "packetPublisherExecuted":False,"queueExecuted":False,"cullingAdmitted":False}
    (out / "packet-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("78 packet frustum/metadata checks PASS; original12 projection/plane disagreements retained")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
