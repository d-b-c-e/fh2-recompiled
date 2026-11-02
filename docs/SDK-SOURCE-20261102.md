# Reconstructing the qualified FH2 SDK source

The Windows branch pins SDK commit`e223de8d7aff090c0acc7a519582f35631e81b21`.
That commit is retained locally, and is **not claimed available from the
third-party SDK remote**. A recursive clone of this app cannot rely on fetching
it. Incremental patches and private bundles remain useful evidence, but are no
longer the only way to obtain the complete source changes.

`windows/patches/shiftglue-sdk-fh2-e223.patch` is the complete15-file source diff
from public base`59bc11f546a6ea67eefcad974d0c14041b2ab20d` to the qualified SDK
tree. It includes all8 local increments: focus-loss stop, XStudio fallback,
opened-haptic capability, endian flags, string serialization, source-preserving
config writes, save-result feedback and explicitGEAR8 parsing. SDK BSD-3-Clause
copyright/license terms remain applicable; no game data, generated game code,
native binaries or third-party dependencies are included in this patch.

| Identity | Value |
| --- | --- |
| Public base tree |`66caf6a1cd2f2e58ec23975da68a13b6a2bce215` |
| Qualified SDK tree |`ebabad40108102589970cd1eedf7daa17366930c` |
| Cumulative patch SHA-256 |`DA79C4D98ECBA6BE0BE107887878FB7433A19CBA43A9CCAD779BEE39D7A0D76C` |

## Obtain the source in a fresh directory

Start with a nonrecursive app checkout of this branch and installedGit/Pwsh7.
The following first two commands fetch only the public SDK base. They do not
fetch the unpublished qualified commit or initialize its dependencies:

```powershell
git init --bare windows/.local/sdk-public-base.git
git -C windows/.local/sdk-public-base.git fetch --no-tags --depth=1 https://github.com/arcanite24/shiftglue-sdk.git 59bc11f546a6ea67eefcad974d0c14041b2ab20d
pwsh -File windows/tools/Restore-Fh2SdkSource.ps1 -SourceRepository windows/.local/sdk-public-base.git -Destination windows/.local/sdk-e223-source
```

The helper itself works offline from an existing **local** repository containing
that base. It checks the patch hash and base tree before creating a destination,
fetches only the base into a new standalone repository, applies the patch to the
index/worktree, and requires the exact qualified Git tree. All mutations stay
inside that new directory. Existing destinations are refused, including dirty
checkouts; no reset/clean, SDK upstream push or source-repository change occurs.
A failure retains its partial fresh destination for inspection.

HEAD deliberately remains at59bc, with the15 changes staged. Matching the tree
does not recreate the original commit metadata or make the SDK gitlink fetchable.
It also does not make the tree pristine relative to HEAD. Do not discard those
staged changes or mistake the base HEAD for the resulting source identity.

Dependency initialization and building are separate explicit steps, when a CPU
slot/toolchain/game-file environment is available:

```powershell
git -C windows/.local/sdk-e223-source submodule update --init --recursive
pwsh -File windows/build.ps1 -SdkRoot windows/.local/sdk-e223-source -Jobs 2
```

`-SdkRoot` overridesREXSDK_DIR in both initial configure and post-codegen
reconfigure. Omitting it retains the existing preset/submodule path. Source
validation happens before game extraction or downloads. The helper does not
initialize dependencies or execute this build. SDK version strings may reflect
the public base/staged state; no byte-identical binary reproduction is claimed.
The existing qualified native pair and payload are preserved separately in
[combined evidence](COMBINED-OFFLINE-20261102.md).

## Evidence

The base was fetched directly from the public URL above into a new bare
repository. The test then reconstructs from only that public-base source;
the resulting repository lacks the privatee223 commit object but matches its
complete tree, including all unchanged files and dependency gitlinks.

```powershell
pwsh -File windows/tools/Test-Fh2SdkSource.ps1 -SourceRepository windows/.local/sdk-public-base.git -OutputDirectory windows/.local/sdk-source-check
```

Eleven checks pass: exact tree/base HEAD/staged paths/source-only identity,
absence of private commit/dependency initialization, existing-destination
refusal with an unchanged sentinel, and early missing-source/missing-base/
tampered-patch refusal. Fixtures and outputs are retained inside the project.
PowerShell parsing and invalidSdkRoot preflight are also checked; no configure
or native rebuild was performed for this source reconstruction.
Private receipt `windows/.local/sdk-reconstruction/run02/result.json` SHA-256
`7C38ADDE43CE48CDFEC1CD7D0DE1A32503C7728459BB1BDC0F8ED1DE3A0D72AA`.
The fetched base repository, both successful fixture trees and refusal copies
remain under that project evidence root; no prior SDK checkout was changed.

No game, window, GPU/input/physical device initialization, installation,
owner-state change or rig lease occurred. This does not relax the held physical
output route or establish runtime UI, gameplay, devices or owner acceptance.
