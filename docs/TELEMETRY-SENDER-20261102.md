# FH2 Data Out sender: live configuration and offline qualification

The production sender now applies port and packet-format changes at its next
tick (nominally16ms). Port0 becomes silent, an initially disabled sender can be
enabled, and changing the port clears the old sample before the new destination
receives packets. Disabling/re-enabling or stopping/restarting also discards old
car data and engine constants. Format changes use the same current sample.

Previously Start captured the port/format once. An initially disabled sender
could not be enabled; an active sender kept transmitting to the original port,
even after setting0 stopped the sampler. The new fixture reproduced the
initial-off failure before the fix. Existing finite-value, packet-layout,
gear-mapping and250ms freshness rules are unchanged.

Defaults remain top-level `fh2_telemetry_port = 0` and
`fh2_telemetry_format = "horizon"`. Nonzero ports send only to127.0.0.1;
`horizon` is324 bytes and `fm7` is311. There is now one idle worker and an
unbound nonblocking UDP socket even when disabled, so later enable can work.
No datagrams are sent and the game hook reads no guest memory while the
disabled state is applied. A queued datagram cannot be recalled; this asynchronous
configuration control is not a physical-output emergency stop.

The sender copies configuration through the SDK's registry-locked Query API.
The game hook checks an atomic sampling flag and retains its try-lock publication
path; it never waits on registry access or network operations. Stop joins the
owned sender before clearing its sample. Call Start/Stop from the existing
serialized application lifecycle; concurrent lifecycle callers are unsupported.

## Checks and limits

Run from the Windows worktree, using a fresh output directory each time:

```powershell
python -I windows/tools/fh2_telemetry_sender_check.py --cxx g++ --out windows/.local/telemetry-sender/example-adapters
```

This compiles the **actual production fh2_telemetry.cpp**, using inert adapters
for SDK cvars/logging/PPCContext. Real Winsock sends to two fixture-owned,
OS-assigned loopback ports. It never sends to the configured owner/SimHub port,
executes guest instructions or initializes input/graphics/physical devices.

For actual SDK API/DLL integration, use an x64 Visual Studio developer shell,
clang++ and an already-built compatible SDK:

```powershell
python -I windows/tools/fh2_telemetry_sender_check.py --cxx clang++ --sdk <built-sdk-root> --out windows/.local/telemetry-sender/example-sdk
```

The runner links rexruntime/fmt/spdlog import/static libraries and copies only
rexruntime.dll into its fixture output. No cvar.cpp replacement is linked in
this mode. Both modes preserve compile/run logs and a result.json with source,
fixture, executable and (when applicable) runtime hashes. Timeouts bound the
child process; the fixture joins its sender and closes owned sockets on success
and assertion failure. No full native app/SDK build or installation is performed.

November2 results:

- Both modes:14 production sender checks PASS. Covers initial-off enable,
  fresh synthetic handoff to wire speed/gear, live311/324 format switch,
  destination retarget/old-port silence,250ms stale-to-neutral transition,
  port0 silence, disabled no-read, re-enable with empty sample, idempotent
  Start/Stop and fresh restart. Synthetic guest memory is not game execution.
- Real SDK mode uses qualified bddeb167/rexruntime SHA256
  `04E80039FBF991A22F5DCA0585DAA5727259FD754F4DA98FF3C76ED0DB58098C`.
- Existing generated-hook placement/continuation checks and65 finite encoder
  checks PASS; the guest override table and generated code are unchanged.
- Private evidence `windows/.local/telemetry-sender/adapter-final/` and
  `sdk-final/` contains logs/receipts. The native01 include-path compile failure,
  native02 pass and original before-fix executable are retained separately.

The app7ce460f/SDKbddeb native binaries and staged payload are unchanged; they do
**not** contain this later sender fix. This is a compiled component and actual
SDK/DLL loopback check, not a new FH2 executable build. Actual game handoff scope,
pause/menu IsRaceOn behavior, SimHub/UI receipt, performance and physical outputs
remain runtime/owner gates from the earlier telemetry plan. Motion/haptic safety
remains held. No owner config, save, install, device or display was changed.
