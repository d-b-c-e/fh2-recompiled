"""FH2 force/motion mute and private smoke route for the installed 734fff4/SDK e223 build.

No rebuild. Two layers, launch-time only:

  B (physical isolation). The fh2 process gets a sanitized environment: every inherited SDL_* variable is
     removed, then the DirectInput, RawInput, WGI, GameInput, XInput and generic HIDAPI backends and every
     HIDAPI driver-enable hint are set to 0, so SDL enumerates and opens no physical controller. Needed because
     opening a force-capable DirectInput device alone sends DISFFC_RESET and DIPROP_AUTOCENTER on, and an
     inherited per-driver hint (for example SDL_JOYSTICK_HIDAPI_PS5=1) overrides the generic HIDAPI=0.
  A (defence in depth). SDK cvars on the command line, repeated in the private fh2.toml: wheel path never
     opened, wheel forces off/zero, guest rumble scaled to 0, DualSense triggers off, Data Out port 0, controller
     chords to the settings/debug menus empty. A alone is not sufficient.

The static check pins the reviewed mechanisms in the exact source; it is not an exhaustive output proof and
not a physical measurement. Nothing on the MOZA, Pit House or SimHub is changed; "restore" is a full-SHA-256
before/after proof of the owner install and Documents/fh2 plus an exact PID+birth+image closure census.

  python -I fh2_force_mute.py check --tree <734fff4 checkout with SDK e223>
  python -I fh2_force_mute.py selftest
  python -I fh2_force_mute.py census
  python -I fh2_force_mute.py prepare --root <private> [--owner <install>]
  python -I fh2_force_mute.py verify --root <private>
  python -I fh2_force_mute.py run --root <private> --go <event> --plan-sha256 H --baseline-sha256 H [--seconds 600]

run sends no OS input (scripted pad and in-process captures only). It requires the named Rig-Lease
(Rig-Lease.ps1 -Enter -Name vibe, purpose containing GO<event>) and never releases it: release only when
result.json says custody_clear, otherwise keep the lease and report. Owner activity is recorded, not a gate
(kole538387); the owner or kole stops a run by creating <root>/STOP.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_HEAD = "734fff4eefc9d7e4db61a70a6948ad5a808a1b12"
SDK_HEAD = "e223de8d7aff090c0acc7a519582f35631e81b21"
SDL_HEAD = "8bf3b7215ad9fc3deb583c6a3a37c6c67f2e24e4"
OWNER = Path("E:/Source/tools/launchbox/Launchbox-Racing/Games/Windows/Forza Horizon 2 (Native)")
BIN = {  # installed receipt dbce.fh2-owner-install@1, napo fh2-041811100
    "fh2.exe": "A4E3BC4FD100DB81EDEC83E6B185F7CBB62EF4A74BC0FFD0CA1CD5AA8ED33EC0",
    "rexruntime.dll": "7708F5FD2F29D2200E67651042836607ABDB0975ED274F69C71A1E2D35865C80",
    "rexgpu-fh1.dll": "33F73DABB51AFF2572DA90E2DE68F0CCAEC5879ACE3BCA6B0B3D1358A6005237",
    "fh2_XMediaFacade_default.dll": "8B798C9E656AB76DADB5C8D21BCBA635096C15FD20486ECE3FB31F5110BA7102",
    "fh2_SpeechFacade_default.dll": "DCEA60C2CF7958CE1BB4E05758CB1BA0229D2669376F04C9276B6CCD47F484BA",
}

S = "windows/thirdparty/shiftglue-sdk/"
L = S + "thirdparty/sdl3/src/"
PINS = {
    S + "src/input/sdl/sdl_input_driver.cpp": "4b3fad3fa430ed8002b50fccd148dfec803d4f24c7ead72d95132698e5c1d4e9",
    S + "src/input/input_system.cpp": "812ee056c8231aefff74b8c1e5867c3939a106b849dde29c30e87f4b5e522924",
    S + "src/input/xinput/xinput_input_driver.cpp": "b582b4a67fa6f867ba6372e6bfe8fcf6927d1fe5f85ea65a891f7672eb37308b",
    S + "src/input/dualsense.cpp": "52ee947ed1177811d901aac298d6630f619338c59480e996448b826876e0682f",
    S + "src/input/ffb_trace.cpp": "16417d8cd4faf50a0ea1c39b617bcb42aeb172adbdc8b19118faca9895d094db",
    S + "src/input/sdl/wheel.cpp": "92621a2423219015ea598728e060ead5017f13fe2d7297089c3003e85681dada",
    S + "src/input/mnk/mnk_input_driver.cpp": "649230d5cb9607f8114e3bc26b936940d5ba1d0d57d9a0cd7d282a729ce40d2b",
    S + "src/system/runtime.cpp": "ca30420082afaca45c3e5e61c20b48d0241bbc90ecc8fee7458e2ddd8545b169",
    S + "src/input/sdl/joystick_mapping.cpp": "ed68171fc6c1f03c131855ff354b19e0f3e5e8ed65a5c554252fdbe3700866e1",
    S + "src/core/cvar.cpp": "6dc4041f8509cb2e9c4c9944dd25bc1e518b90045b9279b068ef6e19f16b3ee7",
    S + "include/rex/cvar.h": "a017f1db7b6fa40fc824e0fb8ea13dec1db0ceecf754e203671d05ce2628e2ae",
    S + "src/ui/rex_app.cpp": "4bf4d6d5178b72db2262a5bdb86ca9d722e026527f0cc1c7fee0721a0852e262",
    S + "src/ui/window.cpp": "82851a86382a5ceccb1d8d669703c5628ae6f91084070c2f7927dee72ab12ee3",
    S + "src/ui/overlay/settings_overlay.cpp": "d344eeca3730f55700377e0dadcf414d3f6aad0d62f1bf3b56959ec69eef986b",
    S + "src/ui/overlay/console_overlay.cpp": "0bc3c4de3ac6320b206816b36816a1fa0112ad72ba8155c4f6edb10ada3f9f35",
    S + "src/kernel/xam/xam_input.cpp": "75ed814d72a5ac1aa7be7c22fc199243efda8331e99cb0bd0e7ba43f1dae03ff",
    L + "SDL_hints.c": "40c59187c5d66689fc536a1ac8f9c7c15df7f421c6b15c236ddac7b334811137",
    L + "joystick/windows/SDL_dinputjoystick.c": "4cb4cb7f17e39d227982d250e5de54bf7f35657dfa5f0eb473547f240c002329",
    L + "joystick/windows/SDL_rawinputjoystick.c": "2a542744d6f8f049d2dbeb07ef6b9845efc5596675e240bc218a88d2ae98a422",
    L + "joystick/windows/SDL_windows_gaming_input.c": "b4d008dcc4e21c47b9b1eda979987c8264cc2a35a1e96ef55c44fa2313b93da3",
    L + "joystick/windows/SDL_xinputjoystick.c": "1520ddfcae5dc84b3f33c3d52c107ec966462d1cce40d6ca1c3dd0df820bbdec",
    L + "joystick/gdk/SDL_gameinputjoystick.cpp": "39cea369f9a948d46bb13c2540bcf5e196b5fd0fa30b5e54d9563015007a9464",
    L + "haptic/windows/SDL_dinputhaptic.c": "82b6bb085f0bd3642eccf9a70092ba438f3d6041f351532efdb43cf7d382ccad",
    L + "haptic/windows/SDL_windowshaptic.c": "06fafd674c09a7e9e01781b8079374f539dfca7320d738205a2fd10644147b42",
    L + "joystick/hidapi/SDL_hidapijoystick.c": "4d8fd0b0459c7b5dc134916b8476dc850641e74db494e798023fbdd3dc701ad5",
    L + "joystick/SDL_gamepad_db.h": "827c90c29e932b4e3da100751ac2b0699dddca2e908a4074c9225cf0f2059daf",
    "windows/src/main.cpp": "793961a7ec7fa58bea5330bb8da08541a1efaa9a848c0f244080a4ec282a0ee6",
    "windows/src/fh2_telemetry.cpp": "be09e259928e30a525acd8b60025b6969c4a7a2a39184e1bff6c135dd7304b2f",
    "windows/src/fh2_toque.cpp": "fc34ade947bf9cfd649ad2fcb94efef65104dc759bb8ab80d3edd41f138e577f",
    "windows/CMakeLists.txt": "9dceca446ba4e8e3ebb91279052ddea82d3cc7729101e63cfb3be96ac47a7ace",
    "app/src/fh2_teste_entrada.cpp": "23c339f9ee4d6481bfbd7e2d5e055d8dbbb674477a060b58bee48de16a319ba8",
    "app/src/fh2_captura.cpp": "78ec4e514b4b192edf8e9d985a05fccfa381acd0271d731553618c0006da076e",
    "app/src/fh2_correcoes.cpp": "90e91700a8c45237ffbd7a45eb5956c0636b1e5f4355c3c4892c59dc615029f4",
}

# Layer A. value None = boolean false (--no-name); True = boolean true (--name).
MUTE = {
    "input_backend": "sdl",  # the SDK XInput driver is only created for "xinput"
    "wheel_enabled": None,
    "wheel_ffb_effects": None,
    "wheel_ffb_mode": "off",
    "wheel_ffb_strength": "0",
    "wheel_ffb_centering": "0",
    "wheel_ffb_spring": "0",
    "wheel_ffb_damper": "0",
    "wheel_ffb_friction": "0",
    "wheel_ffb_inertia": "0",
    "wheel_ffb_rumble_engine": "0",
    "wheel_ffb_rumble_road": "0",
    "wheel_ffb_device": "",
    "pad_rumble_strength": "0",
    "pad_ds_triggers": "off",
    "pad_ds_gear_click": None,
    "fh2_telemetry_port": "0",
    "pad_chord_game_menu": "",
    "pad_chord_debug_overlay": "",
    "mnk_mode": None,
}
# Layer B: every SDL3 Windows joystick backend, and every HIDAPI driver-enable hint (the static check derives
# the set each *_IsEnabled reads from the exact SDL source and requires it to be covered here).
SDL_BACKENDS = ("SDL_JOYSTICK_DIRECTINPUT", "SDL_JOYSTICK_RAWINPUT", "SDL_JOYSTICK_WGI", "SDL_JOYSTICK_GAMEINPUT",
                "SDL_XINPUT_ENABLED", "SDL_JOYSTICK_HIDAPI")
HIDAPI_DRIVER_HINTS = (
    "SDL_JOYSTICK_HIDAPI_8BITDO", "SDL_JOYSTICK_HIDAPI_FLYDIGI", "SDL_JOYSTICK_HIDAPI_GAMECUBE",
    "SDL_JOYSTICK_HIDAPI_GAMESIR", "SDL_JOYSTICK_HIDAPI_GIP", "SDL_JOYSTICK_HIDAPI_JOY_CONS",
    "SDL_JOYSTICK_HIDAPI_LG4FF", "SDL_JOYSTICK_HIDAPI_LUNA", "SDL_JOYSTICK_HIDAPI_NINTENDO_CLASSIC",
    "SDL_JOYSTICK_HIDAPI_PS3", "SDL_JOYSTICK_HIDAPI_PS3_SIXAXIS_DRIVER", "SDL_JOYSTICK_HIDAPI_PS4",
    "SDL_JOYSTICK_HIDAPI_PS5", "SDL_JOYSTICK_HIDAPI_SHIELD", "SDL_JOYSTICK_HIDAPI_SINPUT",
    "SDL_JOYSTICK_HIDAPI_STADIA", "SDL_JOYSTICK_HIDAPI_STEAM", "SDL_JOYSTICK_HIDAPI_STEAMDECK",
    "SDL_JOYSTICK_HIDAPI_STEAM_HORI", "SDL_JOYSTICK_HIDAPI_SWITCH", "SDL_JOYSTICK_HIDAPI_SWITCH2",
    "SDL_JOYSTICK_HIDAPI_WII", "SDL_JOYSTICK_HIDAPI_XBOX", "SDL_JOYSTICK_HIDAPI_XBOX_360",
    "SDL_JOYSTICK_HIDAPI_XBOX_360_WIRELESS", "SDL_JOYSTICK_HIDAPI_XBOX_ONE", "SDL_JOYSTICK_HIDAPI_ZUIKI",
)
SDL_FENCE = {name: "0" for name in SDL_BACKENDS + HIDAPI_DRIVER_HINTS}
PRIVATE_PARENT = Path("E:/Source/_work")
SCHEMA = "dbce.fh2-force-mute-smoke@2"
LEASE_DIR = Path(os.environ.get("LOCALAPPDATA", "C:/missing")) / "dbce"
REFUSE_PROCESSES = ("pit house", "mozapithouse", "simhub", "fh2.exe")  # FH2-only Pit House rule; SimHub per Nov 2 clearance
# Scripted pad (in-process, synthetic): advance boot prompts only; no stick steering (STD-039).
BUTTONS = "45:a,60:a,75:start,90:a,105:a,120:a,150:a,180:a,210:a,240:start,270:a"

OUTPUT_API = re.compile(
    r"\b(SDL_Rumble\w*|SDL_SendGamepadEffect|SDL_SendJoystickEffect|SDL_\w*Haptic\w*|SDL_SetGamepadLED|"
    r"SDL_SetJoystickLED|SDL_hid_write|SDL_hid_send_feature_report|XInputSetState_?|sendto|WSASendTo)\s*\(")

ANCHORS = [  # (file, regex, expected count); DOTALL multiline anchors on the pinned bytes
    (S + "src/input/sdl/sdl_input_driver.cpp",
     r"bool SDLInputDriver::IsWheelPart\(SDL_JoystickID instance_id\) \{\s+if \(!REXCVAR_GET\(wheel_enabled\)\) \{\s+return false;", 1),
    (S + "src/input/sdl/sdl_input_driver.cpp",
     r"void SDLInputDriver::OnJoystickAddedLocked\(const SDL_Event& event\) \{\s+const SDL_JoystickID which = event\.jdevice\.which;\s+if \(!IsWheelPart\(which\)\) \{\s+return;", 1),
    (S + "src/input/sdl/sdl_input_driver.cpp", r"SDL_OpenJoystick\(", 1),
    (S + "src/input/sdl/sdl_input_driver.cpp", r"SDL_OpenHapticFromJoystick\(", 1),
    (S + "src/input/sdl/sdl_input_driver.cpp", r"SDL_OpenHaptic\(", 0),
    (S + "src/input/sdl/sdl_input_driver.cpp", r"\bwheel_ = std::move\(", 1),
    (S + "src/input/sdl/sdl_input_driver.cpp",
     r"if \(IsWheelPart\(event\.gdevice\.which\)\) \{.{0,300}?return;\s+\}\s+const auto controller = SDL_OpenGamepad\(", 1),
    (S + "src/input/sdl/sdl_input_driver.cpp", r"SDL_OpenGamepad\(", 1),
    (S + "src/input/sdl/sdl_input_driver.cpp", r"SDL_SetHint\w*\(SDL_HINT_JOYSTICK_HIDAPI_PS5_PLAYER_LED", 1),
    (S + "src/input/input_system.cpp",
     r"const int32_t strength = std::clamp\(REXCVAR_GET\(pad_rumble_strength\), 0, 100\);", 1),
    (S + "src/input/input_system.cpp", r"X_RESULT result = driver->SetDeviceVibration\(id, vibration\);", 1),
    (S + "src/input/input_system.cpp",
     r"if \(REXCVAR_GET\(input_backend\) == \"xinput\"\) \{\s+auto xinput_driver = std::make_unique<xinput::XinputInputDriver>", 1),
    (S + "src/input/input_system.cpp", r"make_unique<xinput::XinputInputDriver>", 1),
    ("windows/src/fh2_telemetry.cpp", r"if \(port <= 0 \|\| port > 65535\) continue;", 1),
    (S + "include/rex/cvar.h",
     r"enum class Source \{\s+kDefault,.*?kConfig,.*?kEnvironment,.*?kCommandLine,.*?kRuntime", 1),
    (S + "src/core/cvar.cpp", r"bool Outranks\(Source source, const FlagEntry& entry\) \{\s+return source >= entry\.source;", 1),
    (S + "src/ui/rex_app.cpp", r"exe_dir / \(std::string\(GetName\(\)\) \+ \"\.toml\"\)", 1),
    (S + "src/ui/rex_app.cpp", r"user_dir = rex::filesystem::GetUserFolder\(\) / GetName\(\);", 1),
    (S + "src/ui/rex_app.cpp", r"log_config\.log_dir = rex::path_to_utf8\(exe_dir / \"logs\"\);", 1),
    (L + "SDL_hints.c", r"if \(env && \(priority < SDL_HINT_OVERRIDE\)\) \{", 1),
    (L + "joystick/windows/SDL_dinputjoystick.c", r"if \(!SDL_GetHintBoolean\(SDL_HINT_JOYSTICK_DIRECTINPUT, true\)\) \{", 1),
    (L + "joystick/windows/SDL_dinputjoystick.c", r"DISFFC_RESET", 4),
    (L + "joystick/windows/SDL_dinputjoystick.c", r"dipdw\.dwData = DIPROPAUTOCENTER_ON;", 1),
    (L + "haptic/windows/SDL_dinputhaptic.c", r"if \(!SDL_GetHintBoolean\(SDL_HINT_JOYSTICK_DIRECTINPUT, true\)\) \{", 1),
    (L + "joystick/windows/SDL_rawinputjoystick.c", r"SDL_GetHintBoolean\(SDL_HINT_JOYSTICK_RAWINPUT, false\)", 1),
    (L + "joystick/windows/SDL_windows_gaming_input.c", r"SDL_GetHintBoolean\(SDL_HINT_JOYSTICK_WGI, false\)", 1),
    (L + "joystick/windows/SDL_xinputjoystick.c", r"SDL_GetHintBoolean\(SDL_HINT_XINPUT_ENABLED, true\)", 1),
    (L + "joystick/gdk/SDL_gameinputjoystick.cpp", r"SDL_GetHintBoolean\(SDL_HINT_JOYSTICK_GAMEINPUT, SDL_GAMEINPUT_DEFAULT\)", 1),
    (L + "joystick/hidapi/SDL_hidapijoystick.c", r"SDL_AddHintCallback\(SDL_HINT_JOYSTICK_HIDAPI,", 1),
    (L + "joystick/SDL_gamepad_db.h", r"(?i)346e", 0),  # no built-in MOZA gamepad mapping
    ("windows/CMakeLists.txt", r"fh2_teste_entrada\.cpp", 1),
    ("app/src/fh2_teste_entrada.cpp", r"REXCVAR_DEFINE_STRING\(fh2_teste_botoes,", 1),
    ("app/src/fh2_captura.cpp", r"REXCVAR_DEFINE_INT32\(fh2_captura_cada_s,", 1),
]


class Fail(Exception):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, check=True).stdout.strip()


# ---------------------------------------------------------------------------------------------- static check

def cvar_definitions(texts: dict[str, str]) -> dict[str, dict]:
    defs: dict[str, dict] = {}
    pattern = re.compile(r"REXCVAR_DEFINE_(BOOL|INT32|STRING|DOUBLE)\((\w+),")
    for text in texts.values():
        for m in pattern.finditer(text):
            end = text.find(";", m.end())
            body = text[m.start():end]
            entry = {"type": m.group(1), "range": None, "allowed": None}
            r = re.search(r"\.range\((-?\d+),\s*(-?\d+)\)", body)
            if r:
                entry["range"] = (int(r.group(1)), int(r.group(2)))
            a = re.search(r"\.allowed\(\{([^}]*)\}\)", body)
            if a:
                entry["allowed"] = re.findall(r"\"([^\"]*)\"", a.group(1))
            defs[m.group(2)] = entry
    return defs


def check_profile(defs: dict[str, dict], mute: dict) -> list[str]:
    errors = []
    for name, value in mute.items():
        d = defs.get(name)
        if not d:
            errors.append(f"{name}: not defined in the pinned source (an unknown --flag is stashed silently)")
            continue
        if value is None or value is True:
            if d["type"] != "BOOL":
                errors.append(f"{name}: boolean form used for {d['type']}")
            continue
        if d["type"] == "BOOL":
            errors.append(f"{name}: value form used for BOOL")
        if d["type"] == "INT32":
            if not re.fullmatch(r"-?\d+", value):
                errors.append(f"{name}: {value!r} not an integer")
            elif d["range"] and not d["range"][0] <= int(value) <= d["range"][1]:
                errors.append(f"{name}: {value} outside {d['range']}")
        if d["allowed"] is not None and value not in d["allowed"]:
            errors.append(f"{name}: {value!r} not in {d['allowed']}")
    return errors


def static_check(tree: Path, verify_git: bool = True) -> dict:
    result: dict = {"tree": str(tree), "checks": []}

    def ok(name, cond, detail=""):
        result["checks"].append({"check": name, "pass": bool(cond), "detail": detail})
        if not cond:
            raise Fail(f"{name}: {detail}")

    if verify_git:
        ok("app HEAD", git(tree, "rev-parse", "HEAD") == APP_HEAD, git(tree, "rev-parse", "HEAD"))
        ok("app clean", git(tree, "status", "--porcelain", "--ignore-submodules=none") == "", "dirty tree")
        sdk = tree / S
        ok("SDK HEAD", git(sdk, "rev-parse", "HEAD") == SDK_HEAD, git(sdk, "rev-parse", "HEAD"))
        ok("SDK clean", git(sdk, "status", "--porcelain") == "", "dirty SDK")
        sdl = tree / S / "thirdparty/sdl3"
        ok("SDL HEAD", git(sdl, "rev-parse", "HEAD") == SDL_HEAD, git(sdl, "rev-parse", "HEAD"))
        ok("SDL clean", git(sdl, "status", "--porcelain") == "", "dirty SDL")
    texts = {}
    for rel, want in PINS.items():
        data = (tree / rel).read_bytes()
        got = hashlib.sha256(data).hexdigest()
        ok(f"pin {rel}", got == want, got)
        texts[rel] = data.decode("utf-8", "replace")
    for rel, rx, count in ANCHORS:
        n = len(re.findall(rx, texts[rel], re.S))
        ok(f"anchor {rel} /{rx[:60]}/", n == count, f"found {n}, expected {count}")

    # Every output call in the scanned SDK input, app and telemetry sources, outside comments.
    scan_roots = [tree / S / "src", tree / "windows/src"] + [tree / r for r in PINS if r.startswith("app/")]
    sites = []
    for root in scan_roots:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix in (".cpp", ".cc", ".c", ".h", ".hpp", ".inc"))
        for p in files:
            for i, line in enumerate(p.read_text("utf-8", "replace").splitlines(), 1):
                code = line.split("//", 1)[0]
                if OUTPUT_API.search(code) and not re.search(r"\bX_RESULT\s+\w+::\w+\(|decltype|GetProcAddress", code):
                    sites.append(f"{p.relative_to(tree).as_posix()}:{i}")
    by_file: dict[str, int] = {}
    for s in sites:
        by_file[s.rsplit(":", 1)[0]] = by_file.get(s.rsplit(":", 1)[0], 0) + 1
    result["output_sites"] = sites
    allowed = {S + "src/input/sdl/sdl_input_driver.cpp", S + "src/input/xinput/xinput_input_driver.cpp",
               "windows/src/fh2_telemetry.cpp", S + "src/system/xsocket.cpp", S + "src/kernel/xam/xam_net.cpp"}
    ok("output sites only in known files", set(by_file) <= allowed, json.dumps(by_file))
    ok("telemetry sendto count", by_file.get("windows/src/fh2_telemetry.cpp") == 1, str(by_file))

    # Runtime writers that outrank the command line: literal names must not touch any mute cvar.
    writers = []
    for p in sorted((tree / S / "src").rglob("*.cpp")) + [tree / "windows/src/main.cpp"] + \
            [tree / r for r in PINS if r.startswith("app/")]:
        if p == tree / S / "src/core/cvar.cpp":  # the definition itself
            continue
        for m in re.finditer(r"SetFlagByName\(\s*(\"(\w+)\"|[^,]+),", p.read_text("utf-8", "replace")):
            writers.append((p.relative_to(tree).as_posix(), m.group(2) or m.group(1).strip()))
    literal = {n for _, n in writers if re.fullmatch(r"\w+", n)}
    dynamic = sorted({f for f, n in writers if not re.fullmatch(r"\w+", n) or f.endswith("overlay.cpp")})
    ok("no literal runtime writer of a mute cvar", not (literal & set(MUTE)), str(sorted(literal & set(MUTE))))
    ok("dynamic runtime writers are the user menus only",
       set(dynamic) <= {S + "src/ui/overlay/settings_overlay.cpp", S + "src/ui/overlay/console_overlay.cpp"}, str(dynamic))
    result["runtime_writers"] = sorted(set(writers))

    # SDK never overrides an environment hint for a joystick backend.
    overrides = [f"{p.relative_to(tree).as_posix()}" for p in (tree / S / "src").rglob("*.cpp")
                 if re.search(r"SDL_HINT_OVERRIDE|SDL_SetHint\w*\(\s*SDL_HINT_(JOYSTICK_(DIRECTINPUT|RAWINPUT|WGI|GAMEINPUT|HIDAPI)\b|XINPUT_ENABLED)",
                              p.read_text("utf-8", "replace"))]
    ok("no SDK override of SDL backend hints", not overrides, str(overrides))

    # Every hint a HIDAPI driver's IsEnabled reads must be fenced to 0 (an enabled per-driver hint beats HIDAPI=0).
    sdl_src = tree / L
    if verify_git:  # full tree only; the tamper control copies pinned files alone
        macros = dict(re.findall(r'#define (SDL_HINT_\w+) "(\w+)"',
                                 (tree / S / "thirdparty/sdl3/include/SDL3/SDL_hints.h").read_text("utf-8", "replace")))
        consulted, drivers = set(), 0
        for p in sorted((sdl_src / "joystick/hidapi").glob("*.c")):
            text = p.read_text("utf-8", "replace")
            local: dict[str, list[str]] = {}
            for name, value in re.findall(r"#define (SDL_HINT_\w+)[ \t]+([^\n]*)", text):
                local.setdefault(name, []).append(value)

            def resolve(macro: str, seen: frozenset = frozenset()) -> set[str]:
                if macro in macros:
                    return {macros[macro]}
                if macro in local and macro not in seen:  # a file-local default: follow every definition
                    return set().union(*(resolve(m, seen | {macro}) for v in local[macro]
                                         for m in re.findall(r"\bSDL_HINT_\w+", v))) if any(
                        re.search(r"\bSDL_HINT_\w+", v) for v in local[macro]) else set()
                return {macro}  # unknown: reported, so the check fails closed

            for body in re.findall(r"static bool \w+_IsEnabled\(void\)\s*\{(.*?)\n\}", text, re.S):
                drivers += 1
                for macro in re.findall(r"\bSDL_HINT_\w+", body):
                    consulted |= resolve(macro)
        result["hidapi_drivers"], result["hidapi_hints"] = drivers, sorted(consulted)
        ok("HIDAPI drivers found", drivers >= 20, str(drivers))
        ok("every HIDAPI enable hint fenced", consulted <= set(SDL_FENCE), str(sorted(consulted - set(SDL_FENCE))))
        haptic_hints = re.findall(r"SDL_GetHint\w*\(", "".join(p.read_text("utf-8", "replace")
                                                             for p in (sdl_src / "haptic/hidapi").glob("*.c")))
        ok("HIDAPI haptic reads no own enable hint", not haptic_hints, str(haptic_hints))
    virtual = [p.relative_to(tree).as_posix() for p in (tree / S).rglob("*") if p.suffix in (".cpp", ".h")
               and "thirdparty" not in p.relative_to(tree / S).parts and not p.name.startswith("joystick_mapping")
               and "VirtualJoystick" in p.read_text("utf-8", "replace")]
    ok("SDL virtual joystick never attached (no users)", not virtual, str(virtual))

    defs = cvar_definitions({k: v for k, v in texts.items()} | {
        str(p): p.read_text("utf-8", "replace") for p in (tree / S / "src").rglob("*.cpp")})
    errors = check_profile(defs, MUTE | {"pad_log_vibration": True, "wheel_ffb_trace": True,
                                          "wheel_ffb_trace_file": "x", "fh2_captura_cada_s": "15",
                                          "fh2_captura_max": "40", "fh2_teste_botoes": BUTTONS,
                                          "fullscreen": None, "resolution": "1280x720",
                                          "game_data_root": "x", "user_data_root": "x", "cache_root": "x"})
    ok("profile names/types/ranges valid", not errors, "; ".join(errors))
    result["pass"] = True
    return result


# ---------------------------------------------------------------------------------------------- profile

def launch_profile(root: Path, owner: Path) -> dict:
    root = Path(os.path.abspath(root))
    out = root / "out"
    values = MUTE | {
        "pad_log_vibration": True,
        "wheel_ffb_trace": True,
        "wheel_ffb_trace_file": str(out / "ffb-trace.csv"),
        "fh2_captura_cada_s": "15",
        "fh2_captura_max": "40",
        "fh2_teste_botoes": BUTTONS,
        "fullscreen": None,
        "resolution": "1280x720",
        "game_data_root": str(owner / "game"),
        "user_data_root": str(root / "user"),
        "cache_root": str(root / "user" / "cache"),
    }
    argv = [str(root / "bin" / "fh2.exe")]
    for name, value in values.items():
        argv.append(f"--no-{name}" if value is None else f"--{name}" if value is True else f"--{name}={value}")
    toml = "".join(f"{n} = {'false' if v is None else 'true' if v is True else json.dumps(v) if not re.fullmatch(r'-?[0-9]+', v) else v}\n"
                   for n, v in values.items() if n in MUTE)
    write_roots = {"config": root / "bin" / "fh2.toml", "logs": root / "bin" / "logs",
                   "captures": root / "bin" / "capturas", "user": root / "user", "cache": root / "user" / "cache",
                   "ffb_trace": out / "ffb-trace.csv"}
    return {"argv": argv, "env": dict(SDL_FENCE), "toml": toml, "values": values,
            "write_roots": {k: str(v) for k, v in write_roots.items()}}


def launch_env(inherited: dict) -> dict:
    """The inherited environment with every SDL_* variable removed, then the fence applied."""
    env = {k: v for k, v in inherited.items() if not k.upper().startswith("SDL_")}
    env.update(SDL_FENCE)
    return env


def env_errors(env: dict) -> list[str]:
    errors = [f"env {k} = {env.get(k)!r}, want '0'" for k in SDL_FENCE if env.get(k) != "0"]
    errors += [f"env unexpected {k}" for k in env if k.upper().startswith("SDL_") and k not in SDL_FENCE]
    return errors


def effective(profile: dict, toml_text: str | None = None) -> dict:
    """Model the SDK precedence (config < environment < command line) for the mute cvars."""
    import tomllib
    eff: dict = {}
    for k, v in tomllib.loads(profile["toml"] if toml_text is None else toml_text).items():
        eff[k] = ("config", v)
    for a in profile["argv"][1:]:
        m = re.fullmatch(r"--(no-)?(\w+)(?:=(.*))?", a, re.S)
        if m:
            eff[m.group(2)] = ("cli", False if m.group(1) else True if m.group(3) is None else m.group(3))
    return eff


def profile_errors(profile: dict, owner: Path, toml_text: str | None = None) -> list[str]:
    eff = effective(profile, toml_text)
    errors = []
    for name, value in MUTE.items():
        want = False if value is None else value
        got = eff.get(name)
        if got is None or got[0] != "cli" or str(got[1]).lower() != str(want).lower():
            errors.append(f"{name}: effective {got}, want cli {want!r}")
    errors += env_errors(launch_env(dict(os.environ) | profile["env"]))
    if profile["env"] != SDL_FENCE:
        errors.append("profile env differs from the fence")
    for k, v in profile["write_roots"].items():
        if overlaps(Path(v), owner):
            errors.append(f"write root {k} inside owner install: {v}")
    for a in profile["argv"][1:]:
        if re.fullmatch(r"--\w+=", a) and a[2:-1] not in MUTE:
            errors.append(f"unexpected empty value {a}")
    return errors


def overlaps(a: Path, b: Path) -> bool:
    x, y = os.path.normcase(os.path.realpath(a)), os.path.normcase(os.path.realpath(b))
    return x == y or x.startswith(y.rstrip("\\/") + os.sep) or y.startswith(x.rstrip("\\/") + os.sep)


def root_errors(root: Path, owner: Path, must_exist: bool) -> list[str]:
    """Canonical private root under E:/Source/_work, no reparse point anywhere on its path, no owner overlap."""
    errors = []
    absolute = Path(os.path.abspath(root))
    if os.path.normcase(os.path.realpath(absolute)) != os.path.normcase(str(absolute)):
        errors.append(f"{root} is not canonical (reparse point or relative parts)")
    probe = absolute
    while True:
        if probe.exists() and probe.is_symlink() or (probe.exists() and os.path.isjunction(probe)):
            errors.append(f"reparse point on path: {probe}")
        if probe.parent == probe:
            break
        probe = probe.parent
    parent = os.path.normcase(str(PRIVATE_PARENT))
    if os.path.normcase(str(absolute.parent)) != parent:
        errors.append(f"{root} must be a direct child of {PRIVATE_PARENT}")
    if overlaps(absolute, owner):
        errors.append(f"{root} overlaps the owner install")
    if must_exist != absolute.exists():
        errors.append(f"{root} {'missing' if must_exist else 'already exists'}")
    return errors


# ---------------------------------------------------------------------------------------------- owner bytes

def documents_fh2() -> Path:
    buf = ctypes.create_unicode_buffer(260)
    fn = ctypes.WinDLL("shell32").SHGetFolderPathW
    fn.argtypes = [wt.HWND, ctypes.c_int, wt.HANDLE, wt.DWORD, wt.LPWSTR]
    fn.restype = ctypes.c_long
    if fn(None, 5, None, 0, buf) != 0:  # CSIDL_PERSONAL, the SDK's FOLDERID_Documents
        raise Fail("cannot resolve Documents")
    return Path(buf.value) / "fh2"


def snapshot(roots: dict[str, Path]) -> dict:
    """Full SHA-256 plus size, mtime and attributes for every file and directory entry."""
    snap = {}
    for label, root in roots.items():
        if not root.exists():
            snap[label] = None
            continue
        files = {}
        for p in sorted(root.rglob("*")) if root.is_dir() else [root]:
            st = p.stat()
            key = p.relative_to(root).as_posix() if root.is_dir() else p.name
            if p.is_dir():
                files[key + "/"] = {"mtime": st.st_mtime_ns, "attrs": getattr(st, "st_file_attributes", 0)}
                continue
            files[key] = {"size": st.st_size, "mtime": st.st_mtime_ns,
                          "attrs": getattr(st, "st_file_attributes", 0), "sha256": sha256(p)}
        snap[label] = files
    return snap


def diff(before: dict, after: dict) -> list[str]:
    out = []
    for label in sorted(set(before) | set(after)):
        b, a = before.get(label), after.get(label)
        if b is None or a is None:
            if b != a:
                out.append(f"{label}: {'appeared' if b is None else 'disappeared'}")
            continue
        for k in sorted(set(b) | set(a)):
            if b.get(k) != a.get(k):
                out.append(f"{label}/{k}: {b.get(k)} -> {a.get(k)}")
    return out


def owner_roots(owner: Path) -> dict[str, Path]:
    return {"owner_bin": owner / "bin", "owner_logs": owner / "logs", "owner_user": owner / "user",
            "owner_game": owner / "game", "owner_top_toml": owner / "fh2.toml", "documents_fh2": documents_fh2()}


# ---------------------------------------------------------------------------------------------- Win32

K32 = ctypes.WinDLL("kernel32", use_last_error=True)
U32 = ctypes.WinDLL("user32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("dwTime", wt.DWORD)]


for _fn, _args, _res in (
        (U32.GetLastInputInfo, [ctypes.POINTER(LASTINPUTINFO)], wt.BOOL),
        (K32.GetTickCount, [], wt.DWORD),
        (U32.GetForegroundWindow, [], wt.HWND),
        (U32.GetWindowThreadProcessId, [wt.HWND, ctypes.POINTER(wt.DWORD)], wt.DWORD),
        (U32.GetWindowTextW, [wt.HWND, wt.LPWSTR, ctypes.c_int], ctypes.c_int),
        (U32.EnumWindows, [WNDENUMPROC, wt.LPARAM], wt.BOOL),
        (U32.IsWindowVisible, [wt.HWND], wt.BOOL),
        (U32.PostMessageW, [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM], wt.BOOL),
        (K32.GetProcessTimes, [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)] * 4, wt.BOOL),
        (K32.QueryFullProcessImageNameW, [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)], wt.BOOL)):
    _fn.argtypes, _fn.restype = _args, _res


def idle_seconds() -> float:
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    U32.GetLastInputInfo(ctypes.byref(info))
    return ((K32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0


def window_pid(hwnd) -> int:
    pid = wt.DWORD(0)
    U32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def foreground() -> dict:
    hwnd = U32.GetForegroundWindow()
    title = ctypes.create_unicode_buffer(256)
    U32.GetWindowTextW(hwnd, title, 256)
    return {"hwnd": int(hwnd or 0), "pid": window_pid(hwnd) if hwnd else 0, "title": title.value}


def handle_identity(handle: int) -> dict:
    """Birth (FILETIME) and image of a process through the handle we own, immune to PID reuse."""
    t = [wt.FILETIME() for _ in range(4)]
    if not K32.GetProcessTimes(wt.HANDLE(handle), *[ctypes.byref(x) for x in t]):
        raise Fail(f"GetProcessTimes failed {ctypes.get_last_error()}")
    size = wt.DWORD(1024)
    buf = ctypes.create_unicode_buffer(1024)
    if not K32.QueryFullProcessImageNameW(wt.HANDLE(handle), 0, buf, ctypes.byref(size)):
        raise Fail(f"QueryFullProcessImageNameW failed {ctypes.get_last_error()}")
    return {"birth_filetime": (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime, "image": buf.value}


def game_windows(pid: int) -> list[int]:
    found = []

    def cb(hwnd, _):
        if window_pid(hwnd) == pid and U32.IsWindowVisible(hwnd):
            found.append(int(hwnd))
        return True
    U32.EnumWindows(WNDENUMPROC(cb), 0)
    return found


def processes() -> list[dict]:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process | ForEach-Object { \"$($_.ProcessId)`t$($_.ParentProcessId)`t"
                          "$($_.CreationDate.ToFileTimeUtc())`t$($_.Name)`t$($_.ExecutablePath)\" }"],
                         capture_output=True, text=True, timeout=60, check=True).stdout
    rows = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) == 5 and p[0].isdigit():
            rows.append({"pid": int(p[0]), "ppid": int(p[1] or 0), "birth": int(p[2]) if p[2].isdigit() else 0,
                         "name": p[3], "path": p[4]})
    return rows


def census_refusals(rows) -> list[str]:
    return [f"{r['pid']} {r['name']} {r['path']}" for r in rows
            if any(x in (r["name"] + " " + r["path"]).lower() for x in REFUSE_PROCESSES)]


def lease_errors(go: str) -> list[str]:
    """The named vibe lease must be the current slot owner and name this GO."""
    keep, slot = LEASE_DIR / "claude-lease-vibe.json", LEASE_DIR / "test-slot.txt"
    try:
        token = json.loads(keep.read_text(encoding="utf-8-sig"))["token"]
        current = slot.read_text(encoding="utf-8-sig").splitlines()[0].strip()
    except (OSError, KeyError, IndexError, ValueError) as e:
        return [f"lease unreadable: {e}"]
    errors = []
    if current != token:
        errors.append("vibe lease is not the current slot owner")
    if f"GO{go}" not in token or " lease=" not in token:
        errors.append(f"lease purpose does not name GO{go}")
    return errors


# ---------------------------------------------------------------------------------------------- commands

def cmd_prepare(root: Path, owner: Path) -> dict:
    errors = root_errors(root, owner, must_exist=False)
    if errors:
        raise Fail("; ".join(errors))
    for name, want in BIN.items():
        got = sha256(owner / "bin" / name).upper()
        if got != want:
            raise Fail(f"installed {name} {got} != receipt {want}")
    rows = census_refusals(processes())
    if rows:
        raise Fail("refused, running: " + "; ".join(rows))
    profile = launch_profile(root, owner)
    errors = profile_errors(profile, owner)
    if errors:
        raise Fail("; ".join(errors))
    baseline = snapshot(owner_roots(owner))  # before any private write
    (root / "bin").mkdir(parents=True)
    (root / "out").mkdir()
    (root / "user" / "cache").mkdir(parents=True)
    for name in BIN:
        shutil.copy2(owner / "bin" / name, root / "bin" / name)
        if sha256(root / "bin" / name).upper() != BIN[name]:
            raise Fail(f"private copy {name} hash mismatch")
    (root / "bin" / "fh2.toml").write_text(profile["toml"], encoding="utf-8", newline="\n")
    plan = {"schema": SCHEMA, "app": APP_HEAD, "sdk": SDK_HEAD, "owner": str(owner), "root": str(root),
            "bin": BIN, "profile": profile, "toml_sha256": sha256(root / "bin" / "fh2.toml"),
            "tool_sha256": sha256(Path(__file__)), "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (root / "plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    (root / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
    return {"pass": True, "root": str(root), "plan_sha256": sha256(root / "plan.json"),
            "baseline_sha256": sha256(root / "baseline.json")}


def admitted_plan(root: Path, plan_sha: str | None, baseline_sha: str | None) -> dict:
    if plan_sha and sha256(root / "plan.json").lower() != plan_sha.lower():
        raise Fail("plan.json is not the admitted plan")
    if baseline_sha and sha256(root / "baseline.json").lower() != baseline_sha.lower():
        raise Fail("baseline.json is not the admitted baseline")
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    owner = Path(plan["owner"])
    errors = root_errors(root, owner, must_exist=True)
    if plan.get("schema") != SCHEMA or plan.get("bin") != BIN or Path(plan["root"]) != Path(os.path.abspath(root)):
        errors.append("plan schema/bin/root mismatch")
    if plan["profile"] != json.loads(json.dumps(launch_profile(root, owner))):
        errors.append("plan profile differs from the regenerated profile")
    errors += profile_errors(plan["profile"], owner)
    if sha256(Path(__file__)) != plan["tool_sha256"]:
        errors.append("tool changed since prepare")
    if errors:
        raise Fail("; ".join(errors))
    return plan


def cmd_verify(root: Path, plan: dict | None = None) -> dict:
    plan = plan or json.loads((root / "plan.json").read_text(encoding="utf-8"))
    owner = Path(plan["owner"])
    changes = diff(json.loads((root / "baseline.json").read_text(encoding="utf-8")), snapshot(owner_roots(owner)))
    bins = {n: sha256(root / "bin" / n).upper() == h for n, h in plan["bin"].items()}
    running = census_refusals(processes())
    return {"pass": not changes and all(bins.values()) and not running, "owner_changes": changes,
            "private_bins_unchanged": bins, "refused_processes": running}


def evidence(root: Path) -> dict:
    logs = sorted((root / "bin" / "logs").glob("*.log"))
    lines = "\n".join(p.read_text("utf-8", "replace") for p in logs).splitlines()
    caps = sorted((root / "bin" / "capturas").glob("*.png"))
    return {
        "logs": [str(p) for p in logs],
        "sdl_input_initialized": any("SDL input driver initialized successfully" in l for l in lines),
        "sdl_wheel_lines": [l for l in lines if "SDL wheel" in l],
        "sdl_gamepad_opened": [l for l in lines if "OnControllerDeviceAdded" in l],
        "telemetry_sender_started": any("telemetry: loopback sender started" in l for l in lines),
        "vibration_requests": sum("Vibration user" in l for l in lines),
        "captures": [str(p) for p in caps],  # only the command line asks for captures: proves it was applied
        "crash_lines": [l for l in lines if re.search(r"(?i)unhandled exception|access violation|\[critical\]", l)],
    }


def cmd_run(root: Path, go: str, seconds: int, plan_sha: str, baseline_sha: str) -> dict:
    root = Path(os.path.abspath(root))
    plan = admitted_plan(root, plan_sha, baseline_sha)
    errors = lease_errors(go)
    pre = cmd_verify(root, plan)
    if errors or not pre["pass"]:
        raise Fail("preflight: " + json.dumps({"lease": errors, "verify": pre}))
    res: dict = {"go": go, "seconds": seconds, "plan_sha256": plan_sha, "baseline_sha256": baseline_sha,
                 "owner_idle_s_start": round(idle_seconds(), 1), "foreground_before": foreground(),
                 "owner_input_events": 0, "stop": None, "errors": []}
    image = os.path.normcase(str(root / "bin" / "fh2.exe"))
    proc, ident = None, None
    t0 = time.monotonic()
    try:
        with open(root / "out" / "stdout.txt", "wb") as so, open(root / "out" / "stderr.txt", "wb") as se:
            proc = subprocess.Popen(plan["profile"]["argv"], cwd=root / "bin", stdout=so, stderr=se,
                                    env=launch_env(dict(os.environ)))
        ident = {"pid": proc.pid} | handle_identity(int(proc._handle))
        res["process"] = ident
        (root / "out" / "process-receipt.json").write_text(json.dumps(ident), encoding="utf-8")
        if os.path.normcase(ident["image"]) != image:
            raise Fail(f"launched image {ident['image']} is not the private copy")
        last_idle = idle_seconds()
        while proc.poll() is None and time.monotonic() - t0 < seconds:
            if (root / "STOP").exists():
                res["stop"] = "STOP file (owner/kole reclaim)"
                break
            time.sleep(1.0)
            now = idle_seconds()
            if now + 1.5 < last_idle:
                res["owner_input_events"] += 1  # recorded only (kole538387); this run sends no OS input
            last_idle = now
        res["alive_at_end"] = proc.poll() is None
    except Exception as e:  # observer failures never skip cleanup
        res["errors"].append(repr(e))
    finally:
        res["elapsed_s"] = round(time.monotonic() - t0, 1)
        if proc is not None:
            try:
                if proc.poll() is None:
                    hwnds = game_windows(proc.pid) if handle_identity(int(proc._handle)) == {
                        k: v for k, v in ident.items() if k != "pid"} else []
                    for h in hwnds:
                        U32.PostMessageW(wt.HWND(h), 0x0010, 0, 0)  # WM_CLOSE to the verified game's own windows
                    res["wm_close_windows"] = len(hwnds)
                    try:
                        proc.wait(30)
                    except subprocess.TimeoutExpired:
                        proc.kill()  # TerminateProcess on our own handle, never a reopened PID
                        res["forced"] = True
                        proc.wait(15)
                res["exit_code"] = proc.returncode
            except Exception as e:
                res["errors"].append("cleanup: " + repr(e))
        rows = processes()
        lineage = [r for r in rows if os.path.normcase(r["path"] or "") == image
                   or (ident and r["ppid"] == ident["pid"])]
        res["remaining_identities"] = lineage
        res["foreground_after"] = foreground()
        res["owner_idle_s_end"] = round(idle_seconds(), 1)
        res["evidence"] = evidence(root)
        res["postflight"] = cmd_verify(root, plan)
        exited = proc is not None and proc.poll() is not None
        res["custody_clear"] = exited and not lineage and not res["errors"]
        e = res["evidence"]
        res["gates"] = {
            # Runtime negative evidence plus a command-line-applied witness; physical isolation is static only.
            "M_runtime": exited and bool(e["logs"]) and e["sdl_input_initialized"] and e["telemetry_sender_started"]
                         and bool(e["captures"]) and not e["sdl_wheel_lines"] and not e["sdl_gamepad_opened"],
            "G1_boot": res["elapsed_s"] >= 60 and not e["crash_lines"] and bool(e["logs"]),
            "G2_frames": len(e["captures"]) >= 3,
            "G3_menu": "review of captures",
            "R_restore": res["postflight"]["pass"],
        }
        (root / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        res["result_sha256"] = sha256(root / "result.json")
    return res | {"pass": res["custody_clear"] and res["gates"]["R_restore"]}


def cmd_selftest() -> dict:
    checks = []

    def t(name, cond):
        checks.append({"check": name, "pass": bool(cond)})
        if not cond:
            raise Fail(name)

    with tempfile.TemporaryDirectory(prefix="fh2-mute-selftest-") as d:
        d = Path(d)
        owner = d / "owner"
        (owner / "bin").mkdir(parents=True)
        (owner / "game").mkdir()
        (owner / "bin" / "a.dll").write_bytes(b"one")
        (owner / "game" / "big.bin").write_bytes(b"x" * 100)
        roots = {"bin": owner / "bin", "game": owner / "game", "toml": owner / "fh2.toml"}
        base = snapshot(roots)
        mtime = base["bin"]["a.dll"]["mtime"]
        t("unchanged tree compares equal", diff(base, snapshot(roots)) == [])
        (owner / "bin" / "a.dll").write_bytes(b"two")
        os.utime(owner / "bin" / "a.dll", ns=(mtime, mtime))
        t("same-size same-mtime content change detected", diff(base, snapshot(roots)) != [])
        (owner / "bin" / "a.dll").write_bytes(b"one")
        os.utime(owner / "bin" / "a.dll", ns=(mtime, mtime))
        t("restored bytes compare equal", diff(base, snapshot(roots)) == [])
        (owner / "fh2.toml").write_text("x")
        t("created owner fh2.toml detected", any("toml" in c for c in diff(base, snapshot(roots))))
        (owner / "fh2.toml").unlink()
        (owner / "bin" / "new.log").write_text("x")
        t("added file detected", any("new.log" in c for c in diff(base, snapshot(roots))))
        (owner / "bin" / "new.log").unlink()
        big = base["game"]["big.bin"]["mtime"]
        (owner / "game" / "big.bin").write_bytes(b"x" * 99 + b"y")
        os.utime(owner / "game" / "big.bin", ns=(big, big))
        t("game-tree same-size same-mtime change detected (full hash)", diff(base, snapshot(roots)) != [])

        prof = launch_profile(PRIVATE_PARENT / "vibe-fh2-selftest", owner)
        t("generated profile passes", profile_errors(prof, owner) == [])
        loud = prof["toml"].replace("wheel_ffb_strength = 0", "wheel_ffb_strength = 50").replace(
            "wheel_enabled = false", "wheel_enabled = true")
        t("CLI outranks a loud config", profile_errors(prof, owner, toml_text=loud) == [])
        bad = dict(prof, argv=[a for a in prof["argv"] if a != "--pad_rumble_strength=0"])
        t("missing rumble mute refused", any("pad_rumble_strength" in e for e in profile_errors(bad, owner)))
        bad = dict(prof, argv=[a for a in prof["argv"] if a != "--no-wheel_enabled"])
        t("missing wheel_enabled mute refused", any("wheel_enabled" in e for e in profile_errors(bad, owner)))
        inherited = {"PATH": "x", "SDL_JOYSTICK_HIDAPI_PS5": "1", "SDL_JOYSTICK_DIRECTINPUT": "1",
                     "sdl_gamecontrollerconfig": "346e0000,MOZA,a:b0", "SDL_JOYSTICK_HIDAPI_LG4FF": "1"}
        env = launch_env(inherited)
        t("inherited per-driver override neutralised", env["SDL_JOYSTICK_HIDAPI_PS5"] == "0"
          and env["SDL_JOYSTICK_HIDAPI_LG4FF"] == "0" and env["SDL_JOYSTICK_DIRECTINPUT"] == "0")
        t("inherited mapping removed", "sdl_gamecontrollerconfig" not in env and env["PATH"] == "x")
        t("sanitized env passes", env_errors(env) == [])
        t("raw inherited env refused", env_errors(inherited | {k: "0" for k in SDL_BACKENDS}) != [])
        t("profile env tamper refused", any("fence" in e for e in profile_errors(
            dict(prof, env={k: v for k, v in SDL_FENCE.items() if "PS5" not in k}), owner)))
        t("write root inside owner refused", any("inside owner" in e for e in
                                                 profile_errors(launch_profile(owner / "x", owner), owner)))
        t("root outside _work refused", root_errors(d / "elsewhere", owner, False) != [])
        t("root inside owner refused", any("overlaps" in e for e in root_errors(owner / "bin", owner, True)))
        t("existing root refused for prepare", any("already exists" in e for e in root_errors(owner, owner, False)))
        link = d / "link"
        try:
            os.symlink(owner, link, target_is_directory=True)
            t("reparse root refused", root_errors(link / "bin", owner, True) != [])
        except OSError:
            checks.append({"check": "reparse root refused", "pass": None, "detail": "symlink privilege unavailable"})
        defs = {"pad_ds_trigger_strength": {"type": "INT32", "range": (25, 100), "allowed": None},
                "wheel_ffb_mode": {"type": "STRING", "range": None, "allowed": ["difference", "off"]}}
        t("out-of-range value refused", check_profile(defs, {"pad_ds_trigger_strength": "0"}) != [])
        t("unknown cvar refused", check_profile(defs, {"wheel_ffb_strenght": "0"}) != [])
        t("disallowed enum refused", check_profile(defs, {"wheel_ffb_mode": "zero"}) != [])
        row = lambda n, p: {"pid": 1, "ppid": 0, "birth": 0, "name": n, "path": p}
        t("Pit House refused", census_refusals([row("Pit House.exe", "C:/Program Files (x86)/MOZA Pit House/Pit House.exe")]))
        t("SimHub refused", census_refusals([row("SimHubWPF.exe", "C:/Program Files (x86)/SimHub/SimHubWPF.exe")]))
        t("running fh2 refused", census_refusals([row("fh2.exe", "X:/fh2.exe")]))
        t("unrelated process allowed", not census_refusals([row("explorer.exe", "C:/Windows/explorer.exe")]))
        t("lease for another GO refused", lease_errors("selftest-never-a-go") != [])
        t("pointer-width HWND signature", U32.GetForegroundWindow.restype is wt.HWND
          and U32.PostMessageW.argtypes[0] is wt.HWND)
        me = handle_identity(_self_handle())
        t("own-handle identity readable", me["birth_filetime"] > 0 and me["image"].lower().endswith(".exe"))
    return {"pass": True, "checks": checks}


def _self_handle() -> int:
    K32.OpenProcess.argtypes, K32.OpenProcess.restype = [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE
    return int(K32.OpenProcess(0x1000, False, os.getpid()))  # PROCESS_QUERY_LIMITED_INFORMATION


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--tree", type=Path, required=True)
    sub.add_parser("selftest")
    sub.add_parser("census")
    p = sub.add_parser("prepare")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--owner", type=Path, default=OWNER)
    v = sub.add_parser("verify")
    v.add_argument("--root", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--root", type=Path, required=True)
    r.add_argument("--go", required=True)
    r.add_argument("--plan-sha256", required=True)
    r.add_argument("--baseline-sha256", required=True)
    r.add_argument("--seconds", type=int, default=600)
    a = ap.parse_args()
    try:
        if a.cmd == "check":
            out = static_check(a.tree)
            # Negative control: the same pinned bytes with the wheel_enabled guard removed must fail.
            with tempfile.TemporaryDirectory(prefix="fh2-mute-tamper-") as d:
                for rel in PINS:
                    (Path(d) / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(a.tree / rel, Path(d) / rel)
                static_check(Path(d), verify_git=False)  # pinned copy alone passes
                victim = Path(d) / (S + "src/input/sdl/sdl_input_driver.cpp")
                victim.write_text(victim.read_text("utf-8").replace(
                    "  if (!REXCVAR_GET(wheel_enabled)) {\n    return false;\n  }\n", "", 1), "utf-8", newline="")
                try:
                    static_check(Path(d), verify_git=False)
                    raise Fail("tampered wheel guard was not refused")
                except Fail as e:
                    if "tampered" in str(e):
                        raise
                    out["negative_control"] = f"refused as expected: {str(e)[:120]}"
        elif a.cmd == "selftest":
            out = cmd_selftest()
        elif a.cmd == "census":
            rows = census_refusals(processes())
            out = {"pass": not rows, "refused": rows, "owner_idle_s": round(idle_seconds(), 1)}
        elif a.cmd == "prepare":
            out = cmd_prepare(a.root, a.owner)
        elif a.cmd == "verify":
            out = cmd_verify(a.root)
        else:
            out = cmd_run(a.root, a.go, min(a.seconds, 780), a.plan_sha256, a.baseline_sha256)
    except Fail as e:
        print(json.dumps({"pass": False, "error": str(e)}, indent=1))
        return 1
    print(json.dumps(out, indent=1))
    return 0 if out.get("pass", True) else 1


if __name__ == "__main__":
    sys.exit(main())
