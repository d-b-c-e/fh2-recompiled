// fh2 - Forza "Data Out" from the car the local input controller drives (docs/telemetry-data-out-plan.md).
//
// SDK-free on purpose: tools/fh2_telemetry_check.py builds it with fake guest memory and the packet checks.
#pragma once
#include <cstdint>
#include <cstring>

#include "vendor/forza_packet.h"

namespace fh2::telemetry {

// ICarDynamics ("I", *(car+11664); CCarDynamics is I - 2768). Guest memory is big-endian.
inline constexpr uint32_t kVtableA = 0x82003CFC, kVtableB = 0x8224624C;  // the two car-dynamics vtables
inline constexpr uint32_t kEngineSpeed = 324;  // f32 rad/s (B+3092 in the clutch slip and rev-match)
inline constexpr uint32_t kRedline = 452;      // f32 rad/s (B+3220, the rev-match clamp)
inline constexpr uint32_t kIdle = 1228;        // f32 rad/s
inline constexpr uint32_t kGear = 2240;        // u8: 0 R, 1-8, 9 N (the transmission's current gear, B+5008)
inline constexpr uint32_t kSpeed = 3128;       // f32 m/s (vtable +344; sub_824ABF00 multiplies it by 2.2369 for mph)
inline constexpr uint32_t kSpan = kSpeed + 4;  // bytes read from I
inline constexpr uint32_t kControlsSize = 20;  // gas, brake, steer (-1..1), clutch, handbrake: f32 at +0..+16
inline constexpr float kRadPerSecToRpm = 9.5492966f;

struct Snapshot {
  float gas = 0, brake = 0, steer = 0, clutch = 0, handbrake = 0;
  float engine = 0, redline = 0, idle = 0;  // rad/s
  float speed = 0;                          // m/s
  uint8_t gear = 9;                         // guest encoding
};

inline uint32_t LoadU32(const uint8_t* base, uint32_t address) {
  uint32_t v;
  std::memcpy(&v, base + address, 4);
  return __builtin_bswap32(v);
}
inline float LoadF32(const uint8_t* base, uint32_t address) {
  const uint32_t bits = LoadU32(base, address);
  float f;
  std::memcpy(&f, &bits, 4);
  return f;
}

// A guest range the hook may read: not null, no wrap, not the MMIO window. The hook runs right after the game itself
// loaded I's vtable and before it calls through it, so I and the controls on the caller's stack are live.
inline bool Readable(uint32_t address, uint32_t size) {
  const uint64_t end = uint64_t(address) + size;
  return address >= 0x10000 && end <= 0x100000000ull && !(end > 0x7F000000u && address < 0x80000000u);
}

// One snapshot at the controls hand-over. Refuses unless I is a car-dynamics object and both ranges are readable.
inline bool Read(const uint8_t* base, uint32_t dynamics, uint32_t controls, Snapshot& out) {
  if (!Readable(dynamics, kSpan) || !Readable(controls, kControlsSize)) return false;
  const uint32_t vtable = LoadU32(base, dynamics);
  if (vtable != kVtableA && vtable != kVtableB) return false;
  out.gas = LoadF32(base, controls + 0);
  out.brake = LoadF32(base, controls + 4);
  out.steer = LoadF32(base, controls + 8);
  out.clutch = LoadF32(base, controls + 12);
  out.handbrake = LoadF32(base, controls + 16);
  out.engine = LoadF32(base, dynamics + kEngineSpeed);
  out.redline = LoadF32(base, dynamics + kRedline);
  out.idle = LoadF32(base, dynamics + kIdle);
  out.speed = LoadF32(base, dynamics + kSpeed);
  out.gear = base[dynamics + kGear];
  return true;
}

// Forza gear as SimHub decodes it: 0 R, 11 N (toolkit cf9e212), forward unchanged.
inline uint8_t ForzaGear(uint8_t gear) { return gear == 9 ? uint8_t(11) : gear; }

// A packet. `fresh` false (no hand-over lately: menus, pause, no car) keeps only the last engine constants, sends
// IsRaceOn 0 (the toolkit's between-races rule) and gear N, as FH1's empty sample does (not 0, which reads as R).
// Fields with no traced source stay zero.
inline int Build(dbce::forza::Layout layout, const Snapshot& s, bool fresh, uint32_t timestamp_ms, uint8_t* out,
                 int size) {
  dbce::forza::Sled sled;
  dbce::forza::Dash dash;
  std::memset(&sled, 0, sizeof sled);
  std::memset(&dash, 0, sizeof dash);
  sled.timestampMs = timestamp_ms;
  sled.engineMaxRpm = s.redline * kRadPerSecToRpm;
  sled.engineIdleRpm = s.idle * kRadPerSecToRpm;
  dash.gear = ForzaGear(9);
  if (fresh) {
    sled.isRaceOn = 1;
    sled.currentEngineRpm = s.engine * kRadPerSecToRpm;
    dash.speed = s.speed;
    dash.accel = dbce::forza::pedal01(s.gas);
    dash.brake = dbce::forza::pedal01(s.brake);
    dash.clutch = dbce::forza::pedal01(s.clutch);
    dash.handbrake = dbce::forza::pedal01(s.handbrake);
    dash.gear = ForzaGear(s.gear);
    dash.steer = dbce::forza::steer11(s.steer);
  }
  return dbce::forza::build(layout, sled, dash, out, size, 'F');
}

}  // namespace fh2::telemetry
