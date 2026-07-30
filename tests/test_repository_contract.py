from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class RepositoryContractTests(unittest.TestCase):
    def test_shipped_pet_and_reduced_motion_contract(self) -> None:
        expected = {
            ROOT / "pet": ("momo-ayase", 2),
            ROOT / "pet-reduced-motion": ("momo-ayase-reduced-motion", 2),
        }
        for package, (expected_id, expected_version) in expected.items():
            with self.subTest(package=package.name):
                manifest = json.loads((package / "pet.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["id"], expected_id)
                self.assertEqual(manifest["spriteVersionNumber"], expected_version)
                image_path = package / manifest["spritesheetPath"]
                with Image.open(image_path) as image:
                    self.assertEqual(image.size, (1536, 2288))
                for notice in ("ASSET_LICENSE.md", "FAN_ART_NOTICE.md", "NOTICE.md"):
                    self.assertTrue((package / notice).is_file(), notice)

    def test_public_visual_evidence_exists(self) -> None:
        required = (
            ROOT / "artwork" / "qa" / "contact-sheet.png",
            ROOT / "artwork" / "qa" / "look-directions.png",
            ROOT / "artwork" / "qa" / "direction-blind-validation.json",
            ROOT / "artwork" / "qa" / "direction-semantics.json",
            ROOT / "artwork" / "qa" / "look-continuity.json",
            ROOT / "artwork" / "qa" / "validation.json",
        )
        for path in required:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())

    def test_jumping_preserves_scale_and_vertical_arc(self) -> None:
        with Image.open(ROOT / "pet" / "spritesheet.webp") as opened:
            atlas = opened.convert("RGBA")
        cells = [
            atlas.crop((column * 192, 4 * 208, (column + 1) * 192, 5 * 208))
            for column in range(5)
        ]
        bounds = [cell.getbbox() for cell in cells]
        self.assertTrue(all(bound is not None for bound in bounds))
        visible = [bound for bound in bounds if bound is not None]
        widths = [right - left for left, _top, right, _bottom in visible]
        bottoms = [bottom for _left, _top, _right, bottom in visible]
        self.assertLessEqual(max(widths) - min(widths), 12)
        self.assertLessEqual(abs(bottoms[0] - bottoms[4]), 2)
        self.assertLessEqual(bottoms[2], min(bottoms[1], bottoms[3]) - 35)

    def test_local_markdown_links_resolve(self) -> None:
        markdown_files = list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md"))
        for document in markdown_files:
            text = document.read_text(encoding="utf-8")
            for raw_target in LINK.findall(text):
                target = raw_target.strip().strip("<>")
                if (
                    not target
                    or target.startswith("#")
                    or target.startswith(("http://", "https://", "mailto:"))
                ):
                    continue
                relative = target.split("#", 1)[0]
                with self.subTest(document=document.name, target=relative):
                    self.assertTrue((document.parent / relative).resolve().exists())


if __name__ == "__main__":
    unittest.main()
