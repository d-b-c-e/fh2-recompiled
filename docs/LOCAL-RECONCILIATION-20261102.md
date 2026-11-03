# Local FH2 source reconciliation

Kole497316/497360/497386 authorizes local-main integration only. **No push to
origin/public remote.** Source promotion is not a new build, package, install or
game/physical acceptance. No lease or owned process is held.

## Branch disposition

- Original local main7148a42 carried the reviewed helper but still pinned SDK
  `1e8968f712824b97d4f4330c5a22389c4c8be1b5` (not wheel-capable499).
- Merge **074c752** integrates `vuro/fh2-instance-admission-20261102` tip2c64521,
  including its upstream-sync history and SDKgitlinke223de8d. Four helper/README
  conflicts were resolved with vuro's reviewed0ffe successor and its nine
  calibration options. Main's AGENTS/local guidance is retained. Production
  Windows source/build/patches/gitlink remain byte-identical to the vuro lane.
- **ef16839** ports love1c2c3d1/3cf7673's `docs/wheel-layouts.md` and
  `windows/tools/fh2_option_transforms_check.py`. Its full merge would also import
  obsolete device-path factory and SDK auto-patch code, conflicting with vuro's
  newer shutdown/helper/reconstruction path. That uncommitted merge was aborted.
  **love/fh2-option-flags-20261023 is intentionally not fully merged**; keep its
  ref. Its old native/SDK mutation route is not reintroduced. The historical
  note explicitly identifies its unported layout-dump tool.

The existing complete SDK reconstruction patch remains the supported local
source route; see SDK-SOURCE-20261102.md. No SDK source checkout, dependency,
native build directory or vuro restart worktree was modified. Today-dated source,
build and generated-code worktrees under game-modding/.worktrees remain read-only.

## Focused validation

Evidence root: `E:/Source/_work/soba-fh2-reconcile/windows/.local/soba-reconcile`.
The ordinary helper used inert private files only, with automatic exact-path
cleanup. No original owner config/save/shader cache or install was written.

| Check | Result / log |
| --- | --- |
| Test-Fh2Wheel.ps1 |69 inert TOML preservation/refusal/calibration checks PASS; helper.log |
| Test-DiscRevision.ps1 |8 pinned layout checks PASS; disc.log |
| Love option transforms |WheelOptions names/three action swaps and gated Main/Shifting PASS; options.log |
| Retained extent checker before follow-up |378 static checks PASS; extent-baseline.log |
| Typed population follow-up |387 static checks PASS,85,237 functions/171 hashes; resource-population.log |

Read-only generated input:
`E:/Source/game-modding/.worktrees/vuro-fh2-s4/windows/generated/default`.
The existing Test-DiscRevision tool expanded the retained `.wt-sync` default.xex
to private ignored `image.bin`; SHA256
`3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244`.
No title image or generated game body is added to Git. Imported historical
whitespace was not broadly rewritten; the new scoped edits pass whitespace checks.

## New offline finding and next action

The [typed receiver follow-up](INSTANCE-RECEIVER-20261102.md) establishes a
source path through `CTrackProceduralGeometryResource` virtual88 ->virtual60
->82DAA178, publishing at resource+128. Its virtual44/68 are return-zero leaves,
so that typed path is not8244CC30's optional virtual68 callback. No guest code
was executed. Actual selected resources/view roles, kind1 extents and culling
replay remain unqualified; **CULLING HOLD**.

Next offline work: trace callers of typed virtual88 and additional mask writers;
do not replay population or culling callbacks. Next runtime remains the existing
frozen734fff4/e223 private smoke, after provider recovery, verified closed output
apps and fresh koleGO/named lease. Preserve the frozen candidate and all restart
evidence. No original vuro GO is reused. The new main merge does not replace that
native candidate or admit a new scene observer. Only kole/owner decides the
public app push; there is no SDK upstream publication in this work.
