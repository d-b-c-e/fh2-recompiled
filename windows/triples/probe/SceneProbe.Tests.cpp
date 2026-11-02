#include "SceneProbe.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <vector>
struct Memory { std::vector<std::uint8_t> bytes; unsigned reads{}; };
bool Read(void* opaque, std::uint32_t address, void* out, std::size_t count) {
  auto& m = *static_cast<Memory*>(opaque);
  ++m.reads;
  if (address > m.bytes.size() || count > m.bytes.size() - address) return false;
  std::memcpy(out, m.bytes.data() + address, count); return true;
}
int main() {
  using namespace fh2::probe;
  Memory m{std::vector<std::uint8_t>(15000)};
  for (std::size_t i = 0; i < m.bytes.size(); ++i) m.bytes[i] = std::uint8_t(i);
  const auto before = m.bytes;
  Record record{};
  assert(Capture(Read, &m, Boundary::CameraFeed, 7, 0x8262CC40, 0, record));
  assert(record.sequence == 7 && record.pc == 0x8262CC40 && m.reads == 5);
  assert(record.words[0] == 0x00010203 && record.words[4] == 0x28292A2B);
  assert(Capture(Read, &m, Boundary::PacketReady, 8, 0x82F5AF30, 0, record));
  assert(record.words[2] == 0x1C1D1E1F && record.words[4] == 0xD0D1D2D3);
  const auto retained = record;
  assert(!Capture(Read, &m, Boundary::VisibilityWork, 9, 0x82450DE8, 14000, record));
  assert(record.sequence == retained.sequence && record.words == retained.words);
  unsigned reads = m.reads;
  std::uint32_t value = 0;
  assert(!Word(Read, &m, 0xFFFFFFFE, 4, value) && m.reads == reads);
  assert(!Word(Read, &m, 0xFFFFFFFE, 0, value) && m.reads == reads);
  assert(!Word(nullptr, &m, 0, 0, value));
  assert(m.bytes == before);
  std::cout << "PASS: endian, exact fields, bounded reads, overflow refusal, atomic output, no guest writes\n";
}
