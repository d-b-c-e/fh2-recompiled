// Calls actual candidate cvar.cpp; inert paths only, including a real rename failure.
#include <rex/cvar.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

REXCVAR_DEFINE_INT32(fh2_save_result, 1, "Save result fixture", "Inert value");
int main(int argc, char** argv) {
  if (argc != 2) return 2;
  unsigned checks = 0;
  try {
    const auto root = std::filesystem::path(argv[1]);
    if (!std::filesystem::is_directory(root) || !std::filesystem::is_empty(root))
      throw std::runtime_error("Pass an existing empty fixture directory");
    const auto check = [&](bool ok, const char* why) {
      if (!ok) throw std::runtime_error(why); ++checks;
    };
    const auto read = [](const auto& path) {
      std::ifstream file(path, std::ios::binary);
      return std::string((std::istreambuf_iterator<char>(file)), {});
    };
    const auto write = [](const auto& path, const auto& text) {
      std::ofstream file(path, std::ios::binary); file << text;
    };
    rex::cvar::testing::ResetAllForTesting();
    const auto absent = root / "defaults.toml";
    check(rex::cvar::TrySaveConfig(absent) && !std::filesystem::exists(absent), "default no-op must succeed without creating a file");
    const auto empty = root / "empty.toml";
    write(empty, "");
    check(rex::cvar::TrySaveConfig(empty) && read(empty).empty(), "empty existing no-op must succeed");
    REXCVAR_SET(fh2_save_result, 2);
    const auto path = root / "saved.toml";
    check(rex::cvar::TrySaveConfig(path), "new save must report success");
    const auto saved = read(path);
    check(saved.find("fh2_save_result = 2") != std::string::npos, "success did not publish requested value");
    check(rex::cvar::TrySaveConfig(path) && read(path) == saved, "unchanged save must succeed without changing bytes");
    REXCVAR_SET(fh2_save_result, 3);
    const auto staging = path.string() + ".tmp";
    write(staging, "retained staging");
    check(!rex::cvar::TrySaveConfig(path), "staging collision must report failure");
    check(read(path) == saved && read(staging) == "retained staging", "collision changed original or staging");
    for (const auto& content : {"fh2_save_result=1\nfh2_save_result=2\n", "fh2_save_result=[1,2]\n", "owner='unfinished\n"}) {
      const auto invalid = root / ("invalid" + std::to_string(checks) + ".toml");
      write(invalid, content);
      check(!rex::cvar::TrySaveConfig(invalid), "parse/shape refusal must report failure");
      check(read(invalid) == content, "refusal changed original bytes");
    }
    const auto directory = root / "directory.toml";
    std::filesystem::create_directory(directory);
    check(!rex::cvar::TrySaveConfig(directory), "unreadable directory target must fail");
    const auto missing = root / "missing" / "config.toml";
    check(!rex::cvar::TrySaveConfig(missing) && !std::filesystem::exists(missing), "missing parent must fail without publication");
    const auto locked = root / "readonly.toml";
    write(locked, "fh2_save_result=1\n");
    std::filesystem::permissions(locked, std::filesystem::perms::owner_read, std::filesystem::perm_options::replace);
    const bool result = rex::cvar::TrySaveConfig(locked);
    std::filesystem::permissions(locked, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
    check(!result && read(locked) == "fh2_save_result=1\n", "read-only destination rename must report failure and preserve original");
    check(std::filesystem::exists(locked.string() + ".tmp"), "failed rename staging should be retained");
    // Legacy void API still reaches the same implementation and remains callable.
    const auto legacy = root / "legacy.toml";
    rex::cvar::SaveConfig(legacy);
    check(read(legacy).find("fh2_save_result = 3") != std::string::npos, "legacy API stopped saving");
    std::cout << "PASS: " << checks << " real save-result checks; inert files only\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "FAIL after " << checks << " checks: " << e.what() << '\n'; return 1;
  }
}
