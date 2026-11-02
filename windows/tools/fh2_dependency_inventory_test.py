import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import json

from fh2_dependency_inventory import catalog, inventory, member_path, read_metadata


class InventoryTests(unittest.TestCase):
    def metadata(self, body, delay="0x0"):
        return "Format: COFF-x86-64\nArch: x86_64\nDelayImportDescriptorRVA: " + delay + "\n" + body

    def test_normal_and_delay(self):
        text = self.metadata("Import {\n  Name: KERNEL32.dll\n  Symbol: ExitProcess (1)\n}\n"
                             "DelayImport {\n  Name: optional.dll\n  Import {\n    Symbol: Later (0)\n  }\n}\n", "0x1000")
        self.assertEqual([x["kind"] for x in read_metadata(text)], ["Import", "DelayImport"])
        self.assertEqual(read_metadata(text)[1]["symbolCount"], 1)

    def test_refuses_incomplete_metadata(self):
        for text in ["Format: COFF-i386", self.metadata("", "0x1000"),
                     self.metadata("Import {\n  Name: ../evil.dll\n}\n"),
                     self.metadata("Import {\n  Unknown: no name\n}\n")]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                read_metadata(text)

    def test_api_contract_is_not_a_missing_file(self):
        self.assertEqual(catalog("api-ms-win-crt-runtime-l1-1-0.dll", "fh2.exe", [], Path("nonexistent"))["observation"],
                         "api_set_contract")

    def test_packaged_location_is_not_loader_success(self):
        names = ["rexruntime.dll", "optional/backend.dll"]
        self.assertEqual(catalog("REXRUNTIME.DLL", "fh2.exe", names, Path("nonexistent"))["observation"], "packaged_same_directory")
        self.assertEqual(catalog("backend.dll", "fh2.exe", names, Path("nonexistent"))["observation"], "packaged_elsewhere_search_unproven")

    def test_member_escape_refused(self):
        # Disposable fixture is kept under the project, not a machine temp root.
        parent = Path(__file__).resolve().parents[1] / ".local"
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            root = Path(temp).resolve()
            self.assertTrue(root.is_relative_to(parent.resolve()))
            (root / "valid.dll").write_bytes(b"fixture")
            self.assertEqual(member_path(root, "valid.dll"), root / "valid.dll")
            for name in ["../outside.dll", "C:/outside.dll", "x\\outside.dll"]:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    member_path(root, name)

    def test_hash_mismatch_refused_before_tool_or_output(self):
        parent = Path(__file__).resolve().parents[1] / ".local"
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            root = Path(temp).resolve()
            self.assertTrue(root.is_relative_to(parent.resolve()))
            (root / "fh2.exe").write_bytes(b"tampered")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"members": [{"path": "fh2.exe", "bytes": 8, "sha256": "0" * 64}]}))
            with patch("fh2_dependency_inventory.subprocess.run", side_effect=AssertionError("must not run")):
                with self.assertRaisesRegex(ValueError, "differs from manifest"):
                    inventory(root / "unused-tool.exe", root, manifest, root / "output", root)
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
