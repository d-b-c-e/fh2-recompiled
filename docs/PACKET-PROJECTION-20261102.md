# Packet records reconstruct symmetric frustums from scalar camera data

The traced producers carry view matrices and FOV/aspect/clip values into the
packet. They rebuild symmetric frustums from those fields; the traced field
paths do not copy the camera's stored projection at +80. Packet+9216 holds an
**inverse-view matrix**, not a projection. `82F42C50` writes 32-byte FOV/distance
metadata rather than a 4x4 matrix. **CULLING HOLD remains.**

190 static checks pass. A closed offline fixture also passes **78 new actual
packet-math checks**, 446 combined checks, while retaining all 12 prior kind-1
projection/interior disagreements and exit 2.

## View record source: direct and recorded paths

Packet publisher `82F5AF30` reads the view's camera at view+400. Its direct
camera branch uses these established base/refcounted camera methods:

| Packet field | Camera getter | Source |
| --- | --- | --- |
| 9152..9215 | slot 180, 82476B00 | Camera view matrix at +16, 64 bytes |
| 9280 | slot 60, 82470088 | FOV at +260 |
| 9284 | slot 72, 82400E48 | Aspect at +256 |
| 9288 | slot 188, 82401630 | Near at +208 |
| 9292 | slot 192, 82473410 | Far at +212 |

The recorded branch copies a 64-byte matrix from a selected 128-byte record's
+16 and four scalars from +80/+84/+88/+92 to those same packet fields. Its
selection depends on the recorder result at `82F566E8`; it is not universally
the direct branch. Record+80 is a scalar field in this structure, not camera+80.

The publisher calls matrix inverse helper `82422D80` on the view matrix and
stores the result at packet+9216..9279. No direct slot-184 projection-getter
call was found in this producer. Slot 184, `82475C48`, would copy the stored
camera projection at +80. This is a bounded source finding about these paths,
not proof that the renderer never reads that projection elsewhere.

## Selected position and six axial views

`82F46458` chooses an 80-byte presentation entry using packet+9136 and the
span at +9120/+9124. From that entry it copies the translation at +48/+52/+56,
adds 0.5 to Y, and stores the point at packet+9328 with a flag at +9344.
An empty span selects the explicit fallback point and clears the flag. The
80-byte entries are not relabelled projection matrices or triple-screen views.

`82F47188` builds six view matrices about that point using `82475C80` and an
identity orientation. The directions are +X, -X, +Y, -Y, +Z and -Z. Each calls
symmetric frustum constructor `823FB1B0`, using packet fields +9304/+9308/
+9312/+9316 for FOV/aspect/near/far. The producer forces +9316 to 5000; face 3
(-Y) overrides far to 2.5. The six-axis geometry is established; a cubemap
rendering purpose is an inference, not a demonstrated resource/pass identity.

## Per-record construction

Frustum records begin at packet+1440 with stride 192. Their companion metadata
begins at +8096 with stride 32. These indices describe the source operations,
not accepted player-facing view roles:

| Record index | Inputs to symmetric frustum construction |
| --- | --- |
| 0..5 | Six axial transforms and scalar group 9304..9316, with face-3 far override |
| 6 | Active native mirror selector 0 or 1 transform/scalars |
| 7 | Native mirror selector 2 transform/scalars |
| 8 | Native mirror selector 3 transform/scalars |
| Value at packet+36 | View matrix 9152..9215 and scalars 9280..9292 |
| Value at packet+40 | Same view/FOV/near with a separately bounded far value |
| 15 | Same view/FOV/near with far from packet+10224 |

The mirror selectors are conditional; selector 0/1 sharing index 6 does not
establish that both run in a frame. Index values at +36/+40 come from view
fields +404/+408. Their actual branch execution and final draw-role mapping
remain unproved. Additional work in `82F44138` is outside this classification.

## 82F42C50 is metadata, not projection storage

The helper reads the existing field at record+20. In its nonnegative branch it
copies a vector from frustum+160, negates its Z coordinate and writes a squared
FOV scale at metadata+16. It preserves +20. Its angle helper is `82402C80`,
applied to degree-to-radian half angles; the scale is the squared current-FOV/
reference-FOV helper-result ratio. A zero current FOV takes its explicit scale-1
shortcut. A negative +20 uses the fallback vector and writes ones at +16/+24.

For current FOV 90 and reference FOV 60, the actual fixture observes
`3.00000024`. This scalar metadata and its source-specific Z flip do not
qualify a global coordinate convention or GPU projection matrix.

## Isolated packet-math qualification

`windows/tools/fh2_packet_frustum_check.py` reuses the closed camera fixture and
adds six real functions/helpers, for 34 linked generated functions. It executes
`82F47188`, `82475C80`, `82F42C50` and their actual math callees on synthetic
guest memory. It does **not** execute `82F5AF30`, the packet worker, queues,
scene traversal, graphics or an SDK runtime DLL.

Under both FP policies, the 78 new checks establish:

- All six frustums accept a forward interior, reject a backward point and
  reject a point beyond the appropriate far limit, including face 3's 2.5.
- Metadata reflects input origin (2,3,4) as (2,3,-4), gives the expected FOV
  scale, and preserves the incoming distance field.
- The negative-distance fallback writes the expected fields and leaves the
  next 32 bytes unchanged. These outputs are not 64-byte projection matrices.
- The isolated six-frustum call leaves packet bytes outside the declared
  frustum/metadata ranges unchanged.

The prior 368 checks also pass. The original 12/12 kind-1 projection/plane
disagreements remain intact, so the combined tool still exits 2 and its owned
receipt remains failed. Passing isolated symmetric packet math does not clear
the camera kind-1 contract or prove a live frame's visibility.

Next source work should follow these frustum/metadata records through
`82EF12D0`/`82450DE8` and distinguish their visibility masks from the actual GPU
projection path. A camera-object matrix write alone does not establish coherent
packet culling. No guessed swap, plane negation, bypass or renderer hook is added.

## Reproduce and retained evidence

Read-only static trace uses the command in the preceding camera documents.
From a VS x64 developer shell, under the CPU GO/owned-process route:

```powershell
python -I windows/tools/fh2_packet_frustum_check.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-private-output>
```

Private root: `windows/.local/packet-projection/`.

- `static02/result.json`, 190 checks / 67 selected hashes / 85,237 functions:
  `79A02EA74A87D2F2D15DDB7F1F95EC5B1B429F3C2829D220082AA5A9F19C7E3B`.
- `runtime02/result.json`, 446 checks with retained CULLING HOLD:
  `C4AC17B3F6AEB995040B916ECEA2F07C161936840BA1ECB249561400D049ADC9`.
- `runtime02/packet-summary.json`, 78 new isolated packet checks:
  `670481B71D9B5E4813C8655B2FEDAD7273FA84A1421633558CA3DDB080375440`.
- `owned02/result.json`, safely released despite the expected HOLD exit:
  `9A66DA3ABEBF35D2524975F738B16CF5DBE7F19EE7922A682D7539416B347359`.

GO494570 interval 2026-11-02T16:34:47Z..16:34:54Z, jobs 1, BelowNormal;
children quiescent, process census safe, lease released and literal absent.
GO494539's compile-only `far` macro/name collision remains in runtime01/owned01;
the fixture local was renamed `farClip` before the fresh run. Wrong-image
refusal before compile/output passes. All generated bodies/image/executable
remain private. No game/window/device initialization, installation or owner
state changes occurred. Native 734fff4 / SDK e223de8d remain frozen.
