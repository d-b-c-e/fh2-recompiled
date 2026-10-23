// Compiled with extracted generated bodies by fh2_multiscreen_guard_check.py --lifetime-only.
// Fake leaf resources/locks and deterministic completion; never a real host or race test.
#include <windows.h>
#include <atomic>
#include <map>
#include <set>
#include <stdexcept>
#include <string>

uint8_t* guest;
uint32_t nextAllocation = 0x100000, peer, config, wrapper, provider, iface, work, node, server;
constexpr uint32_t dispatcher = 0x90000, stack = 0x6F000, output = 0x60000;
constexpr uint32_t dispatcherTable = 0x834218D0, interfaceTable = 0x83421930;
std::map<uint32_t, bool> allocations;
std::map<uint32_t, int> locks;
std::set<uint32_t> handles;
std::string scenario;
int pumps, providerCloses, interfaceRefs, peerDestructs, closeEntries, embeddedCloses;
bool drained, constructingPeer, retain, serverAdmitted;
[[noreturn]] void Fail(const char* why) { throw std::runtime_error(why); }
void Need(bool ok, const char* why) { if (!ok) Fail(why); }
uint32_t Load(uint32_t p) { return FixtureLoad32(guest, p); }
void Store(uint32_t p, uint32_t v) { FixtureStore32(guest, p, v); }
void Map(uint32_t p, size_t size = 4096) {
  Need(VirtualAlloc(guest + p, size, MEM_COMMIT, PAGE_READWRITE) != nullptr, "guest commit");
}
uint32_t Allocate(uint32_t size) {
  Need(size && size <= 4096, "unsupported allocation size");
  uint32_t p = nextAllocation; nextAllocation += 4096; Map(p); allocations[p] = true;
  return p;
}
bool Live(uint32_t p) { return allocations.contains(p) && allocations.at(p); }
void Free(uint32_t p) {
  Need(Live(p), "unknown/double free");
  if (p == peer || p == wrapper || p == provider || p == config || p == iface || p == work)
    Need(drained, "free before provider drain");
  if (p == server) Need(serverAdmitted, "server free without cleanup admission");
  allocations[p] = false;
  DWORD old;
  Need(VirtualProtect(guest + p, 4096, PAGE_NOACCESS, &old) != 0, "protect freed allocation");
}
void Empty(uint32_t p) { Store(p, p); Store(p + 4, p); }
bool IsEmpty(uint32_t p) { return Load(p) == p && Load(p + 4) == p; }
bool Unlocked() { for (auto [p, depth] : locks) if (depth) return false; return true; }
bool ProviderReady() {
  return !(Load(provider + 8) & 1) && IsEmpty(provider + 32) && IsEmpty(provider + 40) && IsEmpty(provider + 48);
}
PPCContext Context(uint32_t r3, uint32_t r4 = 0) {
  PPCContext ctx{}; ctx.r1.u64 = stack; ctx.r3.u64 = r3; ctx.r4.u64 = r4; ctx.lr = 0x12340000;
  return ctx;
}
void Returned(const PPCContext& ctx) { Need(ctx.r1.u32 == stack && ctx.lr == 0x12340000 && Unlocked(), "ABI/lock return"); }

inline uint64_t Load64(uint8_t* b, uint32_t p) { uint64_t v; memcpy(&v, b + p, 8); return __builtin_bswap64(v); }
inline void Store64(uint8_t* b, uint32_t p, uint64_t v) { v = __builtin_bswap64(v); memcpy(b + p, &v, 8); }
#define REX_STACK_LOAD_U32(a) REX_LOAD_U32(a)
#define REX_STACK_STORE_U32(a,v) REX_STORE_U32(a,v)
#define REX_STACK_LOAD_U64(a) Load64(base, uint32_t(a))
#define REX_STACK_STORE_U64(a,v) Store64(base, uint32_t(a), uint64_t(v))
#define REX_STORE_U64(a,v) REX_STACK_STORE_U64(a,v)
#define REX_STORE_U8(a,v) (base[uint32_t(a)] = uint8_t(v))
#define REX_STORE_U16(a,v) do { uint16_t value = __builtin_bswap16(uint16_t(v)); memcpy(base + uint32_t(a), &value, 2); } while (0)
#define REX_STACK_STORE_U8(a,v) REX_STORE_U8(a,v)
#define REX_RAW_ADDR(a) (base + uint32_t(a))
// Single-thread fixture: actual generated compare_exchange executes; reservation scheduling is not modeled.
#define REX_CHECK_GLOBAL_LOCK() 0
#define REX_ENTER_GLOBAL_LOCK_RESERVATION() ((void)0)
#define REX_LEAVE_GLOBAL_LOCK() ((void)0)
#define REX_TAIL_CALL(fn) do { fn(ctx, base); return; } while (0)
void Dispatch(PPCContext&, uint8_t*, uint32_t);
#undef REX_CALL_INDIRECT_FUNC
#define REX_CALL_INDIRECT_FUNC(a) Dispatch(ctx, base, uint32_t(a))

REX_EXTERN(__imp__RtlInitializeCriticalSection) { Need(!locks.contains(ctx.r3.u32), "lock initialized twice"); locks[ctx.r3.u32] = 0; }
REX_EXTERN(__imp__RtlEnterCriticalSection) {
  uint32_t p = ctx.r3.u32;
  Need(locks.contains(p), "unconstructed lock");
  if (peer && p == peer + 544) ++closeEntries;
  if (peer && p == peer + 656) { Need(!retain, "destroy retained peer"); ++peerDestructs; }
  ++locks[p];
}
REX_EXTERN(__imp__RtlLeaveCriticalSection) { Need(locks[ctx.r3.u32] > 0, "unbalanced leave"); --locks[ctx.r3.u32]; }
REX_EXTERN(sub_83218210) { __imp__RtlInitializeCriticalSection(ctx, base); ctx.r3.u64 = 1; }
REX_EXTERN(sub_823F8700) { ctx.r3.u64 = 0x1234; }
REX_EXTERN(sub_824803A8) {
  Need(ctx.r3.u32 == 0x1234 && ctx.r4.u32 == 0, "heap allocation contract");
  uint32_t size = ctx.r5.u32; ctx.r3.u64 = Allocate(size);
  if (constructingPeer && size == 1508) peer = ctx.r3.u32;
}
REX_EXTERN(sub_832188E0) {
  uint32_t size = ctx.r4.u32; ctx.r3.u64 = Allocate(size);
  if (size == 88) config = ctx.r3.u32;
}
REX_EXTERN(sub_823F8718) { Need(ctx.r3.u32 == 0x1234 && ctx.r4.u32 == 0, "heap free contract"); Free(ctx.r5.u32); }
REX_EXTERN(sub_82C023A0) { Need(Live(ctx.r3.u32) && ctx.r5.u32 <= 4096, "memset allocation"); memset(base + ctx.r3.u32, ctx.r4.u8, ctx.r5.u32); }
REX_EXTERN(sub_82BF0AB0) { ctx.r3.u64 = 0xCAFE0000 + uint32_t(handles.size()) * 4; handles.insert(ctx.r3.u32); }
REX_EXTERN(sub_82BF0B50) { Need(handles.erase(ctx.r3.u32) == 1, "unknown/double handle close"); ctx.r3.u64 = 1; }
REX_EXTERN(sub_82451780) { ctx.r3.u64 = 0x42; }
// Embedded transport and host provider are leaf models. Unknown helper paths fail, never silently succeed.
REX_EXTERN(sub_831FF910) { Need(ctx.r3.u32 == peer + 292 && ctx.r4.u32 == peer, "embedded construction"); Store(peer + 292, 0xFACE0001); ctx.r3.u64 = 0; }
REX_EXTERN(sub_83204138) { Need(ctx.r3.u32 == peer + 292 && Load(peer + 292) == 0xFACE0001 && drained, "embedded cleanup"); ++embeddedCloses; }
REX_EXTERN(sub_8322BBF8) {
  iface = Allocate(8); Store(iface, interfaceTable); interfaceRefs = 1;
  Store(ctx.r3.u32, iface); ctx.r3.u64 = 0;
}
REX_EXTERN(sub_83217A20) { Need(ctx.r4.u32 == node && Load(node + 4) == 0, "pending node release"); Free(node); }

void Dispatch(PPCContext& ctx, uint8_t* base, uint32_t target) {
  if (target == 0x8321F440) {
    Need(ctx.r3.u32 == dispatcher && locks[provider + 56] == 0 && providerCloses == 0, "pump receiver/lock/order");
    Need((Load(provider + 8) & 0x4000) && IsEmpty(provider + 32), "cancel before pump");
    Need(ctx.r4.u32 >= 10 && ctx.r5.u32 == 0, "drain pump arguments");
    ++pumps;
    if (pumps > 6) Fail("provider still pending");
    if (Load(provider + 8) & 1) {
      if (scenario != "stall-busy") Store(provider + 8, Load(provider + 8) & ~1u);
    } else if (!IsEmpty(provider + 40)) {
      if (scenario != "stall-list40") Empty(provider + 40);
    } else if (!IsEmpty(provider + 48)) {
      if (scenario != "stall-list48") Empty(provider + 48);
    } else Fail("unnecessary pump");
    ctx.r3.u64 = 0; return;
  }
  if (target == 0x82E7F698) { sub_82E7F698(ctx, base); return; }
  Need(ctx.r3.u32 == iface, "unexpected indirect receiver");
  if (target == 0x8322DA28) {
    provider = Load(ctx.r4.u32); Need(Live(provider) && Load(ctx.r4.u32 + 4) == 1, "kind-2 provider construction");
    work = Allocate(1024); Store(work + 4, 2); locks[work + 524] = 0;
    ++interfaceRefs; // The real successful provider Initialise retains its interface.
  } else if (target == 0x83229D60) {
    Store(ctx.r4.u32 + 8, 48); Store(ctx.r4.u32 + 12, 1);
    Store(ctx.r4.u32 + 16, work); Store(ctx.r4.u32 + 36, 2);
  } else if (target == 0x83229D38) ++interfaceRefs;
  else if (target == 0x8322DA90) {
    Need(ProviderReady() && Unlocked(), "provider close before drain");
    drained = true; ++providerCloses; --interfaceRefs; Free(work);
  } else if (target == 0x8322BC70) {
    Need(interfaceRefs > 0, "interface double release");
    if (--interfaceRefs == 0) Free(iface);
  } else Fail("unmodeled indirect target");
  ctx.r3.u64 = 0;
}

// Fake empty leaf containers; actual outer server constructors/register/remove/destructors execute.
void Tree(uint32_t root) { uint32_t p = Allocate(32); Store(root + 4, p); Empty(p); Store(p + 8, p); Store(root + 8, 0); }
REX_EXTERN(sub_82F17050) { Tree(ctx.r3.u32); }
REX_EXTERN(sub_82DA5868) { Tree(ctx.r3.u32); }
REX_EXTERN(sub_82E7DC38) { Tree(ctx.r3.u32); }
REX_EXTERN(sub_82E7CEA8) { uint32_t p = Allocate(16); Empty(p); Store(ctx.r3.u32 + 12, p); Store(ctx.r3.u32 + 16, 0); }
REX_EXTERN(sub_82401A60) { ctx.r3.u64 = 1000; }
REX_EXTERN(sub_82C009E0) { Need(ctx.r5.u32 <= 64, "copy bound"); memcpy(base + ctx.r3.u32, base + ctx.r4.u32, ctx.r5.u32); }
REX_EXTERN(sub_82E7A110) {
  Need(Load(ctx.r3.u32) == 0 && ctx.r4.u32 == 0, "only fresh listener array growth");
  Store(ctx.r3.u32, Allocate(64)); Store(ctx.r3.u32 + 4, 16); ctx.r3.u64 = 1;
}
REX_EXTERN(sub_82E79360) { Need(ctx.r5.u32 == 0, "nonempty listener move unsupported"); }
REX_EXTERN(sub_8251A0B8) { Need(IsEmpty(Load(ctx.r4.u32 + 4)) && Load(ctx.r4.u32 + 8) == 0, "nonempty tree destruction"); }
REX_EXTERN(sub_82519DC0) { Need(IsEmpty(Load(ctx.r4.u32 + 4)) && Load(ctx.r4.u32 + 8) == 0, "nonempty tree destruction"); }
REX_EXTERN(sub_82DE08A0) { Need(IsEmpty(Load(ctx.r3.u32)) && Load(ctx.r3.u32 + 4) == 0, "nonempty base list destruction"); }
REX_EXTERN(sub_8240D2C8) { Free(ctx.r3.u32); }

void ValidatePeer() {
  Need(Live(peer) && Live(config) && Live(wrapper) && Live(provider) && Live(iface) && Live(work), "incomplete factory state");
  Need(Load(peer + 152) == wrapper && Load(wrapper + 12) == peer && Load(wrapper + 8) == provider &&
       Load(wrapper + 4) == iface && Load(provider + 12) == iface && Load(provider + 16) == config &&
       Load(peer + 44) == config && Load(peer + 164) == dispatcher && interfaceRefs == 3, "incomplete factory state");
  Need(Load(peer) == 0x83421740 && Load(peer + 4) == 1 && Load(peer + 16) == 0 &&
       Load(peer + 20) == 0 && Load(peer + 24) == 0 && Load(peer + 292) == 0xFACE0001, "factory flags/callbacks");
  for (int offset : {104,112,120,128,136,144,156}) Need(IsEmpty(peer + offset), "factory list sentinel");
  Need(ProviderReady() && handles.contains(Load(peer + 32)) && Unlocked(), "factory resource state");
}
void BuildPeer() {
  constructingPeer = true;
  auto ctx = Context(2, output); sub_831FBD58(ctx, guest); Returned(ctx);
  Need(ctx.r3.u32 == 0 && Load(output) == peer, "factory did not publish success");
  constructingPeer = false; wrapper = Load(peer + 152); ValidatePeer();
}
void Pending() {
  node = Allocate(64); Store(node + 4, 1); Store(node + 28, work);
  Store(node + 44, provider + 32); Store(node + 48, provider + 32);
  Store(provider + 32, node + 44); Store(provider + 36, node + 44);
  Store(provider + 8, Load(provider + 8) | 1);
  // The fake dispatcher owns these two outstanding completion markers.
  Store(provider + 40, work + 128); Store(provider + 44, work + 128);
  Store(provider + 48, work + 144); Store(provider + 52, work + 144);
}
void PeerCase() {
  BuildPeer();
  if (scenario == "incomplete") { Store(peer + 152, 0); ValidatePeer(); Fail("incomplete state admitted"); }
  auto ctx = Context(peer); sub_832138F8(ctx, guest); Returned(ctx);
  Need(ctx.r3.u32 == 0x80158640 && closeEntries == 1 && peerDestructs == 0 && providerCloses == 0,
       "uninitialized rejection is not teardown");
  closeEntries = 0;
  if (scenario == "retained") { Store(peer + 4, 2); retain = true; }
  if (scenario == "drain" || scenario.starts_with("stall-")) Pending();
  ctx = Context(peer); sub_831FA3A0(ctx, guest); Returned(ctx);
  if (retain) Need(ctx.r3.u32 == 1 && Load(peer + 4) == 1 && closeEntries == 0 && peerDestructs == 0 &&
                   providerCloses == 0 && Live(wrapper), "retained ref must not close/free");
  else {
    Need(ctx.r3.u32 == 0 && closeEntries == 1 && peerDestructs == 1 && providerCloses == 1 &&
         embeddedCloses == 1 && interfaceRefs == 0 && handles.empty(), "last-reference teardown count");
    for (auto [p, live] : allocations) Need(!live, "owned allocation leaked");
    Need(pumps == (scenario == "drain" ? 3 : 0), "drain phase count");
  }
}
void ServerCase() {
  server = Allocate(2284);
  auto ctx = Context(server); sub_82E7F528(ctx, guest); Returned(ctx);
  ctx = Context(server); sub_82E7EBA8(ctx, guest); Returned(ctx);
  Need(Load(server + 2100) == 0 && Load(server + 2096) == 0 && Load(server + 2160) == 0 &&
       Load(server + 20) == 0 && IsEmpty(server + 2240) && IsEmpty(server + 2248), "fresh server construction");
  ctx = Context(server + 132, 0x90080); sub_82E78DD8(ctx, guest); Returned(ctx);
  ctx = Context(server, 0x90084); sub_82E849A8(ctx, guest); Returned(ctx);
  Need(Load(server + 2276) == 0x90080 && Load(server + 20) == 1 && Load(Load(server + 8)) == 0x90084,
       "notification/listener registration");
  if (scenario == "server-connection") Store(server + 2160, 1);
  if (scenario == "server-queue") Store(server + 2240, 0x900C0);
  // Fixture admission, not a proposed production cleanup policy.
  Need(Load(server + 2160) == 0, "nonempty server connections");
  Need(IsEmpty(server + 2240) && IsEmpty(server + 2248), "pending server queue");
  ctx = Context(server + 132); sub_82E78DE0(ctx, guest); Returned(ctx);
  ctx = Context(server, 0x90084); sub_82E83488(ctx, guest); Returned(ctx);
  Need(Load(server + 2276) == 0, "notification still registered");
  Need(Load(server + 20) == 0, "listener still registered");
  serverAdmitted = true;
  ctx = Context(server, 1); sub_82E7FB38(ctx, guest); Returned(ctx);
  for (auto [p, live] : allocations) Need(!live, "server allocation leaked");
}
int main(int argc, char** argv) {
  if (argc != 2) return 2;
  scenario = argv[1];
  guest = static_cast<uint8_t*>(VirtualAlloc(nullptr, 0x100000000ull, MEM_RESERVE, PAGE_NOACCESS));
  if (!guest) return 2;
  int result = 0;
  try {
    for (uint32_t p : {0x60000u,0x82000000u,0x82240000u,0x83420000u,0x83650000u,0x833F0000u}) Map(p, 65536);
    Map(dispatcher); Store(dispatcher, dispatcherTable); Store(0x83658AE8, dispatcher);
    Store(dispatcherTable + 52, 0x8321F440);
    for (auto [offset, target] : std::map<int,uint32_t>{{4,0x83229D38},{8,0x8322BC70},{12,0x8322DA28},{16,0x8322DA90},{64,0x83229D60}})
      Store(interfaceTable + offset, target);
    Store(0x82244590 + 8, 0x82E7F698);
    if (scenario.starts_with("server")) ServerCase(); else PeerCase();
    Need(!scenario.starts_with("stall-") && scenario != "incomplete" && scenario != "server-connection" &&
         scenario != "server-queue", "negative case unexpectedly returned");
    printf("PASS %s pumps=%d providerClose=%d peerDestroy=%d\n", scenario.c_str(), pumps, providerCloses, peerDestructs);
  } catch (const std::exception& e) {
    bool blocked = (scenario.starts_with("stall-") && std::string(e.what()) == "provider still pending" &&
                    providerCloses == 0 && Live(peer) && Live(provider) && Live(config) && Live(wrapper)) ||
                   (scenario == "incomplete" && std::string(e.what()) == "incomplete factory state" && peerDestructs == 0) ||
                   (scenario == "server-connection" && std::string(e.what()) == "nonempty server connections" && Live(server)) ||
                   (scenario == "server-queue" && std::string(e.what()) == "pending server queue" && Live(server));
    printf("%s %s: %s pumps=%d providerClose=%d\n", blocked ? "PASS" : "FAIL", scenario.c_str(), e.what(), pumps, providerCloses);
    result = blocked ? 0 : 1;
  }
  VirtualFree(guest, 0, MEM_RELEASE);
  return result;
}
