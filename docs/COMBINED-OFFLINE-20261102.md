# FH2 combined offline successor

Source candidate for a separate native build, Guna GO492432, jobs2, maximum90min.
SDK source pin **e223de8d7aff090c0acc7a519582f35631e81b21** combines qualified
bddeb167 with config-preservation fb1822c9, save-result e35aedef and GEAR8.
App source includes the production telemetry-sender e24b9b2 follow-up. The
offline managed triple planner is retained; no native triple renderer is added.

The SDK pin is retained locally through verified source bundles and the three
published SDK patches. It is not claimed available from the third-party remote.
Reconstruct on bddeb167 by applying cvar-preserve, save-result, then gear8;
alternatively use the locally retained bundle chain. No SDK upstream push.

Previous app7ce460f/SDKbddeb167 worktrees, logs, native binaries and private
payloads remain separate and unchanged. This new source pin is **not yet a
qualified native build or owner installation**. Fresh build receipts and output
hashes will determine its outcome; component fixtures do not imply a full build.

Build interval: one named operator vuro, fresh short checkout, existing qualified
stage/owned-process/lease helpers, jobs2 and BelowNormal priority. Pin all XEX,
toolchain, SDK and source inputs. Run native codegen/link plus existing generated
gear/reverse/telemetry checks and focused real-runtime config/sender checks.
No game launch, GPU/input/physical-device initialization, display mutation or
owner install/config access. Physical motion/haptic and runtime acceptance stay
held. Release the lease only after owned children are quiescent and verified.
