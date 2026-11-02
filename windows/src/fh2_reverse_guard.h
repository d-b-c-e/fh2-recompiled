// fh2 - the H-shifter's reverse request obeys the stock paddle speed limit (owner decision, miho 371206).
//
// Stock FH2 refuses a paddle shift from 1 into reverse unless the forward velocity is below
// MaxForwardVelShiftReverseMPH (15.0 in PhysicsSettings.ini), but applies an H-gate reverse request at any speed.
// Both H-gate blocks (Manual sub_82EBC460 at 0x82EBC658, ManualWithClutch sub_82EBCAD8 at 0x82EBCCC0) now run the
// paddle's own test first: when it refuses, the reverse request becomes "no request" (10) for that physics step.
// Neutral, forward gears and reverse below the limit are untouched; a held R engages once the car is slow enough.
//
#pragma once
#include <cstdint>
#include <cstring>
#include <rex/ppc/intrinsics.h>

namespace fh2::reverse_guard {

// CCarDynamics ("B", r31 in both handlers). Guest memory is big-endian.
inline constexpr uint32_t kRequest = 6696;    // u8 gate request: the per-step working copy, restored from B+5848
                                              // by sub_82EBD0B0 at the start of every step
inline constexpr uint32_t kVelocity = 192;    // vec4, m/s (first three components)
inline constexpr uint32_t kForward = 144;     // vec4, the car's forward axis
inline constexpr uint32_t kLimitMph = 0x835FE378u + 360;  // Physics MaxForwardVelShiftReverseMPH (f32)
inline constexpr uint32_t kMphToMps = 0x8200590Cu;        // .rdata 0.44704 (f32)
inline constexpr uint8_t kReverse = 0, kNoRequest = 10;

inline float LoadF32(const uint8_t* base, uint32_t address) {
  uint32_t v;
  std::memcpy(&v, base + address, 4);
  v = __builtin_bswap32(v);
  float f;
  std::memcpy(&f, &v, 4);
  return f;
}

// The paddle ShiftDown test, as the generated code computes it: vmsum3fp128(B+192, B+144) (double products,
// (x + z) + y, narrowed to float) against float(limit_mph * 0.44704); reverse is allowed only when strictly below.
inline float ForwardVelocity(const uint8_t* base, uint32_t b) {
  double p[3];
  for (int i = 0; i < 3; ++i)
    p[i] = double(LoadF32(base, b + kVelocity + 4 * i)) * double(LoadF32(base, b + kForward + 4 * i));
  return rex::ppc::simde_mm_vmsum_narrow_result((p[0] + p[2]) + p[1]);
}
inline float Limit(const uint8_t* base) { return float(double(LoadF32(base, kLimitMph)) * double(LoadF32(base, kMphToMps))); }
inline bool Refuses(float forward, float limit) { return !(double(forward) < double(limit)); }  // NaN refuses, as stock

// At the start of an H-gate block: a reverse request the paddle test refuses becomes no request for this step.
inline void Apply(uint8_t* base, uint32_t b) {
  if (base[b + kRequest] == kReverse && Refuses(ForwardVelocity(base, b), Limit(base))) base[b + kRequest] = kNoRequest;
}

}  // namespace fh2::reverse_guard
