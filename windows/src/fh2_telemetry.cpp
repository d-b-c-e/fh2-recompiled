// fh2 - Forza "Data Out" telemetry (fh2_telemetry.h, docs/telemetry-data-out-plan.md).
//
// The hook (fh2_dbce_overrides.toml, 0x8249B3F0) runs on the game thread where the local input controller
// sub_8249A8E8 hands its controls to the car through vtable +80: r3 is that car's ICarDynamics, r4 the controls. It
// only copies a snapshot. A sender thread turns the latest one into a packet about 60 times a second and sends it to
// 127.0.0.1 only. Off unless fh2_telemetry_port is set.
//
// Assumptions, not proven: sub_8249A8E8 drives only the local player's car (it reads the pad); the hand-over stops in
// pause and menus, so "no hand-over for 250 ms" is IsRaceOn 0. Both are runtime gates.
#include "fh2_telemetry.h"

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <winsock2.h>
#endif

#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/ppc/context.h>

#include <chrono>
#include <condition_variable>
#include <mutex>
#include <thread>

REXCVAR_DEFINE_INT32(fh2_telemetry_port, 0, "FH2",
                     "Forza Data Out telemetry to 127.0.0.1 on this UDP port (for example 5300); 0 = off")
    .range(0, 65535);
REXCVAR_DEFINE_STRING(fh2_telemetry_format, "horizon", "FH2",
                      "Telemetry packet layout: horizon (Forza Horizon 4/5, 324 bytes) or fm7 (311 bytes)")
    .allowed({"horizon", "fm7"});

namespace fh2::telemetry {
namespace {
using Clock = std::chrono::steady_clock;
constexpr auto kFresh = std::chrono::milliseconds(250);
constexpr auto kPeriod = std::chrono::milliseconds(16);

std::mutex g_sample_mutex;  // the game thread only try_locks it
Snapshot g_sample;
Clock::time_point g_sampled{};
bool g_have = false;

std::mutex g_mutex;
std::condition_variable g_cv;
bool g_stop = false;
std::thread g_thread;

#if defined(_WIN32)
void Loop(SOCKET socket_, sockaddr_in target, dbce::forza::Layout layout) {
  const auto start = Clock::now();
  uint8_t packet[dbce::forza::FORZA_HORIZON_324];
  std::unique_lock<std::mutex> lock(g_mutex);
  while (!g_cv.wait_for(lock, kPeriod, [] { return g_stop; })) {
    Snapshot sample;
    bool fresh;
    {
      std::lock_guard<std::mutex> sample_lock(g_sample_mutex);
      sample = g_sample;
      fresh = g_have && Clock::now() - g_sampled < kFresh;
    }
    const auto ms = uint32_t(std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - start).count());
    const int size = Build(layout, sample, fresh, ms, packet, int(sizeof packet));
    sendto(socket_, reinterpret_cast<const char*>(packet), size, 0, reinterpret_cast<const sockaddr*>(&target),
           int(sizeof target));  // nonblocking: a full buffer drops the frame
  }
  closesocket(socket_);
  WSACleanup();
}
#endif

}  // namespace

void Start() {
#if defined(_WIN32)
  const int port = REXCVAR_GET(fh2_telemetry_port);
  if (port <= 0 || g_thread.joinable()) return;
  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
    REXLOG_WARN("[fh2] telemetry: WSAStartup failed");
    return;
  }
  const SOCKET socket_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  u_long nonblocking = 1;
  if (socket_ == INVALID_SOCKET || ioctlsocket(socket_, FIONBIO, &nonblocking) != 0) {
    REXLOG_WARN("[fh2] telemetry: no UDP socket");
    if (socket_ != INVALID_SOCKET) closesocket(socket_);
    WSACleanup();
    return;
  }
  sockaddr_in target{};
  target.sin_family = AF_INET;
  target.sin_port = htons(uint16_t(port));
  target.sin_addr.s_addr = htonl(INADDR_LOOPBACK);  // localhost only, by design
  const bool fm7 = REXCVAR_GET(fh2_telemetry_format) == "fm7";
  {
    std::lock_guard<std::mutex> lock(g_mutex);
    g_stop = false;
  }
  g_thread = std::thread(Loop, socket_, target, fm7 ? dbce::forza::FORZA_FM7_DASH_311 : dbce::forza::FORZA_HORIZON_324);
  REXLOG_INFO("[fh2] telemetry: {} packets to 127.0.0.1:{}", fm7 ? "fm7" : "horizon", port);
#endif
}

void Stop() {
  {
    std::lock_guard<std::mutex> lock(g_mutex);
    g_stop = true;
  }
  g_cv.notify_all();
  if (g_thread.joinable()) g_thread.join();
}

}  // namespace fh2::telemetry

// The controls hand-over (fh2_dbce_overrides.toml). Never blocks the game thread: a sample the sender is copying is
// skipped. Off: nothing is read.
void Fh2TelemetryHandOff(PPCContext& ctx, uint8_t* base) {
  using namespace fh2::telemetry;
  if (REXCVAR_GET(fh2_telemetry_port) <= 0) return;
  Snapshot sample;
  if (!Read(base, ctx.r3.u32, ctx.r4.u32, sample)) return;
  std::unique_lock<std::mutex> lock(g_sample_mutex, std::try_to_lock);
  if (!lock.owns_lock()) return;
  g_sample = sample;
  g_sampled = Clock::now();
  g_have = true;
}
