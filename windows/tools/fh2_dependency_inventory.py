"""Read hash-bound payload imports with LLVM; never load or execute a payload binary.

File presence is a catalog observation, not Windows loader/search/ABI/driver
success. API-set contract availability and runtime LoadLibrary calls remain
unresolved. This inventories all PE members, including optional upscalers.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def read_metadata(text):
    if "Format: COFF-x86-64" not in text or not re.search(r"(?m)^Arch: x86_64$", text):
        raise ValueError("Expected an x64 PE image")
    delay = re.search(r"DelayImportDescriptorRVA: (0x[0-9A-Fa-f]+)", text)
    if not delay:
        raise ValueError("Missing delay-directory metadata; inventory is incomplete")
    imports = []
    for match in re.finditer(r"(?m)^(Import|DelayImport) \{\r?\n(.*?)^\}", text, re.S):
        body = match[2]
        names = re.findall(r"(?m)^  Name: ([^\r\n]+)$", body)
        if len(names) != 1 or not re.fullmatch(r"[A-Za-z0-9_.-]+\.dll", names[0], re.I):
            raise ValueError("Unsupported import module name")
        imports.append({"kind": match[1], "name": names[0],
                        "symbolCount": len(re.findall(r"(?m)^[ \t]+Symbol:", body))})
    if bool(int(delay[1], 16)) != any(x["kind"] == "DelayImport" for x in imports):
        raise ValueError("Delay-directory/LLVM-record mismatch; inventory is incomplete")
    headers = len(re.findall(r"(?m)^(?:Import|DelayImport) \{", text))
    if headers != len(imports):
        raise ValueError("Unrecognized LLVM import record")
    return imports


def member_path(root, relative):
    value = PurePosixPath(relative)
    if value.is_absolute() or ".." in value.parts or "\\" in relative or ":" in relative:
        raise ValueError("Manifest member must be a relative path")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Manifest member escapes the payload")
    return path


def catalog(name, importer, members, system32):
    lower = name.lower()
    if lower.startswith(("api-", "ext-")):
        return {"observation": "api_set_contract", "availability": "not_checked"}
    siblings = [x for x in members if PurePosixPath(x).parent == PurePosixPath(importer).parent
                and PurePosixPath(x).name.lower() == lower]
    if siblings:
        return {"observation": "packaged_same_directory", "members": siblings}
    packaged = [x for x in members if PurePosixPath(x).name.lower() == lower]
    if packaged:
        return {"observation": "packaged_elsewhere_search_unproven", "members": packaged}
    host = system32 / name
    vc = bool(re.match(r"(?:msvcp|vcruntime|concrt|msvcr)\d", lower))
    return {"observation": "host_system32_file_present" if host.is_file() else "not_found_in_catalog",
            "path": str(host), "vc_runtime_name": vc}


def inventory(llvm, root, manifest_path, output, system32):
    root = root.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    members = manifest["members"]
    if not 1 <= len(members) <= 64 or len({x["path"] for x in members}) != len(members):
        raise ValueError("Invalid or duplicate manifest members")
    verified = {}
    for item in members:
        path = member_path(root, item["path"])
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError("Payload differs from manifest: " + item["path"])
        verified[item["path"]] = path
    output.mkdir(parents=True, exist_ok=False)
    report = {"source": manifest["source"], "sdk": manifest["sdk"],
              "manifestSha256": digest(manifest_path), "llvmSha256": digest(llvm),
              "scriptSha256": digest(Path(__file__)),
              "observedUtc": datetime.now(timezone.utc).isoformat(), "system32Catalog": str(system32),
              "payloadExecuted": False, "libraryLoaded": False, "ownerStateWritten": False,
              "startupEstablished": False, "apiSetAvailabilityChecked": False,
              "runtimeLibraryLoadsEnumerated": False, "files": []}
    for relative, path in verified.items():
        if path.suffix.lower() not in (".exe", ".dll"):
            continue
        result = subprocess.run([str(llvm), "--file-header", "--coff-imports", str(path)],
                                capture_output=True, text=True, timeout=30, check=True)
        (output / (relative.replace("/", "__") + ".llvm.txt")).write_text(result.stdout, encoding="utf-8")
        imports = read_metadata(result.stdout)
        for imported in imports:
            imported.update(catalog(imported["name"], relative, verified, system32))
        report["files"].append({"path": relative, "sha256": digest(path), "imports": imports})
    (output / "inventory.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llvm", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sys.maxsize <= 2**32:
        raise SystemExit("Use x64 Python for the native System32 catalog")
    report = inventory(args.llvm.resolve(strict=True), args.payload, args.manifest, args.out,
                       Path(os.environ["SystemRoot"]) / "System32")
    print(f"PASS: {len(report['files'])} hash-bound x64 PE files inventoried; no load/startup claim")
