# FH2 camera projection oracle and offline adapter

Later [native asymmetric API investigation](OFFAXIS-API-20261102.md) finds a
separate extent setter/builder with a different depth contract. The adapter
below remains tied to this symmetric builder's tested reverse-depth convention.

The actual generated camera builder82F46988 and its math-only callee82468C00
now run in an isolated fixture on synthetic camera/stack memory. This resolves
the **stored engine camera-matrix convention for the tested input modes**;
it does not establish live camera ownership, units, shader/viewport conventions,
culling state, a scene replay boundary or a connected renderer.

## Observed convention

For positive inputs field208=n and field212=f,0<n<f, FOVdegrees at260 and
aspect at256, the stored matrix atcamera+80 is naturally interpreted as
row-vector multiplication, with the following symmetric form:

```text
[ sx  0   0          0 ]
[ 0   sy  0          0 ]
[ 0   0  -q*n/(f-n)  q ]
[ 0   0   n*f/(f-n)  0 ]
```

q=+1 when r4=0 (positive-Z forward), q=-1 when r4 is nonzero (negative-Z
forward). Nearz=q*n maps to normalized depth1; farz=q*f maps to0.
Camera byte272 nonzero negates **both** sx and sy by using the negative FOV
conversion factor. No semantic mirror/display label is inferred for that flag.

Static constructor82F46838 writes defaultfield208 from image82000ADC
(0.0099999998),field212 from82000B58 (1000), defaultFOV90 and aspect1. This
corroborates the small/large clip order; the constructor is not executed by
the oracle. Runtime selection of mode/flag and the native physical unit scale
still require source/trace correlation. The pure builder itself is unit-agnostic.

The builder writes16 projection floats at+80, mode at+12, zero at+8 and dirty
byte480=1. The fixture checks those state effects, unchanged64-byte pose at+16,
restoredr30/r31 and stack pointer. This is not a full-object/state rollback proof.

## Adapter contract

`GuestProjection.EncodeForMetres` consumes the existing canonical
OffAxisProjection, preserving its X/Y scales and asymmetric offsets. It returns
16 row-major float values for a **consumer explicitly using metre coordinates**,
with reversed depth, an explicit forward-axis choice and explicit clip-X/Y
negation. It scales the depth bias from mm to metres. It derives the depth
coefficients directly from near/far to avoid cancellation at large ratios,
and refuses invalid axis/null/float overflow. The caller must establish actual
runtime units/mode/flags before using this data; there is no automatic choice.

Canonical geometry still comes from the pinned unmodified toolkit149cc66.
This adapter neither recalculates screen geometry nor changes curve warp,
measured-eye policy, camera starting sets, owner measurements or single-screen
framing. It is a managed offline component, not a new CLR dependency in FH2.
No guest-memory writer, hook, native setting or enabled renderer is added.

## Reproduce and interpret the evidence

Use an x64 VS developer shell, the qualified SDK headers and private generated
source from app734fff4/SDKe223de8d, plus the verified private expanded image:

```powershell
python -I windows/tools/fh2_projection_oracle.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-project-output>
dotnet build windows/triples/tests/Fh2.Triples.Tests.csproj -c Release -p:UseSharedCompilation=false -m:1
dotnet windows/triples/tests/bin/Release/net8.0/Fh2.Triples.Tests.dll --guest-oracle <fresh-project-output/oracle.json>
```

The generator refuses any image except SHA256
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`.
It checks the closed direct-call graph (one pure builder/one leaf math function),
emits those generated bodies privately and runs them with actual SDK PPCContext
and intrinsics. It reserves4GiB but commits only synthetic RAM and the24MiB
image as data, never executable guest pages. No SDK DLL or runtime startup is
linked. The one referenced runtime FP-policy variable is fixture-owned, matching
the SDK's x64false default; bothfalse/true policies are exercised. No trig/math
callee is mocked or replaced with a host approximation.

- **288 actual stock matrices pass**: both FP policies, both mode branches,
  both byte272 states, FOV30/60/90/120, aspect1/16:9/32:9 and three clip ranges.
  Stock polynomial trigonometry/single rounding are retained.
- **5,726 combined checks PASS**, .NET build0 warnings/errors. Includes the
  previous534 canonical geometry/config checks, off-axis physical corners from
  flat/curved/asymmetric rigs, both forward/clip-flip choices, reversed depth,
  all stock-oracle matrix coefficients, and wrong-unit/transpose/forward-axis
  negative controls. Float/polynomial comparison tolerance3e-6 relative/absolute
  is explicit; this is not a bit-exact native-render claim.
- Default no-oracle console route passes828 checks. Its documented command now
  uses BuildInParallel=false: `dotnet run -m:1` had forwarded-m:1 into app args,
  which the old test ignored. Build/run are separated for the oracle route.
- Private record `windows/.local/projection-oracle/final-with-constructor/oracle.json`,
  SHA256 `94749EE73356B24965AD7FCE3E83DF29D173C83C9FE19A89A520AEBC42264276`.
  Source/script/context/intrinsics/macros/executable hashes and all numeric
  cases are retained. Generated C++ and image are never published. Initial
  PowerShell flag tokenization/FP-global link failures and exploratory outputs
  remain private. Generated helper vectorization warnings are retained in logs.

No game, native UI/window, GPU/input/device initialization, owner write,
installation, rig lease or new native app/SDK build occurred. Qualified native
734fff4/e223de8d and its private payload remain unchanged. Scene packet ownership,
per-view culling/temporal resources, shader clip integration, compositor and
spanning window still need the [scene trace](SCENE-CUT-TRACE-20261102.md).
