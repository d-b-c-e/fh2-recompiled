// Includes the production sender unchanged; only SDK config/log/context adapters are substituted.
#include "../src/fh2_telemetry.cpp"
#include <atomic>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace fixture {
#if defined(FH2_FIXTURE_SDK_ADAPTERS)
std::mutex registry;
int Port() { std::lock_guard lock(registry); return FLAGS_fh2_telemetry_port_storage_(); }
std::string Format() { std::lock_guard lock(registry); return FLAGS_fh2_telemetry_format_storage_(); }
#endif
void Configure(int port, const char* format) {
  if (!rex::cvar::SetFlagByName("fh2_telemetry_port", std::to_string(port)) ||
      !rex::cvar::SetFlagByName("fh2_telemetry_format", format))
    throw std::runtime_error("fixture cvar update refused");
}
}  // namespace fixture

#if defined(FH2_FIXTURE_SDK_ADAPTERS)
namespace rex::cvar {
bool SetFlagByName(std::string_view name, std::string_view value) {
  std::lock_guard lock(fixture::registry);
  if (name == "fh2_telemetry_port") FLAGS_fh2_telemetry_port_storage_() = std::stoi(std::string(value));
  else if (name == "fh2_telemetry_format") FLAGS_fh2_telemetry_format_storage_() = value;
  else return false;
  return true;
}
}
#endif

using namespace std::chrono_literals;
int checks = 0;
void Check(bool ok, const char* why) {
  if (!ok) throw std::runtime_error(why);
  ++checks;
}
struct Receiver {
  SOCKET socket_ = INVALID_SOCKET;
  int port = 0;
  Receiver() {
    socket_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (socket_ == INVALID_SOCKET) throw std::runtime_error("fixture socket");
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    int size = sizeof address;
    if (bind(socket_, reinterpret_cast<sockaddr*>(&address), size) ||
        getsockname(socket_, reinterpret_cast<sockaddr*>(&address), &size)) {
      closesocket(socket_); throw std::runtime_error("fixture loopback bind");
    }
    port = ntohs(address.sin_port);
  }
  ~Receiver() { closesocket(socket_); }
  Receiver(const Receiver&) = delete;
  std::vector<uint8_t> Receive(int timeout_ms) {
    fd_set readable;
    FD_ZERO(&readable); FD_SET(socket_, &readable);
    timeval timeout{timeout_ms / 1000, (timeout_ms % 1000) * 1000};
    const int ready = select(0, &readable, nullptr, nullptr, &timeout);
    if (ready == SOCKET_ERROR) throw std::runtime_error("fixture select");
    if (!ready) return {};
    std::vector<uint8_t> bytes(512);
    const int size = recv(socket_, reinterpret_cast<char*>(bytes.data()), int(bytes.size()), 0);
    if (size == SOCKET_ERROR) throw std::runtime_error("fixture recv");
    bytes.resize(size); return bytes;
  }
  void Drain() { while (!Receive(0).empty()) {} }
};
uint32_t U32(const std::vector<uint8_t>& p, int offset) {
  uint32_t value{}; std::memcpy(&value, p.data() + offset, sizeof value); return value;
}
template<class Predicate> std::vector<uint8_t> Wait(Receiver& receiver, Predicate accept) {
  const auto until = std::chrono::steady_clock::now() + 2s;
  while (std::chrono::steady_clock::now() < until) {
    auto p = receiver.Receive(50);
    if (!p.empty() && accept(p)) return p;
  }
  return {};
}
void Put(std::vector<uint8_t>& memory, uint32_t address, uint32_t value) {
  value = __builtin_bswap32(value); std::memcpy(memory.data() + address, &value, 4);
}
void Float(std::vector<uint8_t>& memory, uint32_t address, float value) {
  uint32_t bits; std::memcpy(&bits, &value, 4); Put(memory, address, bits);
}
int main() {
  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa)) return 2;
  int status = 0;
  try {
    Receiver a, b;
    constexpr uint32_t car = 0x10000, controls = 0x12000;
    std::vector<uint8_t> memory(0x13000);
    Put(memory, car, fh2::telemetry::kVtableA);
    Float(memory, car + fh2::telemetry::kEngineSpeed, 400.f);
    Float(memory, car + fh2::telemetry::kRedline, 700.f);
    Float(memory, car + fh2::telemetry::kIdle, 80.f);
    Float(memory, car + fh2::telemetry::kSpeed, 25.f);
    Float(memory, controls, 0.5f);
    memory[car + fh2::telemetry::kGear] = 3;
    PPCContext context; context.r3.u32 = car; context.r4.u32 = controls;

    fixture::Configure(0, "horizon");
    fh2::telemetry::Start();
    Fh2TelemetryHandOff(context, nullptr);  // Off must not touch even a valid-looking guest address.
    fixture::Configure(a.port, "horizon");
    auto p = Wait(a, [](const auto& packet) { return packet.size() == 324; });
    Check(!p.empty(), "initially off sender cannot enable without restarting");
    Check(U32(p, 0) == 0 && p[319] == 11 && U32(p, 8) == 0, "enable starts neutral with no old engine constants");
    Fh2TelemetryHandOff(context, memory.data());
    p = Wait(a, [](const auto& packet) { return packet.size() == 324 && U32(packet, 0) == 1; });
    Check(!p.empty() && p[319] == 3 && U32(p, 256) == 0x41C80000, "real handoff reaches loopback with speed and gear");

    fixture::Configure(a.port, "fm7");
    p = Wait(a, [](const auto& packet) { return packet.size() == 311; });
    Check(!p.empty(), "live format change does not reach sender");
    fixture::Configure(b.port, "horizon");
    p = Wait(b, [](const auto& packet) { return packet.size() == 324; });
    Check(!p.empty() && U32(p, 0) == 0 && U32(p, 8) == 0, "retarget starts neutral on the new port");
    a.Drain(); Check(a.Receive(80).empty(), "old destination still receives packets");

    Fh2TelemetryHandOff(context, memory.data());
    p = Wait(b, [](const auto& packet) { return U32(packet, 0) == 1; });
    Check(!p.empty(), "retargeted sender cannot accept a fresh handoff");
    p = Wait(b, [](const auto& packet) { return U32(packet, 0) == 0; });
    Check(!p.empty() && U32(p, 8) != 0 && U32(p, 16) == 0 && p[319] == 11,
          "250ms stale transition must keep constants only and neutral gear");

    fixture::Configure(0, "horizon");
    // Drain any packet already queued before the off change, then prove continued silence.
    const auto silence_deadline = std::chrono::steady_clock::now() + 2s;
    bool quiet = false;
    while (std::chrono::steady_clock::now() < silence_deadline)
      if (b.Receive(80).empty()) { quiet = true; break; }
    Check(quiet, "port0 never becomes silent");
    Check(b.Receive(100).empty(), "port0 keeps transmitting after sampling stops");
    Fh2TelemetryHandOff(context, nullptr);
    fixture::Configure(b.port, "horizon");
    p = Wait(b, [](const auto& packet) { return packet.size() == 324; });
    Check(!p.empty() && U32(p, 0) == 0 && U32(p, 8) == 0, "reenable must discard the previous sample");
    Fh2TelemetryHandOff(context, memory.data());
    Check(!Wait(b, [](const auto& packet) { return U32(packet, 0) == 1; }).empty(), "reenabled sender cannot publish");
    fh2::telemetry::Start();  // Idempotent: one sender remains owned.
    fh2::telemetry::Stop();
    b.Drain(); Check(b.Receive(80).empty(), "Stop returned before sender quiescence");
    fh2::telemetry::Stop();
    fh2::telemetry::Start();
    p = Wait(b, [](const auto& packet) { return packet.size() == 324; });
    Check(!p.empty() && U32(p, 0) == 0 && U32(p, 8) == 0, "restart reuses a previous session sample");
    fh2::telemetry::Stop();
  } catch (const std::exception& e) {
    std::fprintf(stderr, "FAIL after %d checks: %s\n", checks, e.what()); status = 1;
  }
  fh2::telemetry::Stop();
  WSACleanup();
  if (!status) std::printf("PASS: production sender loopback, %d checks, no game/device execution\n", checks);
  return status;
}
