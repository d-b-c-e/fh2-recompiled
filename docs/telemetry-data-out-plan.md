# FH2 Data Out: guest state and a first implementation path (source only, 2026-10-23)

This is a plan for miho 370655. Nothing has been built or run. It is kept separate from the refusal-site fix (`muzu/fh2-gear-refusal-20261023`), which it does not touch. It builds on Nepo's feasibility notes (hub `artifacts/fh2-telemetry-feasibility-nepo-20261023`, which find a host seam but no sender) and on Tile's reader offsets.

## Where the values live (guest evidence)

`I` is the car's `ICarDynamics` interface (`*(car+11664)`); `B = I − 2768` is `CCarDynamics`.

| Value | Location | Evidence |
| --- | --- | --- |
| Current gear | `I+2240` (u8: 0 R, 1-8, 9 N) | Transmission writes it as `B+5008` (`sub_82EBC460`/`sub_82EBCAD8` states 0/4/7); FH1 upstream `dynamics.gear` |
| Speed | `I+3128` (f32, **m/s**) | Car vtable `+344` getter `sub_82EA8340`; `sub_824ABF00` multiplies it by 2.2369 (`0x82005908`) and compares the result with an mph threshold |
| Engine speed | `I+324` (f32 rad/s; × 9.5493 gives RPM) | `B+3092` in the clutch slip, rev-match and stall checks |
| Redline / limiter / idle | `I+452` / `I+456` / `I+1228` | `B+3220` is the rev-match clamp in `sub_82EB8240`; `B+3996` is read in transmission state 0; FH1 upstream objects.toml |
| Gas, brake, steer, clutch, handbrake | the 28-byte controls (f32 at +0/+4/+8/+12/+16; steer −1..1) | The sampler `sub_824972C0` builds them; the car keeps them at `I+3904` |

## Which car, and when to sample

Hooking the guest's own hand-over avoids the static-chain player-index question and the sampling-boundary question:
- `sub_8249A8E8` (single caller `sub_823F31D0`) is the local input controller. It reads the pad and runs the sampler.
- It then calls the car through vtable `+80` at **`0x8249B3F0` `bctrl` (`4E800421`)**, after `lwz r3,0(r3)` (`80630000`), `addi r4,r1,96` (`38810060`), `lwz r11,0(r3)`, `lwz r11,80(r11)` (`816B0050`) and `mtctr`.
- At that instruction r3 is the controlled car's dynamics interface and r4 is the controls.
- That is the game thread, once per input step, after the controls are built and before physics uses them.

## First implementation (bounded)

1. **Codegen hook** in the existing Windows-only `windows/fh2_dbce_overrides.toml`: `[[midasm_hook]] address = 0x8249B3F0, name = "Fh2TelemetryHandOff", context = true`. It is a void hook, with no return or jump.
2. **`windows/src/fh2_telemetry.cpp`, the hook.** On the game thread it only:
   - checks that `I` and the controls are readable guest ranges, and refuses otherwise;
   - copies the seven controls, the gear, the speed, the engine speed, the redline, the limiter and the idle;
   - stamps a host time and a step counter into a seqlock snapshot.
3. **Sender.**
   - **Lifecycle:** one thread, started in `Fh2App::OnPostSetup` and joined in `OnShutdown`, the existing lifecycle Nepo identified.
   - **Rate and destination:** about 60 Hz, nonblocking UDP to `127.0.0.1`. The port comes from a new cvar that defaults to off, and the layout to a cvar (Horizon 324 by default, or FM7 311).
   - **Encoder:** the toolkit's header-only `native/forza/forza_packet.h`, vendored or pinned as other consumers do.
4. **Mapping.**
   - Gear 0 → 0 (R), 9 → 11 (N), 1-8 unchanged (toolkit `cf9e212`, hub `f95945d0`).
   - Speed as-is in m/s.
   - RPM = rad/s × 9.5493.
   - Pedals use `pedal01`; steer uses `steer11`.
   - Fields with no traced source stay zero, the toolkit's "leave alone" rule: accelerations, velocity and angular vectors, wheels, position, lap/race and the car identity fields.
5. **`IsRaceOn` (provisional).** 1 while the hook fired within the last 250 ms, else 0, with zeroed frames keeping the engine constants as the toolkit idle rule says. Whether the controller stops stepping in pause and menus is a runtime fact, unproven.

## Checks before any runtime

- **Codegen check** in the refusal-fix style: exactly one telemetry hook, emitted before the `bctrl` at `0x8249B3F0`; the continuation `0x8249B3F4` and the sampler unchanged; the refusal hook untouched.
- **Host unit test** of snapshot → packet through the toolkit encoder: the gear mapping including 9 → 11, speed, RPM, pedals, the 324/311 lengths, and that stale snapshots give IsRaceOn = 0.
- **Fake-guest-memory fixture** for the hook's reads, including refusal of unreadable ranges.

## Runtime gates (attended, later)

- SimHub receives exactly 324 bytes.
- Gear, speed and RPM match the HUD in R, N and 1-6.
- The pause and menu IsRaceOn behaviour is observed.
- There is no frame-time cost.

## Not established

- **Local-only scope.** That `sub_8249A8E8` serves only local human cars was inferred from its pad reads, not proven for online or AI.
- **Missing sled fields.** No source is traced for wheels (FH1's `+3936`/1024 stride is unverified on FH2), the velocity vector or position.
- **Race identity and lap data.** Not traced.
