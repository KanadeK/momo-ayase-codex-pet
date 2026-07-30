from __future__ import annotations

import json
import os
import runpy
import tempfile
import unittest
import warnings
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from petease.archive import package_pet, verify_archive
from petease.atlas import (
    PetPackageError,
    iter_cells,
    load_package,
    save_webp,
    sha256_file,
)
from petease.audit import audit_package
from petease.cli import main
from petease.compile import compile_reduced_motion
from petease.install import install_package, resolve_codex_home
from petease.sarif import to_sarif

from .helpers import make_package


def rewrite_manifest(root: Path, **changes: object) -> None:
    path = root / "pet.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.update(changes)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def write_zip(path: Path, entries: list[tuple[str, bytes, int | None]]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, contents, external_attr in entries:
            info = zipfile.ZipInfo(name)
            if external_attr is not None:
                info.external_attr = external_attr
            archive.writestr(info, contents)


class PackageValidationEdgeTests(unittest.TestCase):
    def test_missing_nonobject_and_missing_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(PetPackageError, "does not exist"):
                load_package(root / "missing")

            empty = root / "empty"
            empty.mkdir()
            with self.assertRaisesRegex(PetPackageError, "Missing pet.json"):
                load_package(empty)

            (empty / "pet.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(PetPackageError, "one JSON object"):
                load_package(empty)

            (empty / "pet.json").write_text('{"id": "only"}', encoding="utf-8")
            with self.assertRaisesRegex(PetPackageError, "is missing"):
                load_package(empty)

    def test_manifest_values_id_and_sprite_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            cases = (
                ("version", {"spriteVersionNumber": 1}, "must be 2"),
                ("empty", {"description": ""}, "non-empty"),
                ("unsafe-id", {"id": "../escape"}, "1-64 lowercase"),
                ("missing-image", {"spritesheetPath": "gone.png"}, "Missing spritesheet"),
            )
            for name, changes, message in cases:
                with self.subTest(name=name):
                    package = make_package(base / name)
                    rewrite_manifest(package, **changes)
                    with self.assertRaisesRegex(PetPackageError, message):
                        load_package(package)

            unreadable = make_package(base / "unreadable")
            (unreadable / "spritesheet.png").write_bytes(b"not an image")
            with self.assertRaisesRegex(PetPackageError, "Unreadable spritesheet"):
                load_package(unreadable)

    def test_nested_sprite_iteration_and_lossless_save(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_package(Path(temporary) / "pet")
            assets = root / "assets"
            assets.mkdir()
            (root / "spritesheet.png").replace(assets / "atlas.png")
            rewrite_manifest(root, spritesheetPath="assets/atlas.png")
            package, image = load_package(root)
            cells = list(iter_cells(image))
            self.assertEqual(len(cells), 88)
            self.assertEqual(sum(used for _, _, used, _ in cells), 73)
            output = Path(temporary) / "copy.webp"
            save_webp(image, output)
            self.assertEqual(len(sha256_file(output)), 64)
            self.assertEqual(package.spritesheet_path, assets / "atlas.png")
            archive = Path(temporary) / "nested.codex-pet"
            result = package_pet(root, archive)
            self.assertIn("assets/atlas.png", result["entries"])
            self.assertTrue(verify_archive(archive)["ok"])


class ArchiveAndInstallEdgeTests(unittest.TestCase):
    def test_packaging_refuses_bad_input_and_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = make_package(root / "pet")
            output = root / "pet.codex-pet"
            package_pet(package, output)
            with self.assertRaises(FileExistsError):
                package_pet(package, output)

            (package / "NOTICE.md").write_text("notice", encoding="utf-8")
            temporary_archive = output.with_suffix(".codex-pet.tmp")
            temporary_archive.write_text("stale", encoding="utf-8")
            rebuilt = package_pet(package, output, force=True)
            self.assertIn("NOTICE.md", rebuilt["entries"])
            self.assertFalse(temporary_archive.exists())

            loaded, atlas = load_package(package)
            atlas.paste((0, 0, 0, 0), (48, 34, 130, 164))
            atlas.save(loaded.spritesheet_path)
            with self.assertRaisesRegex(ValueError, "structural audit"):
                package_pet(package, root / "invalid.codex-pet")

    def test_archive_verifier_rejects_malformed_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = json.dumps({"spritesheetPath": "spritesheet.png"}).encode()
            sprite = b"sprite"

            duplicate = root / "duplicate.codex-pet"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                write_zip(
                    duplicate,
                    [
                        ("pet.json", manifest, None),
                        ("pet.json", manifest, None),
                        ("spritesheet.png", sprite, None),
                    ],
                )
            with self.assertRaisesRegex(ValueError, "unique"):
                verify_archive(duplicate)

            missing = root / "missing.codex-pet"
            write_zip(missing, [("spritesheet.png", sprite, None)])
            with self.assertRaisesRegex(ValueError, "missing pet.json"):
                verify_archive(missing)

            invalid_manifest = root / "invalid-manifest.codex-pet"
            write_zip(invalid_manifest, [("pet.json", b"{", None)])
            with self.assertRaisesRegex(ValueError, "invalid pet.json"):
                verify_archive(invalid_manifest)

            nonobject_manifest = root / "nonobject-manifest.codex-pet"
            write_zip(nonobject_manifest, [("pet.json", b"[]", None)])
            with self.assertRaisesRegex(ValueError, "one JSON object"):
                verify_archive(nonobject_manifest)

            unsafe = root / "unsafe.codex-pet"
            write_zip(
                unsafe,
                [
                    ("../pet.json", manifest, None),
                    ("pet.json", manifest, None),
                    ("spritesheet.png", sprite, None),
                ],
            )
            with self.assertRaisesRegex(ValueError, "unsafe entries"):
                verify_archive(unsafe)

            unsafe_sprite = root / "unsafe-sprite.codex-pet"
            unsafe_manifest = json.dumps({"spritesheetPath": "../sprite.png"}).encode()
            write_zip(unsafe_sprite, [("pet.json", unsafe_manifest, None)])
            with self.assertRaisesRegex(ValueError, "unsafe spritesheetPath"):
                verify_archive(unsafe_sprite)

            unknown = root / "unknown.codex-pet"
            write_zip(
                unknown,
                [
                    ("evil.txt", b"x", None),
                    ("pet.json", manifest, None),
                    ("spritesheet.png", sprite, None),
                ],
            )
            with self.assertRaisesRegex(ValueError, "unexpected entries"):
                verify_archive(unknown)

            wrong_sprite = root / "wrong-sprite.codex-pet"
            wrong_manifest = json.dumps({"spritesheetPath": "spritesheet.webp"}).encode()
            write_zip(
                wrong_sprite,
                [("pet.json", wrong_manifest, None), ("spritesheet.png", sprite, None)],
            )
            with self.assertRaisesRegex(ValueError, "manifest spritesheet"):
                verify_archive(wrong_sprite)

            symlink = root / "symlink.codex-pet"
            write_zip(
                symlink,
                [
                    ("pet.json", manifest, None),
                    ("spritesheet.png", b"target", 0o120777 << 16),
                ],
            )
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify_archive(symlink)

    def test_install_nested_files_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = make_package(root / "pet")
            assets = package / "assets"
            assets.mkdir()
            (package / "spritesheet.png").replace(assets / "atlas.png")
            rewrite_manifest(package, spritesheetPath="assets/atlas.png")
            codex_home = root / "home"
            result = install_package(package, codex_home=codex_home)
            destination = Path(result["destination"])
            self.assertTrue((destination / "assets" / "atlas.png").is_file())

            original_write_text = Path.write_text

            def fail_install_state(path: Path, *args: object, **kwargs: object) -> int:
                if path.name == ".petease-install.json":
                    raise OSError("synthetic state write failure")
                return original_write_text(path, *args, **kwargs)

            with patch.object(Path, "write_text", fail_install_state):
                with self.assertRaisesRegex(OSError, "synthetic"):
                    install_package(package, codex_home=codex_home)
            self.assertTrue((destination / "assets" / "atlas.png").is_file())

    def test_resolve_home_and_invalid_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(resolve_codex_home(root), root.resolve())
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "configured")}):
                self.assertEqual(resolve_codex_home(), (root / "configured").resolve())

            package = make_package(root / "invalid")
            loaded, atlas = load_package(package)
            atlas.paste((0, 0, 0, 0), (48, 34, 130, 164))
            atlas.save(loaded.spritesheet_path)
            with self.assertRaisesRegex(ValueError, "structural audit"):
                install_package(package, codex_home=root / "home")


class CompilerCliAndSarifEdgeTests(unittest.TestCase):
    def test_compiler_force_and_output_guards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_package(root / "source")
            (source / "NOTICE.md").write_text("notice", encoding="utf-8")
            output = root / "reduced"
            compile_reduced_motion(source, output)
            self.assertTrue((output / "NOTICE.md").is_file())
            with self.assertRaises(FileExistsError):
                compile_reduced_motion(source, output)
            compile_reduced_motion(source, output, force=True)

            file_output = root / "file"
            file_output.write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                compile_reduced_motion(source, file_output, force=True)
            with self.assertRaisesRegex(ValueError, "broad filesystem"):
                compile_reduced_motion(source, Path.cwd())

    def test_cli_strict_policy_error_main_module_and_sarif_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            moving = make_package(root / "moving", moving=True)
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["audit", str(moving), "--strict"]), 2)

            policy = root / "policy.json"
            policy.write_text("[]", encoding="utf-8")
            error = StringIO()
            with redirect_stderr(error):
                self.assertEqual(main(["audit", str(moving), "--policy", str(policy)]), 1)
            self.assertIn("one JSON object", error.getvalue())

            report = audit_package(moving)
            sarif = to_sarif(report)
            self.assertGreater(len(sarif["runs"][0]["results"]), 0)
            self.assertGreater(len(sarif["runs"][0]["tool"]["driver"]["rules"]), 0)

            with patch("sys.argv", ["petease", "--version"]):
                with redirect_stdout(StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        runpy.run_module("petease.__main__", run_name="__main__")
            self.assertEqual(caught.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
