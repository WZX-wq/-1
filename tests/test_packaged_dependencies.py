import hashlib
import os
import unittest
from pathlib import Path

import pefile
from PyInstaller.archive.readers import CArchiveReader


class PackagedDependenciesTests(unittest.TestCase):
    def test_qt_icu_dependencies_are_bundled(self):
        executable = os.environ.get("PACKAGED_EXE_PATH")
        if not executable:
            self.skipTest("Set PACKAGED_EXE_PATH to validate a release executable")

        executable_path = Path(executable)
        internal_dir = executable_path.parent / "_internal"
        if internal_dir.is_dir():
            qt_bin = internal_dir / "PyQt6" / "Qt6" / "bin"
            if not (qt_bin / "Qt6Widgets.dll").is_file():
                qt_bin = internal_dir
            expected_hashes = {
                "Qt6Core.dll": "05982ff42ba7ae3074badaee1a09ff7f45e694de815bb06b514b28c28cfe0500",
                "Qt6Widgets.dll": "3fac74f2736ee0850657005ceade2a4edef6e97d58c764e77c2e39e629e04e82",
                "icu.dll": "119f844e8b65b1103f10aa13718c4bbe12abe372477f065bc4c5d46d0aac9c96",
                "icuuc.dll": "59d134ddc15ae0594f0a328979f8201662fc82634ddb7c537b156e7cf871f5eb",
                "icuin.dll": "585026af25fe25b330de89c5b7376ec8ac504980f4393b98236fbdb302e3215b",
            }
            for name, expected_hash in expected_hashes.items():
                dependency = qt_bin / name
                self.assertTrue(dependency.is_file(), dependency)
                actual_hash = hashlib.sha256(dependency.read_bytes()).hexdigest()
                self.assertEqual(actual_hash, expected_hash, dependency)

            qtcore = pefile.PE(
                str(qt_bin / "Qt6Core.dll"), fast_load=False
            )
            imports = {
                import_item.name.decode("ascii", "replace")
                for entry in getattr(qtcore, "DIRECTORY_ENTRY_IMPORT", [])
                for import_item in entry.imports
                if import_item.name
            }
            self.assertNotIn("SetThreadDescription", imports)

            # The release also carries a flat fallback for older Windows DLL
            # search behavior; verify it is not accidentally omitted.
            if qt_bin != internal_dir:
                for name in expected_hashes:
                    fallback = internal_dir / name
                    self.assertTrue(fallback.is_file(), fallback)

            qtwidgets = internal_dir / "PyQt6" / "QtWidgets.pyd"
            self.assertTrue(qtwidgets.is_file(), qtwidgets)
            self.assertEqual(
                hashlib.sha256(qtwidgets.read_bytes()).hexdigest(),
                "3daad2162489819f55f3013d9250362271bbabba51712224576b970ed9f3bf0c",
            )
            return

        archive = CArchiveReader(str(executable_path))
        bundled_files = set(archive.toc)
        required_files = {
            r"PyQt6\Qt6\bin\icu.dll",
            r"PyQt6\Qt6\bin\icuuc.dll",
            r"PyQt6\Qt6\bin\icuin.dll",
        }
        self.assertFalse(required_files - bundled_files, required_files - bundled_files)


if __name__ == "__main__":
    unittest.main()
