#!/usr/bin/env python3
"""Compiles windows/src/fh2_device_paths.h against the patched SDK's DevicePathPolicy with a fake
input system and checks the host side of fh2_excluded_device_paths. Needs patches/sdk applied
(build.ps1 does that). The SDK's own tests/unit/input/device_path_seam.py checks the driver side.

    python -I fh2_device_paths_check.py --cxx <clang++> --out <scratch folder>
"""
import argparse
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cxx", required=True)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()
windows = Path(__file__).resolve().parents[1]

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
  const auto policy = ParseExcludedPaths(" //?/HID#VID_346E&PID_0006#7&a ; other ");
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
