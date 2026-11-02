"""Compare original-word VMX cross products to an observed private SIMD fixture.

Uses the existing closed camera fixture, with observations only in its private
generated constructor. The original negative culling cases remain unchanged.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct

module_path = Path(__file__).with_name("fh2_camera_consumer_check.py")
spec = importlib.util.spec_from_file_location("camera_fixture", module_path)
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)

# Instruction positions, not a copy of guest function bodies or image bytes.
KERNEL = {79:"load",81:"perm",83:"perm",84:"load",86:"perm",87:"copy",
          88:"perm",89:"load",91:"perm",93:"mul",94:"perm",95:"copy",
          96:"load",98:"perm",100:"mul",101:"perm",105:"mul",107:"mul",
          110:"nmsub",111:"copy",115:"copy",116:"copy",119:"nmsub",120:"nmsub",122:"nmsub"}
SAMPLES = [i for i, kind in KERNEL.items() if kind in ("load", "perm", "nmsub")]


def f32(value):
    return struct.unpack(">f", struct.pack(">f", value))[0]


def decode(word, kind):
    """Independent raw bit fields; VMX128 layouts from Xenia ppc_instr.h."""
    d, a, b = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    if kind == "nmsub":
        if word & 0xFC00003F != 0x1000002F:
            raise ValueError("Expected standard VA negative multiply-subtract")
        return d, a, b, (word >> 6) & 31
    d |= ((word >> 2) & 3) << 5
    if kind == "load":
        if word & 0xFC0007F3 != 0x100000C3 or a != 0:
            raise ValueError("Expected indexed corner load")
        return d, a, b, None
    b |= (word & 3) << 5
    if kind == "perm":
        if word & 0xFC000630 != 0x18000210:
            raise ValueError("Expected VMX128 immediate permutation")
        return d, None, b, a | (((word >> 6) & 7) << 5)
    a |= ((word >> 5) & 1) << 5 | ((word >> 10) & 1) << 6
    expected = 0x14000090 if kind == "mul" else 0x140002D0
    if word & 0xFC0003D0 != expected or (kind == "copy" and a != b):
        raise ValueError("Expected vector multiply or same-source OR")
    return d, a, b, None


def reference(words, near):
    # Reproduce setter argument rounding, then evaluate in architectural XYZ/W
    # order. This scalar path uses no SDK vector types or shuffle intrinsics.
    l,t,r,b = [f32(f32(k)*near) for k in (.4,.6,1.6,-.6)]
    corners = iter(((l,t,near,0), (l,b,near,0), (r,b,near,0), (r,t,near,0)))
    regs, samples = {}, {}
    for index, kind in KERNEL.items():
        d,a,b,c = decode(words[index], kind)
        if kind == "load":
            regs[d] = list(next(corners))
        elif kind == "perm":
            regs[d] = [regs[b][(c >> shift) & 3] for shift in (6,4,2,0)]
        elif kind == "copy":
            regs[d] = regs[a].copy()
        elif kind == "mul":
            regs[d] = [f32(x*y) for x,y in zip(regs[a],regs[b])]
        else:
            # VA encoding's B is the addend and C is the other multiplicand.
            regs[d] = [f32(z-x*y) for x,y,z in zip(regs[a],regs[c],regs[b])]
        if index in SAMPLES:
            samples[index] = regs[d].copy()
    # The identity-basis constructor negates these four raw cross products,
    # then normalizes. Compare signs/directions, not reciprocal-estimate bits.
    sides = []
    for index in (110,119,122,120):
        normal = [-x for x in samples[index][:3]]
        length = math.sqrt(sum(x*x for x in normal))
        sides.extend([x/length for x in normal]+[0.])
    return samples, sides


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("generated", "sdk", "image", "cxx", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    raw = args.image.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != camera.IMAGE_SHA:
        raise ValueError("Wrong title image")
    words = {i:struct.unpack_from(">I", raw, 0xE431E0+4*i)[0] for i in KERNEL}
    # Decode before any output/compile. The four load address registers must
    # still reference the checked near corners in their original order.
    for index, address_register in zip((79,84,89,96),(10,9,8,7)):
        if decode(words[index], "load")[2] != address_register:
            raise ValueError("Corner load address changed")
    for index, kind in KERNEL.items():
        decode(words[index], kind)

    def transform(name, body):
        if name != "sub_82E431E0":
            return body
        comments = list(re.finditer(r"\t// (.+)", body))
        for index in reversed(SAMPLES):
            end = comments[index+1].start()
            d = decode(words[index], KERNEL[index])[0]
            body = body[:end]+f"\tObserve({SAMPLES.index(index)}, ctx.v{d}.f32);\n"+body[end:]
        return body

    observer = f"float stages[{len(SAMPLES)}][4]{{}}; void Observe(int i,const float* v){{for(int j=0;j<4;++j)stages[i][j]=v[3-j];}}\n"
    camera.HARNESS = camera.HARNESS.replace("@FUNCTIONS@", observer+"@FUNCTIONS@")
    old = 'std::printf("]}");first=false;'
    replacement = r'''std::printf("],\"vectorStages\":[");for(int a=0;a<16;++a){std::printf("%s[",a?",":"");for(int b=0;b<4;++b)std::printf("%s%.9g",b?",":"",stages[a][b]);std::printf("]");}std::printf("]}");first=false;'''
    if camera.HARNESS.count(old) != 1 or len(SAMPLES) != 16:
        raise ValueError("Fixture observation marker changed")
    camera.HARNESS = camera.HARNESS.replace(old, replacement)
    status = camera.main(transform=transform)
    record = json.loads((args.out / "result.json").read_text())
    checks, max_error = 0, 0.
    for case in record["cases"]:
        samples, sides = reference(words, f32(case["near"]))
        if len(case["vectorStages"]) != len(SAMPLES):
            raise ValueError("Incomplete vector observations")
        for actual, expected in zip(case["vectorStages"], (samples[i] for i in SAMPLES)):
            for a,e in zip(actual,expected):
                checks += 1
                max_error = max(max_error,abs(a-e))
                if not math.isclose(a,e,rel_tol=2e-6,abs_tol=1e-7):
                    raise ValueError("Original VMX and generated SIMD stage disagree")
        for actual, expected in zip(case["planes"][:16], sides):
            checks += 1
            if not math.isclose(actual,expected,rel_tol=2e-6,abs_tol=1e-7):
                raise ValueError("Normalized generated side plane disagrees with original kernel")
    reference_record = {"status":"finite-kernel-agrees-culling-held", "checks":checks,
                        "maxStageAbsError":max_error, "sampleInstructionIndices":SAMPLES,
                        "rawKernelSha256":hashlib.sha256(b"".join(struct.pack(">I", words[i]) for i in KERNEL)).hexdigest().upper(),
                        "originalConsumerResultSha256":hashlib.sha256((args.out / "result.json").read_bytes()).hexdigest().upper(),
                        "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
                        "originalWordDecodeCount":len(KERNEL), "caseCount":len(record["cases"]),
                        "cullingAdmitted":False,"hardwareVmxExecuted":False,"completeIsaQualified":False}
    (args.out / "reference.json").write_text(json.dumps(reference_record,indent=2)+"\n")
    print(f"{checks} independent scalar/stage/side-plane comparisons PASS; CULLING HOLD unchanged")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
