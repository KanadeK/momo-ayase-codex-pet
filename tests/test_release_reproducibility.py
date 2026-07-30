from __future__ import annotations

import gzip
import io
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_release import (
    SOURCE_DATE_EPOCH,
    canonicalize_sdist,
    canonicalize_wheel,
    python_distribution_sources,
    write_checksums,
)


def write_wheel(path: Path, *, create_system: int, newline: bytes) -> None:
    entries = {
        "petease/__init__.py": b'__version__ = "0.1.0"' + newline,
        "petease-0.1.0.dist-info/METADATA": b"Metadata-Version: 2.4" + newline,
        "petease-0.1.0.dist-info/WHEEL": b"Wheel-Version: 1.0" + newline,
        "petease-0.1.0.dist-info/RECORD": b"platform-specific,stale,record" + newline,
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, date_time=(2024, 2, 3, 4, 5, 6))
            info.create_system = create_system
            info.external_attr = (0o100666 if create_system == 0 else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)


def write_sdist(path: Path, *, mtime: int, newline: bytes, uid: int) -> None:
    contents = {
        "petease-0.1.0/PKG-INFO": b"Metadata-Version: 2.4" + newline,
        "petease-0.1.0/src/petease/__init__.py": b'__version__ = "0.1.0"' + newline,
    }
    with path.open("wb") as raw:
        with gzip.GzipFile(filename=path.name, mode="wb", fileobj=raw, mtime=mtime) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                directory = tarfile.TarInfo("petease-0.1.0")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o777
                directory.mtime = mtime
                directory.uid = uid
                directory.gid = uid
                archive.addfile(directory)
                for name, data in contents.items():
                    info = tarfile.TarInfo(name)
                    info.mode = 0o666
                    info.mtime = mtime
                    info.uid = uid
                    info.gid = uid
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))


class ReleaseReproducibilityTests(unittest.TestCase):
    def test_wheel_normalization_removes_platform_metadata_and_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            windows = root / "windows.whl"
            unix = root / "unix.whl"
            write_wheel(windows, create_system=0, newline=b"\r\n")
            write_wheel(unix, create_system=3, newline=b"\n")

            canonicalize_wheel(windows)
            canonicalize_wheel(unix)

            self.assertEqual(windows.read_bytes(), unix.read_bytes())
            with zipfile.ZipFile(windows) as archive:
                self.assertTrue(all(info.create_system == 3 for info in archive.infolist()))
                self.assertNotIn(b"\r", archive.read("petease-0.1.0.dist-info/METADATA"))
                record = archive.read("petease-0.1.0.dist-info/RECORD")
                self.assertIn(b"sha256=", record)
                self.assertNotIn(b"stale", record)

    def test_sdist_normalization_removes_platform_metadata_and_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            windows = root / "windows.tar.gz"
            unix = root / "unix.tar.gz"
            write_sdist(windows, mtime=1_700_000_000, newline=b"\r\n", uid=0)
            write_sdist(unix, mtime=1_800_000_000, newline=b"\n", uid=1001)

            canonicalize_sdist(windows)
            canonicalize_sdist(unix)

            self.assertEqual(windows.read_bytes(), unix.read_bytes())
            with tarfile.open(windows, "r:gz") as archive:
                for member in archive.getmembers():
                    self.assertEqual(member.mtime, SOURCE_DATE_EPOCH)
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                metadata = archive.extractfile("petease-0.1.0/PKG-INFO")
                self.assertIsNotNone(metadata)
                if metadata is not None:
                    self.assertNotIn(b"\r", metadata.read())

    def test_python_distribution_whitelist_ignores_unrelated_source_directories(self) -> None:
        relative = [path.as_posix() for path in python_distribution_sources()]
        self.assertTrue(any(path.endswith("/src/petease/archive.py") for path in relative))
        self.assertFalse(any("petprobe" in path for path in relative))

    def test_checksum_order_is_independent_of_platform_path_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "DEPENDENCIES.md").write_text("upper", encoding="utf-8")
            (root / "audit.json").write_text("lower", encoding="utf-8")

            checksums = write_checksums(root).read_text(encoding="utf-8").splitlines()

            self.assertTrue(checksums[0].endswith("  audit.json"))
            self.assertTrue(checksums[1].endswith("  DEPENDENCIES.md"))


if __name__ == "__main__":
    unittest.main()
