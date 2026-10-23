#!/usr/bin/env python3
"""Compiles windows/src/fh2_device_paths.h against the patched SDK's DevicePathPolicy with a fake
input system and checks the host side of fh2_excluded_device_paths. Needs patches/sdk applied
(build.ps1 does that). The SDK's own tests/unit/input/device_path_seam.py checks the driver side.

    python -I fh2_device_paths_check.py --cxx <clang++> --out <scratch folder>
"""
import argparse
import re
import subprocess
import tomllib
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cxx", required=True)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()
windows = Path(__file__).resolve().parents[1]
sdk = windows / "thirdparty/shiftglue-sdk"

# The list is read once before input opens, so the setting must say it needs a restart (F4 marks
# kHotReload settings as live).
main = (windows / "src/main.cpp").read_text()
start = main.find("REXCVAR_DEFINE_STRING(fh2_excluded_device_paths,")
definition = main[start:main.find("\n\n", start)] if start >= 0 else ""  # the description itself holds ';'
assert "Lifecycle::kRequiresRestart" in definition, "fh2_excluded_device_paths must be kRequiresRestart"
# Save and reload: SaveConfig writes a string setting as "value" with no escaping (cvar.cpp
# MergeIntoTOML). The '/' form survives that; the same path with backslashes does not.
assert 'FlagType::String ? "\\"" + entry.getter() + "\\""' in (sdk / "src/core/cvar.cpp").read_text(), "SDK string write rule changed"
saved = "//?/HID#VID_346E&PID_0006#7&a; other"
assert tomllib.loads(f'fh2_excluded_device_paths = "{saved}"\n')["fh2_excluded_device_paths"] == saved, "slash form must round-trip"
try:
    reread = tomllib.loads('fh2_excluded_device_paths = "\\\\?\\HID#VID_346E&PID_0006#7&a"\n')["fh2_excluded_device_paths"]
except tomllib.TOMLDecodeError:
    reread = None
assert reread != "\\\\?\\HID#VID_346E&PID_0006#7&a", "a backslash path must not be mistaken for safe"
print("setting metadata and save/reload checks passed")

harness = r'''
#include "fh2_device_paths.h"
#include <cstdlib>
#include <iostream>
int checks = 0;
void check(bool ok, const char* why) {
  ++checks;
  if (!ok) { std::cerr << "FAIL: " << why << '\n'; std::exit(1); }
}
struct FakeInput {
  int accepting = 1, calls = 0;
  rex::input::DevicePathPolicy seen;
  size_t ConfigureDevicePaths(const rex::input::DevicePathPolicy& policy) { ++calls; seen = policy; return accepting; }
};
int main() {
  using fh2::ParseExcludedPaths;
  check(ParseExcludedPaths("").excluded_paths.empty(), "empty excludes nothing");
  check(ParseExcludedPaths(" ; ;\t").excluded_paths.empty(), "blank entries dropped");
  const auto policy = ParseExcludedPaths("//?/HID#VID_346E&PID_0006#7&a; other");  // the saved form
  check(policy.excluded_paths.size() == 2, "two paths");
  check(policy.excluded_paths[0] == "\\\\?\\HID#VID_346E&PID_0006#7&a", "slashes read as backslashes, trimmed");
  check(!policy.Allows("\\\\?\\hid#vid_346e&pid_0006#7&a"), "excluded path refused, any case");
  check(policy.Allows("\\\\?\\HID#VID_346E&PID_0007#7&a"), "another device still allowed");
  check(!policy.Allows("other") && policy.Allows("others"), "exact match only");

  FakeInput stock;
  check(fh2::InstallExcludedPaths(stock, "") && stock.calls == 0, "unset: nothing installed");
  FakeInput one;
  check(fh2::InstallExcludedPaths(one, "a;b") && one.calls == 1 && one.seen.excluded_paths.size() == 2,
        "one accepting driver: installed");
  FakeInput none; none.accepting = 0;
  check(!fh2::InstallExcludedPaths(none, "a"), "no accepting driver: refused");
  FakeInput two; two.accepting = 2;
  check(!fh2::InstallExcludedPaths(two, "a"), "two accepting drivers: refused");
  std::cout << checks << " host exclusion checks passed\n";
}
'''
args.out.mkdir(parents=True, exist_ok=True)
source = args.out.resolve() / "fh2_device_paths_check.cpp"
exe = args.out.resolve() / "fh2_device_paths_check.exe"
source.write_text(harness)
subprocess.run([args.cxx, "-std=c++20", "-Wall", "-Wextra", "-Werror",
                "-I", str(windows / "src"), "-I", str(windows / "thirdparty/shiftglue-sdk/include"),
                str(source), "-o", str(exe)], check=True)
subprocess.run([str(exe)], check=True)
