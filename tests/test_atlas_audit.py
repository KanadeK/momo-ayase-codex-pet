from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from petease.atlas import PetPackageError, get_cell, load_package, transparent_rgb_residue
from petease.audit import audit_package, pair_metrics, safe_audit_package
from petease.model import ATLAS_HEIGHT, ATLAS_WIDTH, AuditPolicy

from .helpers import make_package


class AtlasAuditTests(unittest.TestCase):
    def test_valid_package_has_expected_cell_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = make_package(Path(temporary) / "pet")
            report = audit_package(package)
            self.assertTrue(report["summary"]["ok"])
            self.assertEqual(report["summary"]["errors"], 0)
            self.assertEqual(report["summary"]["used_cells"], 73)
            self.assertEqual(report["summary"]["unused_cells"], 14)
            self.assertEqual(report["summary"]["optional_cells"], 1)
            self.assertEqual(report["summary"]["populated_optional_cells"], 0)
            self.assertEqual(report["package"]["dimensions"], [ATLAS_WIDTH, ATLAS_HEIGHT])

    def test_optional_neutral_cell_is_allowed_and_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_package(Path(temporary) / "pet")
            package, atlas = load_package(root)
            atlas.paste((180, 40, 90, 255), (6 * 192 + 48, 34, 6 * 192 + 130, 164))
            atlas.save(package.spritesheet_path)
            report = audit_package(root)
            self.assertTrue(report["summary"]["ok"])
            self.assertEqual(report["summary"]["populated_optional_cells"], 1)

    def test_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_package(Path(temporary) / "pet")
            manifest = json.loads((root / "pet.json").read_text(encoding="utf-8"))
            manifest["spritesheetPath"] = "../spritesheet.png"
            (root / "pet.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(PetPackageError, "inside the package"):
                load_package(root)

    def test_wrong_size_and_malformed_manifest_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pet"
            root.mkdir()
            (root / "pet.json").write_text("{broken", encoding="utf-8")
            report = safe_audit_package(root)
            self.assertFalse(report["summary"]["ok"])
            self.assertEqual(report["issues"][0]["code"], "package-invalid")
            self.assertIn("repair", report["issues"][0])

            Image.new("RGBA", (10, 10)).save(root / "tiny.png")
            (root / "pet.json").write_text(
                json.dumps(
                    {
                        "id": "tiny",
                        "displayName": "Tiny",
                        "description": "Wrong size",
                        "spriteVersionNumber": 2,
                        "spritesheetPath": "tiny.png",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(PetPackageError, "1536x2288"):
                load_package(root)

    def test_blank_used_nonempty_unused_edge_and_residue_are_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_package(Path(temporary) / "pet")
            package, atlas = load_package(root)
            atlas.paste((0, 0, 0, 0), (48, 34, 130, 164))
            atlas.paste((255, 0, 0, 255), (7 * 192, 0, 7 * 192 + 10, 10))
            atlas.paste((255, 255, 255, 255), (192, 34, 198, 50))
            atlas.putpixel((1500, 2200), (7, 8, 9, 0))
            atlas.save(package.spritesheet_path)
            report = audit_package(root)
            codes = {issue["code"] for issue in report["issues"]}
            self.assertIn("blank-used-cell", codes)
            self.assertIn("nonempty-unused-cell", codes)
            self.assertIn("edge-contact", codes)
            self.assertIn("transparent-rgb-residue", codes)
            self.assertGreater(transparent_rgb_residue(atlas), 0)

    def test_motion_warnings_and_strict_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_package(Path(temporary) / "pet", moving=True)
            report = audit_package(root, AuditPolicy(centroid_shift_px_warning=5))
            codes = {issue["code"] for issue in report["issues"]}
            self.assertIn("motion-centroid-shift-px", codes)
            self.assertFalse(report["summary"]["accessible_motion"])

    def test_pair_metrics_and_policy_validation(self) -> None:
        first = Image.new("RGBA", (192, 208), (0, 0, 0, 0))
        second = first.copy()
        second.paste((255, 255, 255, 255), (70, 70, 100, 100))
        metrics = pair_metrics(first, second)
        self.assertGreater(metrics["mean_pixel_delta"], 0)
        self.assertGreater(metrics["area_delta_ratio"], 0)
        self.assertEqual(get_cell(Image.new("RGBA", (1536, 2288)), 0, 0).size, (192, 208))
        with self.assertRaisesRegex(ValueError, "Unknown policy"):
            AuditPolicy.from_dict({"thresholds": {"surprise": 1}})
        with self.assertRaisesRegex(ValueError, "one JSON object"):
            AuditPolicy.from_dict({"thresholds": []})
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            AuditPolicy.from_dict({"mean_pixel_delta_warning": "high"})
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            AuditPolicy.from_dict({"changed_area_ratio_warning": 1.5})
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            AuditPolicy.from_dict({"edge_contact_error": 0.5})


if __name__ == "__main__":
    unittest.main()
