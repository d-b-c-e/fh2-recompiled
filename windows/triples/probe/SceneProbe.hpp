#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

// Inert diagnostic adapter: no hook registration, guest calls, writes or waits.
// The future native hook must supply a bounds-checked, nonfaulting copy reader.
namespace fh2::probe {
using MemoryRead = bool (*)(void*, std::uint32_t, void*, std::size_t);
enum class Boundary { CameraFeed, PacketReady, VisibilityWork };
struct Record {
  Boundary boundary{};
  std::uint64_t sequence{};  // Observer order only; never a GPU frame/view identity.
  std::uint32_t pc{}, receiver{};
  std::array<std::uint32_t, 5> words{};
};
inline bool Word(MemoryRead read, void* state, std::uint32_t base,
                 std::uint32_t offset, std::uint32_t& value) {
  if (!read || base > std::numeric_limits<std::uint32_t>::max() - offset ||
      base + offset > std::numeric_limits<std::uint32_t>::max() - 3) return false;
  std::array<std::uint8_t, 4> bytes{};
  if (!read(state, base + offset, bytes.data(), bytes.size())) return false;
  value = (std::uint32_t(bytes[0]) << 24) | (std::uint32_t(bytes[1]) << 16) |
          (std::uint32_t(bytes[2]) << 8) | bytes[3];
  return true;
}
inline bool Capture(MemoryRead read, void* state, Boundary boundary, std::uint64_t sequence,
                    std::uint32_t pc, std::uint32_t receiver, Record& output) {
  Record next{boundary, sequence, pc, receiver, {}};
  // CameraFeed receiver is context r3 at8262CC40; remaining receivers are packet r3.
  const std::array<std::uint32_t, 5> offsets = boundary == Boundary::CameraFeed
      ? std::array<std::uint32_t, 5>{0, 4, 8, 12, 40}
      : std::array<std::uint32_t, 5>{0, 8, 28, 9136, 14032};
  for (std::size_t i = 0; i < offsets.size(); ++i)
    if (!Word(read, state, receiver, offsets[i], next.words[i])) return false;
  output = next;  // Refused/partial copies never publish a successful record.
  return true;
}
}  // namespace fh2::probe
