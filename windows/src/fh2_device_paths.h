#pragma once
// Optional exclusion of exact device paths from the game's SDL input (patches\sdk\0001), for a
// wheel another program drives. Header-only so tools\fh2_device_paths_check.py can test it.
#include <rex/input/device_path_policy.h>

#include <algorithm>
#include <string>
#include <string_view>

namespace fh2 {

// "path;path" -> exclusions. Blank entries are dropped, so "" excludes nothing. '/' is read as
// '\': the SDK writes string settings back unescaped, so a backslash cannot stay in fh2.toml.
inline rex::input::DevicePathPolicy ParseExcludedPaths(std::string_view list) {
  rex::input::DevicePathPolicy policy;
  while (!list.empty()) {
    const auto end = list.find(';');
    auto item = list.substr(0, end);
    while (!item.empty() && (item.front() == ' ' || item.front() == '\t')) item.remove_prefix(1);
    while (!item.empty() && (item.back() == ' ' || item.back() == '\t')) item.remove_suffix(1);
    if (!item.empty()) {
      std::string path(item);
      std::replace(path.begin(), path.end(), '/', '\\');
      policy.excluded_paths.push_back(std::move(path));
    }
    if (end == std::string_view::npos) break;
    list.remove_prefix(end + 1);
  }
  return policy;
}

// True when nothing is excluded, or when exactly one driver (SDL, the only one that can) took the
// exclusions before the window attached. Anything else would let the excluded device open.
template <class Input>
bool InstallExcludedPaths(Input& input, std::string_view list) {
  const auto policy = ParseExcludedPaths(list);
  return policy.excluded_paths.empty() || input.ConfigureDevicePaths(policy) == 1;
}

}  // namespace fh2
