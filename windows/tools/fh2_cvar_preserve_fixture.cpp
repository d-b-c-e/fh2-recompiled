// Production cvar.cpp and toml++ only; no game, graphics, input or device initialization.
#include <rex/cvar.h>
#include <toml++/toml.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

REXCVAR_DEFINE_STRING(fh2_preserve_string, "new", "Preserve fixture", "Inert string");
REXCVAR_DEFINE_INT32(fh2_preserve_int, 7, "Preserve fixture", "Inert integer");

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  unsigned checks = 0;
  try {
    const auto root = std::filesystem::path(argv[1]);
    if (!std::filesystem::is_directory(root) || !std::filesystem::is_empty(root))
      throw std::runtime_error("Pass an existing empty fixture directory");
    const auto check = [&](bool ok, const char* why) {
      if (!ok) throw std::runtime_error(why);
      ++checks;
    };
    rex::cvar::testing::ResetAllForTesting();
    const std::vector<std::pair<std::string, std::string>> cases = {
      {"# owner\r\n  fh2_preserve_int  = 1  # tune\r\n", "# owner\r\n  fh2_preserve_int  = 7  # tune\r\n"},
      {"\"fh2_preserve_int\" = 1", "\"fh2_preserve_int\" = 7"},
      {"'fh2_preserve_string' = '\xC3\xA9\xF0\x9F\x9B\x9E' # unicode\n",
       "'fh2_preserve_string' = \"new\" # unicode\n"},
      {"\"fh2_preserve_\\u0069nt\"=1\n", "\"fh2_preserve_\\u0069nt\"=7\n"},
      {"fh2_preserve_string = \"\"\"old\n[not_table]\nfh2_preserve_int = 999\n\"\"\" # end\r\nfh2_preserve_int=1",
       "fh2_preserve_string = \"new\" # end\r\nfh2_preserve_int=7"},
      {"fh2_preserve_string='''old\n[a]\n'''\n", "fh2_preserve_string=\"new\"\n"},
      {"fh2_preserve_int=1\n[scope]\nfh2_preserve_int=2\n", "fh2_preserve_int=7\n[scope]\nfh2_preserve_int=2\n"},
      {"fh2_preserve_int = 1\r\n# LF follows\n", "fh2_preserve_int = 7\r\n# LF follows\n"},
      {"\xEF\xBB\xBF" "fh2_preserve_int=1\r\n", "\xEF\xBB\xBF" "fh2_preserve_int=7\r\n"},
    };
    for (const auto& [before, expected] : cases) {
      const auto result = rex::cvar::MergeIntoTOML(before);
      check(result == expected, "owned scalar edit changed surrounding bytes");
      check(toml::parse(result).contains("fh2_preserve_int") ||
            toml::parse(result).contains("fh2_preserve_string"), "merged output is not valid root TOML");
      check(rex::cvar::MergeIntoTOML(result) == result, "second merge is not stable");
    }
    const std::vector<std::string> untouched = {
      "host = \"\"\"text\nfh2_preserve_int = 999\n[looks_like_table]\n\"\"\"\n",
      "host = '''text\nfh2_preserve_string = 'owner'\n[a]\n'''\r\n",
      "host = [\n  '[a]',\n  \"fh2_preserve_int=2\"\n]\n",
      "host = { fh2_preserve_int=1, nested={ fh2_preserve_string='owner' } }\n",
      "host.child = 'owner'\n[host.other]\nfh2_preserve_int=2\n",
      "[[cars]]\nfh2_preserve_int=1\n[[cars]]\nfh2_preserve_int=2\n",
      "# Unicode \xC3\xA9 \xF0\x9F\x9B\x9E\n# final comment",
    };
    for (const auto& before : untouched)
      check(rex::cvar::MergeIntoTOML(before) == before, "unknown owner data changed");
    REXCVAR_SET(fh2_preserve_int, 8);
    for (const auto& before : {"[table]\nkeep=1\n", "[[cars]]\nkeep=1\n",
                              "host.child='owner'\n[host.other]\nkeep=1\n",
                              "host='''[fake]\n'''\n", "# EOF", ""}) {
      const auto result = rex::cvar::MergeIntoTOML(before);
      check(toml::parse(result)["fh2_preserve_int"].value<int64_t>() == 8,
            "missing cvar appended outside root scope");
      check(rex::cvar::MergeIntoTOML(result) == result, "appended cvar not stable");
    }
    const std::vector<std::string> refused = {
      "fh2_preserve_int=1\nfh2_preserve_int=2\n", "fh2_preserve_int = [1,2]\n",
      "[fh2_preserve_int]\nx=1\n", "fh2_preserve_string = \"unfinished\n",
      "host = [\n", std::string("host='bad\xFF'\n"),
    };
    unsigned index = 0;
    const auto read = [](const auto& path) {
      std::ifstream file(path, std::ios::binary);
      return std::string((std::istreambuf_iterator<char>(file)), {});
    };
    for (const auto& before : refused) {
      bool threw = false;
      try { (void)rex::cvar::MergeIntoTOML(before); } catch (const std::exception&) { threw = true; }
      check(threw, "ambiguous or invalid TOML was accepted");
      const auto path = root / ("refused" + std::to_string(index++) + ".toml");
      { std::ofstream file(path, std::ios::binary); file << before; }
      rex::cvar::SaveConfig(path);
      check(read(path) == before, "refused SaveConfig changed owner bytes");
      check(!std::filesystem::exists(path.string() + ".tmp"), "refused save created staging output");
    }
    const auto path = root / "bom.toml";
    const std::string before = "\xEF\xBB\xBF" "# owner\r\nfh2_preserve_int = 1 # tune\r\n";
    { std::ofstream file(path, std::ios::binary); file << before; }
    rex::cvar::SaveConfig(path);
    const std::string expected = "\xEF\xBB\xBF" "# owner\r\nfh2_preserve_int = 8 # tune\r\n";
    check(read(path) == expected, "SaveConfig lost BOM or comments");
    rex::cvar::SaveConfig(path);
    check(read(path) == expected, "second SaveConfig changed bytes");
    const auto staging = path.string() + ".tmp";
    { std::ofstream file(staging, std::ios::binary); file << "retained owner staging"; }
    REXCVAR_SET(fh2_preserve_int, 9);
    rex::cvar::SaveConfig(path);
    check(read(path) == expected && read(staging) == "retained owner staging", "save overwrote existing staging file");
    std::cout << "PASS: " << checks << " preservation checks; actual cvar.cpp/toml++; inert files only\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "FAIL after " << checks << " checks: " << e.what() << '\n';
    return 1;
  }
}
