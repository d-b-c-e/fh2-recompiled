// fh2 - the H-shifter reverse speed limit (fh2_reverse_guard.h, fh2_dbce_overrides.toml).
#include "fh2_reverse_guard.h"

#include <rex/ppc/context.h>

// Before each H-gate block reads B+6696; r31 is the handler's CCarDynamics (non_volatile_as_local stays off).
void Fh2GateReverseGuard(PPCContext& ctx, uint8_t* base) { fh2::reverse_guard::Apply(base, ctx.r31.u32); }
