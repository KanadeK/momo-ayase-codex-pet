from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from petease.archive import package_pet, verify_archive
from petease.atlas import get_cell, load_package
from petease.compile import choose_medoid, compile_reduced_motion
from petease.install import install_package

from .helpers import make_package


class CompileInstallArchiveTests(unittest.TestCase):
    def test_compile_reduced_motion_is_static_and_preserves_looks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_package(root / "source", moving=True)
            source_package, source_image = load_package(source)
            source_image.paste(
                (180, 40, 90, 255),
                (6 * 192 + 48, 34, 6 * 192 + 130, 164),
            )
            source_image.save(source_package.spritesheet_path)
            output = root / "reduced"
            provenance = compile_reduced_motion(source, output)
            self.assertEqual(provenance["output"]["id"], "fixture-pet-reduced-motion")
            source_package, source_image = load_package(source)
            output_package, output_image = load_package(output)
            self.assertNotEqual(source_package.image_sha256, output_package.image_sha256)
            self.assertNotIn(b"\r", (output / "pet.json").read_bytes())
            self.assertNotIn(b"\r", (output / "petease-provenance.json").read_bytes())
            for column in range(6):
                self.assertEqual(
                    get_cell(output_image, 0, column).tobytes(),
                    get_cell(output_image, 0, 0).tobytes(),
                )
            for row in (9, 10):
                for column in range(8):
                    self.assertEqual(
                        get_cell(output_image, row, column).tobytes(),
                        get_cell(source_image, row, column).tobytes(),
                    )
            self.assertEqual(
                get_cell(output_image, 0, 6).tobytes(),
                get_cell(source_image, 0, 6).tobytes(),
            )

    def test_medoid_is_deterministic(self) -> None:
        from PIL import Image

        dark = Image.new("RGBA", (8, 8), (10, 10, 10, 255))
        middle = Image.new("RGBA", (8, 8), (20, 20, 20, 255))
        bright = Image.new("RGBA", (8, 8), (240, 240, 240, 255))
        self.assertEqual(choose_medoid([dark, middle, bright]), 1)
        self.assertEqual(choose_medoid([dark]), 0)
        with self.assertRaisesRegex(ValueError, "zero frames"):
            choose_medoid([])

    def test_force_refuses_unrelated_or_source_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_package(root / "source")
            unrelated = root / "unrelated"
            unrelated.mkdir()
            (unrelated / "keep.txt").write_text("mine", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not previously generated"):
                compile_reduced_motion(source, unrelated, force=True)
            with self.assertRaisesRegex(ValueError, "source package"):
                compile_reduced_motion(source, source, force=True)

    def test_transactional_install_dry_run_and_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_package(root / "source")
            codex_home = root / "codex-home"
            dry = install_package(source, codex_home=codex_home, dry_run=True)
            self.assertTrue(dry["dry_run"])
            self.assertFalse((codex_home / "pets").exists())

            first = install_package(source, codex_home=codex_home)
            destination = Path(first["destination"])
            self.assertTrue((destination / ".petease-install.json").is_file())
            second = install_package(source, codex_home=codex_home)
            self.assertIsNotNone(second["backup"])
            self.assertTrue(Path(second["backup"]).is_dir())

    def test_archive_is_deterministic_and_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_package(root / "source")
            first = root / "first.codex-pet"
            second = root / "second.codex-pet"
            result_one = package_pet(source, first)
            result_two = package_pet(source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(result_one["sha256"], result_two["sha256"])
            self.assertTrue(verify_archive(first)["ok"])
            with zipfile.ZipFile(first) as archive:
                self.assertTrue(all(info.create_system == 3 for info in archive.infolist()))
            with self.assertRaisesRegex(ValueError, ".codex-pet"):
                package_pet(source, root / "wrong.zip")

            unsafe = root / "unsafe.codex-pet"
            with zipfile.ZipFile(unsafe, "w") as archive:
                archive.writestr("../pet.json", "{}")
            with self.assertRaisesRegex(ValueError, "missing pet.json"):
                verify_archive(unsafe)


if __name__ == "__main__":
    unittest.main()
