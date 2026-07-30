from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from petease.model import ATLAS_HEIGHT, ATLAS_WIDTH, CELL_HEIGHT, CELL_WIDTH, ROW_SPECS


def make_package(
    root: Path,
    *,
    image_format: str = "PNG",
    image_name: str | None = None,
    moving: bool = False,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    for spec in ROW_SPECS:
        for column in range(spec.frames):
            offset = 36 if moving and spec.index == 0 and column % 2 else 0
            left = column * CELL_WIDTH + 48 + offset
            top = spec.index * CELL_HEIGHT + 34
            right = min(column * CELL_WIDTH + CELL_WIDTH - 20, left + 82)
            bottom = top + 130
            color = (
                180 + spec.index * 3,
                40 + column * 4,
                90 + (spec.index + column) * 2,
                255,
            )
            atlas.paste(color, (left, top, right, bottom))

    selected_name = image_name or (
        "spritesheet.webp" if image_format == "WEBP" else "spritesheet.png"
    )
    atlas.save(root / selected_name, image_format, lossless=True, exact=True)
    manifest = {
        "id": "fixture-pet",
        "displayName": "Fixture Pet",
        "description": "Synthetic deterministic test fixture.",
        "spriteVersionNumber": 2,
        "spritesheetPath": selected_name,
    }
    (root / "pet.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return root
