from __future__ import annotations

import importlib.util
import io
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"wbcp_test_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagingSafetyTests(unittest.TestCase):
    def test_source_packager_rejects_symlinks(self) -> None:
        module = load_script("package_candidate")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.txt"
            target.write_text("safe", encoding="utf-8")
            (root / "alias.txt").symlink_to(target)
            module.ROOT = root
            with self.assertRaisesRegex(RuntimeError, "BLOCKED_PACKAGE_SYMLINK"):
                module.files()

    def test_package_manifest_generator_rejects_symlinks(self) -> None:
        module = load_script("generate_package_manifest")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.txt"
            target.write_text("safe", encoding="utf-8")
            (root / "alias.txt").symlink_to(target)
            module.ROOT = root
            with self.assertRaisesRegex(RuntimeError, "BLOCKED_PACKAGE_SYMLINK"):
                module.included_files()

    def test_local_oneclick_provenance_marker_is_never_packaged_or_manifested(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".wbcp-oneclick-source.json").write_text('{"local": true}\n', encoding="utf-8")
            (root / "README.md").write_text("portable candidate\n", encoding="utf-8")
            for script, function in (
                ("package_candidate", "files"),
                ("generate_package_manifest", "included_files"),
                ("generate_supply_chain", "source_paths"),
            ):
                module = load_script(script)
                module.ROOT = root
                paths = getattr(module, function)()
                self.assertEqual([path.name for path in paths], ["README.md"])

    def test_safe_extractor_rejects_path_escape_and_removes_partial_output(self) -> None:
        module = load_script("safe_extract_candidate")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "candidate.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                safe = tarfile.TarInfo("candidate/README.md")
                safe_data = b"safe source\n"
                safe.size = len(safe_data)
                handle.addfile(safe, io.BytesIO(safe_data))
                escape = tarfile.TarInfo("../escape.txt")
                escape_data = b"blocked\n"
                escape.size = len(escape_data)
                handle.addfile(escape, io.BytesIO(escape_data))
            output = root / "extracted"
            with self.assertRaisesRegex(module.UnsafeArchiveError, "BLOCKED_ARCHIVE_MEMBER_PATH"):
                module.extract_archive(archive, output, expected_root="candidate")
            self.assertFalse(output.exists())
            self.assertFalse((root / "escape.txt").exists())

    def test_safe_extractor_accepts_exact_root_zip_and_rejects_symlink(self) -> None:
        module = load_script("safe_extract_candidate")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            valid = root / "candidate.zip"
            with zipfile.ZipFile(valid, "w") as handle:
                handle.writestr("candidate/README.md", "safe source\n")
            report = module.extract_archive(valid, root / "valid", expected_root="candidate")
            self.assertEqual(report["status"], "PASS")
            self.assertEqual((root / "valid" / "candidate" / "README.md").read_text(), "safe source\n")

            unsafe = root / "unsafe.zip"
            with zipfile.ZipFile(unsafe, "w") as handle:
                link = zipfile.ZipInfo("candidate/link")
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                handle.writestr(link, "target")
            with self.assertRaisesRegex(module.UnsafeArchiveError, "BLOCKED_ARCHIVE_SPECIAL_MEMBER"):
                module.extract_archive(unsafe, root / "unsafe", expected_root="candidate")
            self.assertFalse((root / "unsafe").exists())


if __name__ == "__main__":
    unittest.main()
