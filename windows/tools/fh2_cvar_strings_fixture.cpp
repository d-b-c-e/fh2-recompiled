// Offline production-cvar fixture. No game, input, graphics or device initialization.
#include <rex/cvar.h>
#include <toml++/toml.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

REXCVAR_DEFINE_STRING(fh2_fixture_string, "default", "FH2 String Fixture", "Inert string");
REXCVAR_DEFINE_INT32(fh2_fixture_int, 1, "FH2 String Fixture", "Inert integer");
REXCVAR_DEFINE_BOOL(fh2_fixture_bool, false, "FH2 String Fixture", "Inert boolean");

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "Pass an existing empty fixture directory.\n";
    return 2;
  }
  try {
    const auto root = std::filesystem::path(argv[1]);
    if (!std::filesystem::is_directory(root) || !std::filesystem::is_empty(root)) {
      throw std::runtime_error("Fixture directory must exist and be empty");
    }
    unsigned checks = 0;
    const auto check = [&](bool condition, const char* message) {
      if (!condition) throw std::runtime_error(message);
      ++checks;
    };
    const std::vector<std::string> values = {
        R"(path:\\?\HID#VID_0EB7&PID_0004)", "quote\" and slash\\", "'literal' and \"quotes\"",
        "line\nreturn\rtab\tback\bform\f", std::string("nul\0end", 7), "controls\x01\x1F\x7F",
        "Unicode caf\xC3\xA9", ""};
    for (size_t i = 0; i < values.size(); ++i) {
      const auto& value = values[i];
      rex::cvar::testing::ResetAllForTesting();
      REXCVAR_SET(fh2_fixture_string, value);
      REXCVAR_SET(fh2_fixture_int, 7);
      REXCVAR_SET(fh2_fixture_bool, true);
      const auto parse = [&](const std::string& text) {
        const auto parsed = toml::parse(text);
        check(parsed["fh2_fixture_string"].value<std::string>() == value, "string changed");
        check(parsed["fh2_fixture_int"].value<int64_t>() == 7, "integer changed");
        check(parsed["fh2_fixture_bool"].value<bool>() == true, "boolean changed");
        check(text.find("\"\"\"") == std::string::npos, "multiline output");
      };
      parse(rex::cvar::SerializeToTOML());
      parse(rex::cvar::SerializeToTOML("FH2 String Fixture"));
      const std::string host = "# host\r\nhost_schema = 27\r\nfh2_fixture_string = 'old'\r\n"
                               "[section]\r\nkeep = 7\r\n";
      const auto merged = rex::cvar::MergeIntoTOML(host);
      parse(merged);
      check(merged.starts_with("# host\r\nhost_schema = 27\r\n"), "unknown root changed");
      check(merged.ends_with("[section]\r\nkeep = 7\r\n"), "unknown table changed");
      parse(rex::cvar::MergeIntoTOML("[section]\nkeep = 7\n"));
      const auto path = root / (std::to_string(i) + ".toml");
      { std::ofstream file(path, std::ios::binary); file << host; }
      rex::cvar::SaveConfig(path);
      std::ifstream file(path, std::ios::binary);
      const std::string saved((std::istreambuf_iterator<char>(file)), {});
      parse(saved);
      check(saved == merged, "saved bytes differ from merge");
      REXCVAR_SET(fh2_fixture_string, "overwritten before load");
      rex::cvar::LoadConfig(path);
      check(REXCVAR_GET(fh2_fixture_string) == value, "real LoadConfig did not restore string");
      rex::cvar::SaveConfig(path);
      std::ifstream again(path, std::ios::binary);
      check(std::string((std::istreambuf_iterator<char>(again)), {}) == saved,
            "second save changed bytes");
    }
    std::cout << "PASS: " << checks << " checks, " << values.size()
              << " strings; real serializers/merge/SaveConfig/LoadConfig; inert files only\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}
