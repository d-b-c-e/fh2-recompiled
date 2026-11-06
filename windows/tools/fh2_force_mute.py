"""FH2 force/motion mute and private smoke route for the installed 734fff4/SDK e223 build.

No rebuild. Two independent layers keep every physical output silent:

  A. SDK cvars (command line, outranking the private fh2.toml that repeats them): the wheel path is
     never opened (wheel_enabled false), every wheel force is off/zero, guest rumble is scaled to 0,
     DualSense triggers off, Forza Data Out port 0, controller chords to the settings/debug menus empty.
  B. SDL environment hints on the fh2 process only: DirectInput, RawInput, WGI, GameInput, HIDAPI and
     XInput joystick backends off, so SDL can enumerate or open no physical controller. Opening a
     force-capable DirectInput device alone sends DISFFC_RESET and DIPROP_AUTOCENTER on, so A alone is not
     enough; B alone holds even if a runtime menu flipped A.

Nothing on the MOZA, Pit House or SimHub is changed, so "restore" is a byte-exact proof that the owner
install, Documents/fh2 and the private copy's inputs are unchanged, plus a closed-process census.

  python -I fh2_force_mute.py check --tree <734fff4 checkout with SDK e223>
  python -I fh2_force_mute.py selftest
  python -I fh2_force_mute.py census
  python -I fh2_force_mute.py prepare --root <private> [--owner <install>]
  python -I fh2_force_mute.py verify --root <private>
  python -I fh2_force_mute.py run --root <private> --go <event> [--seconds 600]

run sends no OS input (scripted pad and in-process captures only); take the Rig-Lease outside it.
"""

from __future__ import annotations

import argparse
import ctypes
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
# Layer B: every SDL3 Windows joystick backend that could see a wheel base.
SDL_ENV = {
    "SDL_JOYSTICK_DIRECTINPUT": "0",  # also gates the DirectInput haptic backend
    "SDL_JOYSTICK_RAWINPUT": "0",
    "SDL_JOYSTICK_WGI": "0",
    "SDL_JOYSTICK_GAMEINPUT": "0",
    "SDL_JOYSTICK_HIDAPI": "0",
    "SDL_XINPUT_ENABLED": "0",
}
REFUSE_PROCESSES = ("pit house", "mozapithouse", "simhub", "fh2.exe")  # FH2-only Pit House rule
# Scripted pad (in-process, synthetic): advance boot prompts only; no stick steering (STD-039).
BUTTONS = "45:a,60:a,75:start,90:a,105:a,120:a,150:a,180:a,210:a,240:start,270:a"

OUTPUT_API = re.compile(
    r"\b(SDL_Rumble\w*|SDL_SendGamepadEffect|SDL_SendJoystickEffect|SDL_\w*Haptic\w*|SDL_SetGamepadLED|"
    r"SDL_SetJoystickLED|SDL_hid_write|SDL_hid_send_feature_report|XInputSetState_?|sendto|WSASendTo)\s*\(")
# Expected output call sites per file in the exact source (calls, not declarations).
OUTPUT_SITES = {
    S + "src/input/sdl/sdl_input_driver.cpp": None,  # counted below, every site behind wheel_/gamepad gates
    S + "src/input/xinput/xinput_input_driver.cpp": None,
    "windows/src/fh2_telemetry.cpp": 1,
}

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
    root = root.resolve()
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
    return {"argv": argv, "env": dict(SDL_ENV), "toml": toml, "values": values,
            "write_roots": {k: str(v) for k, v in write_roots.items()}}


def effective(profile: dict, toml_text: str | None = None, env: dict | None = None) -> dict:
    """Model the SDK precedence (config < environment < command line) for the mute cvars."""
    import tomllib
    eff: dict = {}
    for k, v in tomllib.loads(profile["toml"] if toml_text is None else toml_text).items():
        eff[k] = ("config", v)
    for a in profile["argv"][1:]:
        m = re.fullmatch(r"--(no-)?(\w+)(?:=(.*))?", a, re.S)
        if m:
            eff[m.group(2)] = ("cli", False if m.group(1) else True if m.group(3) is None else m.group(3))
    eff["__env__"] = env if env is not None else profile["env"]
    return eff


def profile_errors(profile: dict, owner: Path, toml_text: str | None = None, env: dict | None = None) -> list[str]:
    eff = effective(profile, toml_text, env)
    errors = []
    for name, value in MUTE.items():
        want = False if value is None else value
        got = eff.get(name)
        if got is None or got[0] != "cli" or str(got[1]).lower() != str(want).lower():
            errors.append(f"{name}: effective {got}, want cli {want!r}")
    for k, v in SDL_ENV.items():
        if eff["__env__"].get(k) != v:
            errors.append(f"env {k} missing")
    owner_r = str(owner.resolve()).lower()
    for k, v in profile["write_roots"].items():
        if str(Path(v).resolve()).lower().startswith(owner_r):
            errors.append(f"write root {k} inside owner install: {v}")
    for a in profile["argv"][1:]:
        if re.fullmatch(r"--\w+=", a) and a[2:-1] not in MUTE:
            errors.append(f"unexpected empty value {a}")
    return errors


# ---------------------------------------------------------------------------------------------- owner bytes

def documents_fh2() -> Path:
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # CSIDL_PERSONAL, the SDK's FOLDERID_Documents
    return Path(buf.value) / "fh2"


def snapshot(roots: dict[str, Path], hash_limit: int = 64 << 20) -> dict:
    """Full SHA-256 for every file up to hash_limit, size+mtime+attrs beyond (the 7.4 GB game/ tree)."""
    snap = {}
    for label, root in roots.items():
        if not root.exists():
            snap[label] = None
            continue
        files = {}
        for p in sorted(root.rglob("*")) if root.is_dir() else [root]:
            st = p.stat()
            if p.is_dir():
                files[p.relative_to(root).as_posix() + "/"] = {"mtime": st.st_mtime_ns}
                continue
            files[p.relative_to(root).as_posix() if root.is_dir() else p.name] = {
                "size": st.st_size, "mtime": st.st_mtime_ns,
                "attrs": getattr(st, "st_file_attributes", 0),
                "sha256": sha256(p) if st.st_size <= hash_limit else None}
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


# ---------------------------------------------------------------------------------------------- processes

def processes() -> list[tuple[int, str, str]]:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process | ForEach-Object { \"$($_.ProcessId)`t$($_.Name)`t$($_.ExecutablePath)\" }"],
                         capture_output=True, text=True, check=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].isdigit():
            rows.append((int(parts[0]), parts[1], parts[2]))
    return rows


def census_refusals(rows) -> list[str]:
    return [f"{pid} {name} {path}" for pid, name, path in rows
            if any(r in (name + " " + path).lower() for r in REFUSE_PROCESSES)]


def idle_seconds() -> float:
    class LII(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    info = LII(ctypes.sizeof(LII), 0)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0


def foreground() -> dict:
    u = ctypes.windll.user32
    hwnd = u.GetForegroundWindow()
    pid = ctypes.c_uint(0)
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    title = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, title, 256)
    return {"hwnd": int(hwnd or 0), "pid": pid.value, "title": title.value}


def close_windows(pid: int) -> int:
    u = ctypes.windll.user32
    sent = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        p = ctypes.c_uint(0)
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(hwnd):
            u.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
            sent.append(hwnd)
        return True
    u.EnumWindows(cb, 0)
    return len(sent)


# ---------------------------------------------------------------------------------------------- commands

def cmd_prepare(root: Path, owner: Path) -> dict:
    if root.exists() and any(root.iterdir()):
        raise Fail(f"{root} exists and is not empty; choose a fresh session root")
    for name, want in BIN.items():
        got = sha256(owner / "bin" / name).upper()
        if got != want:
            raise Fail(f"installed {name} {got} != receipt {want}")
    rows = census_refusals(processes())
    if rows:
        raise Fail("refused, running: " + "; ".join(rows))
    (root / "bin").mkdir(parents=True)
    (root / "out").mkdir()
    (root / "user" / "cache").mkdir(parents=True)
    for name in BIN:
        shutil.copy2(owner / "bin" / name, root / "bin" / name)
        if sha256(root / "bin" / name).upper() != BIN[name]:
            raise Fail(f"private copy {name} hash mismatch")
    profile = launch_profile(root, owner)
    errors = profile_errors(profile, owner)
    if errors:
        raise Fail("; ".join(errors))
    (root / "bin" / "fh2.toml").write_text(profile["toml"], encoding="utf-8", newline="\n")
    baseline = snapshot(owner_roots(owner))
    plan = {"schema": "dbce.fh2-force-mute-smoke@1", "app": APP_HEAD, "sdk": SDK_HEAD, "owner": str(owner),
            "bin": BIN, "profile": profile, "toml_sha256": sha256(root / "bin" / "fh2.toml"),
            "tool_sha256": sha256(Path(__file__)), "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (root / "plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    (root / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
    return {"pass": True, "root": str(root), "plan_sha256": sha256(root / "plan.json"),
            "baseline_sha256": sha256(root / "baseline.json")}


def cmd_verify(root: Path) -> dict:
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    owner = Path(plan["owner"])
    changes = diff(json.loads((root / "baseline.json").read_text(encoding="utf-8")), snapshot(owner_roots(owner)))
    bins = {n: sha256(root / "bin" / n).upper() == h for n, h in plan["bin"].items()}
    toml_same = sha256(root / "bin" / "fh2.toml") == plan["toml_sha256"]
    running = census_refusals(processes())
    return {"pass": not changes and all(bins.values()) and not running, "owner_changes": changes,
            "private_bins_unchanged": bins, "private_toml_unchanged": toml_same, "refused_processes": running}


def evidence(root: Path) -> dict:
    logs = sorted((root / "bin" / "logs").glob("*.log"))
    text = "\n".join(p.read_text("utf-8", "replace") for p in logs)
    trace = root / "out" / "ffb-trace.csv"
    caps = sorted((root / "bin" / "capturas").glob("*.png"))
    return {
        "logs": [str(p) for p in logs],
        "sdl_wheel_lines": [l for l in text.splitlines() if "SDL wheel" in l],
        "sdl_gamepad_opened": [l for l in text.splitlines() if "OnControllerDeviceAdded" in l],
        "telemetry_started_port0": "telemetry: loopback sender started" in text,
        "vibration_requests": sum("Vibration user" in l for l in text.splitlines()),
        "ffb_trace_rows": max(0, len(trace.read_text("utf-8", "replace").splitlines()) - 1) if trace.exists() else None,
        "captures": [str(p) for p in caps],
        "title_started": bool(re.search(r"(?i)launching module|title (started|module)|module loaded", text)),
        "crash": bool(re.search(r"(?i)unhandled exception|access violation|fatal", text)),
    }


def cmd_run(root: Path, go: str, seconds: int) -> dict:
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    if sha256(Path(__file__)) != plan["tool_sha256"]:
        raise Fail("tool changed since prepare")
    pre = cmd_verify(root)
    if not pre["pass"] or not pre["private_toml_unchanged"]:
        raise Fail("preflight: " + json.dumps(pre))
    if idle_seconds() < 180:
        raise Fail(f"owner input {idle_seconds():.0f}s ago (< 180 s)")
    res: dict = {"go": go, "seconds": seconds, "foreground_before": foreground(), "aborts": []}
    env = dict(os.environ) | plan["profile"]["env"]
    stdout = open(root / "out" / "stdout.txt", "wb")
    stderr = open(root / "out" / "stderr.txt", "wb")
    t0 = time.monotonic()
    proc = subprocess.Popen(plan["profile"]["argv"], cwd=root / "bin", env=env, stdout=stdout, stderr=stderr)
    res["pid"] = proc.pid
    last_idle = idle_seconds()
    while proc.poll() is None and time.monotonic() - t0 < seconds:
        time.sleep(1.0)
        now_idle = idle_seconds()
        if now_idle + 1.5 < last_idle:  # this run sends no OS input, so any input is the owner
            res["aborts"].append("owner input")
            break
        last_idle = now_idle
    res["alive_at_end"] = proc.poll() is None
    res["elapsed_s"] = round(time.monotonic() - t0, 1)
    if proc.poll() is None:
        res["wm_close_windows"] = close_windows(proc.pid)
        try:
            proc.wait(30)
        except subprocess.TimeoutExpired:
            proc.kill()  # exact owned handle, after graceful retry; forces are already zero/unopened
            res["forced"] = True
            proc.wait(10)
    res["exit_code"] = proc.returncode
    stdout.close()
    stderr.close()
    res["foreground_after"] = foreground()
    res["evidence"] = evidence(root)
    res["postflight"] = cmd_verify(root)
    e = res["evidence"]
    res["gates"] = {
        "M_mute": not e["sdl_wheel_lines"] and not e["sdl_gamepad_opened"] and res["postflight"]["pass"],
        "G1_boot": res["elapsed_s"] >= 60 and not e["crash"],
        "G2_frames": len(e["captures"]) >= 3,
        "G3_menu": "owner/agent review of captures",
        "R_restore": res["postflight"]["pass"] and not res["postflight"]["owner_changes"],
    }
    (root / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    res["result_sha256"] = sha256(root / "result.json")
    return res


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
        base = snapshot(roots, hash_limit=50)
        t("unchanged tree compares equal", diff(base, snapshot(roots, 50)) == [])
        (owner / "bin" / "a.dll").write_bytes(b"two")
        os.utime(owner / "bin" / "a.dll", ns=(base["bin"]["a.dll"]["mtime"], base["bin"]["a.dll"]["mtime"]))
        t("same-size same-mtime content change detected", diff(base, snapshot(roots, 50)) != [])
        (owner / "bin" / "a.dll").write_bytes(b"one")
        os.utime(owner / "bin" / "a.dll", ns=(base["bin"]["a.dll"]["mtime"], base["bin"]["a.dll"]["mtime"]))
        t("restored bytes compare equal", diff(base, snapshot(roots, 50)) == [])
        (owner / "fh2.toml").write_text("x")
        t("created owner fh2.toml detected", any("toml" in c for c in diff(base, snapshot(roots, 50))))
        (owner / "fh2.toml").unlink()
        (owner / "bin" / "new.log").write_text("x")
        t("added file detected", any("new.log" in c for c in diff(base, snapshot(roots, 50))))
        (owner / "bin" / "new.log").unlink()
        with open(owner / "game" / "big.bin", "ab") as f:
            f.write(b"y")
        t("large-file size change detected", diff(base, snapshot(roots, 50)) != [])

        prof = launch_profile(d / "private", owner)
        t("generated profile passes", profile_errors(prof, owner) == [])
        loud = prof["toml"].replace("wheel_ffb_strength = 0", "wheel_ffb_strength = 50").replace("wheel_enabled = false", "wheel_enabled = true")
        t("CLI outranks a loud config", profile_errors(prof, owner, toml_text=loud) == [])
        bad = dict(prof, argv=[a for a in prof["argv"] if a != "--pad_rumble_strength=0"])
        t("missing rumble mute refused", any("pad_rumble_strength" in e for e in profile_errors(bad, owner)))
        bad = dict(prof, argv=[a for a in prof["argv"] if a != "--no-wheel_enabled"])
        t("missing wheel_enabled mute refused", any("wheel_enabled" in e for e in profile_errors(bad, owner)))
        t("missing DirectInput env refused",
          any("DIRECTINPUT" in e for e in profile_errors(prof, owner, env={k: v for k, v in SDL_ENV.items() if "DIRECT" not in k})))
        inside = launch_profile(owner / "x", owner)
        t("write root inside owner refused", any("inside owner" in e for e in profile_errors(inside, owner)))
        defs = {"pad_ds_trigger_strength": {"type": "INT32", "range": (25, 100), "allowed": None},
                "wheel_ffb_mode": {"type": "STRING", "range": None, "allowed": ["difference", "off"]}}
        t("out-of-range value refused", check_profile(defs, {"pad_ds_trigger_strength": "0"}) != [])
        t("unknown cvar refused", check_profile(defs, {"wheel_ffb_strenght": "0"}) != [])
        t("disallowed enum refused", check_profile(defs, {"wheel_ffb_mode": "zero"}) != [])
        t("Pit House refused", census_refusals([(1, "Pit House.exe", "C:/Program Files (x86)/MOZA Pit House/Pit House.exe")]))
        t("SimHub refused", census_refusals([(2, "SimHubWPF.exe", "C:/Program Files (x86)/SimHub/SimHubWPF.exe")]))
        t("running fh2 refused", census_refusals([(3, "fh2.exe", "X:/fh2.exe")]))
        t("unrelated process allowed", not census_refusals([(4, "explorer.exe", "C:/Windows/explorer.exe")]))
        t("pin mismatch detected", hashlib.sha256(b"tampered").hexdigest() not in PINS.values())
    return {"pass": True, "checks": checks}


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
            out = cmd_run(a.root, a.go, min(a.seconds, 780))
    except Fail as e:
        print(json.dumps({"pass": False, "error": str(e)}, indent=1))
        return 1
    print(json.dumps(out, indent=1))
    return 0 if out.get("pass", True) else 1


if __name__ == "__main__":
    sys.exit(main())
