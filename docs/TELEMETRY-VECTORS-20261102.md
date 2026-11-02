# FH2 dynamics vectors: offline evidence and remaining mapping

The actual FH2 dynamics snapshot producer and vector getters now execute in a
closed fixture. They establish the copy offsets and the vector whose XYZ norm
supplies speed. **No new Data Out fields are enabled.** Native vector space,
axis/sign conversion to the packet's local fields, and position origin/unit
correlation have not all been established. Keeping those fields zero avoids
presenting a plausible vector as a qualified motion signal. Physical output
remains held independently of this research.

## Actual guest paths

`I` is the ICarDynamics subobject; `B=I-2768`. Both image vtables82003CFC and
8224624C have the same four entries below, verified as big-endian image words.
Vector-return calls use hidden output pointerr3 and receiverI inr4; the scalar
speed getter uses receiverI inr3. Confusing these conventions would read the
output buffer as the car.

| Slot | Actual function | Established storage / behavior |
| --- | --- | --- |
|316 |82EB3F58 | Copies16 bytes fromI-2592 (B+176) to caller output |
|328 |82EB5F48 | Withr5 nonzero copies16 bytes fromI-2576 (B+192); zero takes an optional nonlinear curve path |
|344 |82EA8340 | Returns floatI+3128 (B+5896), existing speed source |
|356 |82EB3FB0 | Copies16 bytes fromI-2560 (B+208); no angular-velocity semantic label admitted |

Actual producer82EAAAD8 consumes a synthetic snapshot inr4 and writes:

- input+0 XYZ toI-2592, with homogeneousW forced to1;
- input+16 vector toI-2576 unchanged, and its three-component length toI+3128;
  the fourth component does not contribute to speed;
- input+32 vector toI-2560 unchanged;
- three basis rows frominput+48/+64/+80 toI-2656/+16/+32, with W forced to0.

Static integration routine82EC63A0 independently adds a scaledI-2576 vector
toI-2592, including an acceleration contribution, and updatesI+3128 from the
new vector length. This corroborates a position/linear-velocity relationship.
The routine itself is **not executed**: it has virtual physics/resource calls.
That relationship does not by itself prove the full packet coordinate mapping.
The earlier m/s evidence for scalar speed remains in the historical
[Data Out plan](telemetry-data-out-plan.md).

Adjacent transforms are not enough to label the third vector local angular
velocity:82EA84B8/82EA8530 use different derived3x3 blocks, while82ED3F90 derives
blocks from other matrix/tensor data. An orthogonal rotation and an inertia
tensor must not be treated as interchangeable. Those angular fields remain zero.

## Reproduce

Use a VS x64 developer shell and private generated source/SDK from the qualified
app734fff4/SDKe223de8d pair:

```powershell
python -I windows/tools/fh2_telemetry_vectors_check.py --generated <generated/default> --sdk <sdk> --image <expanded-image.bin> --cxx <clang++.exe> --out <fresh-project-output>
```

The script verifies expanded-image SHA256
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`, the8
vtable words and the closed generated direct-call graph. It emits generated
code only into the private output. Actual save/restore helpers and the optional
curve lookup are linked; only the rawr5=1 vector-getter path is exercised.
No guest callee is mocked. SDK FP-policy global is fixture-owned, tested false
and true. The image is mapped as nonexecutable data, with synthetic stack/car
memory; no SDK DLL or runtime startup is loaded.

The mask at835FDB30 starts in BSS, so a raw image alone is insufficient. The
first fixture correctly failed its homogeneous-W check. Actual pure leaf
initializer832C51F0 writes the XYZ/W bit mask; the corrected fixture executes
and verifies that one initializer, without invoking general game startup.

- **1,274 checks PASS**,10 cases: both FP policies and5 velocity vectors,
  including zero, signed components, fractional values and large values. Norm
  tolerance2e-6 relative/absolute. Nonzero distinctW sentinels prove XYZ-only
  length and homogeneous-lane handling.
- Tests actual16-byte output, surrounding canaries, unchanged source object,
  restored producer nonvolatile registers/SP/LR, copied basis and speed return.
  Synthetic nonidentity basis is used; this is not an axis-conversion proof.
- Wrong-image negative control refuses before output creation or compilation.
- Private result `windows/.local/telemetry-vectors/run02/result.json`, SHA256
  `8157A02DB9F4823BC74F5AFE1C98D79ED28CABB2A2A32986C438F0DF4058B64D`.
  Script/function/header/macros/executable hashes, cases and compile/run logs
  retained. Initialrun01 remains as failure evidence.

## Next boundary

Before wiring local velocity, establish the actual orthogonal body frame and
packet axis/sign mapping. Before position, corroborate track/world origin and
physical scale from actual producers/consumers. A later diagnostic may correlate
these candidates with controlled forward/reverse/lateral motion; this document
does not authorize a game/device run. Existing local-player and pause/menu scope
remain separate runtime gates. New negative-offset reads would also need an
explicit lower-bound check, beyond the current positive telemetry span.

Native734/e223, telemetry header/sender, all packet bytes and the nine-file
private payload are unchanged. No game, window, GPU/input/physical device
initialization, installation, owner-state writes or rig lease occurred.
