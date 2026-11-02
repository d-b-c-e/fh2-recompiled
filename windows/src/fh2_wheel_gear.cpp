// fh2 - the H-shifter gate read's refusal (fh2_dbce_overrides.toml, 0x82D84260).
#include <rex/ppc/context.h>

// A refused gate read is no gate request (10), never REVERSE (-1). Replaces `li r3,-1`.
bool Fh2GearReadRefused(PPCRegister& r3) {
  r3.s64 = 10;
  return true;
}
