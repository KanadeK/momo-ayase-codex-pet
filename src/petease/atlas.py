from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from PIL import Image

from .model import (
    ATLAS_HEIGHT,
    ATLAS_WIDTH,
    CELL_HEIGHT,
    CELL_WIDTH,
    ROW_SPECS,
    PetPackage,
)


class PetPackageError(ValueError):
    """Raised when a package violates the Codex v2 manifest contract."""


PET_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise PetPackageError("spritesheetPath must be a non-empty string")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PetPackageError("spritesheetPath must stay inside the package")
    return path


def load_package(package_dir: str | Path) -> tuple[PetPackage, Image.Image]:
    root = Path(package_dir).expanduser().resolve()
    if not root.is_dir():
        raise PetPackageError(f"Package directory does not exist: {root}")

    manifest_path = root / "pet.json"
    if not manifest_path.is_file():
        raise PetPackageError(f"Missing pet.json: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PetPackageError(f"Invalid pet.json: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PetPackageError("pet.json must contain one JSON object")

    required = ("id", "displayName", "description", "spriteVersionNumber", "spritesheetPath")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise PetPackageError(f"pet.json is missing: {', '.join(missing)}")
    if manifest["spriteVersionNumber"] != 2:
        raise PetPackageError("spriteVersionNumber must be 2")
    for key in ("id", "displayName", "description"):
        if not isinstance(manifest[key], str) or not manifest[key].strip():
            raise PetPackageError(f"{key} must be a non-empty string")
    if not PET_ID_PATTERN.fullmatch(manifest["id"]):
        raise PetPackageError(
            "id must contain 1-64 lowercase ASCII letters, digits, dots, underscores, or hyphens"
        )

    relative = _safe_relative_path(manifest["spritesheetPath"])
    spritesheet_path = root.joinpath(*relative.parts).resolve()
    try:
        spritesheet_path.relative_to(root)
    except ValueError as exc:
        raise PetPackageError("spritesheetPath escapes the package") from exc
    if not spritesheet_path.is_file():
        raise PetPackageError(f"Missing spritesheet: {spritesheet_path}")

    try:
        with Image.open(spritesheet_path) as opened:
            opened.load()
            image = opened.convert("RGBA")
    except (OSError, ValueError) as exc:
        raise PetPackageError(f"Unreadable spritesheet: {exc}") from exc

    if image.size != (ATLAS_WIDTH, ATLAS_HEIGHT):
        raise PetPackageError(
            f"Spritesheet must be {ATLAS_WIDTH}x{ATLAS_HEIGHT}, got {image.width}x{image.height}"
        )

    package = PetPackage(
        root=root,
        manifest_path=manifest_path,
        spritesheet_path=spritesheet_path,
        manifest=manifest,
        image_sha256=sha256_file(spritesheet_path),
    )
    return package, image


def get_cell(image: Image.Image, row: int, column: int) -> Image.Image:
    left = column * CELL_WIDTH
    top = row * CELL_HEIGHT
    return image.crop((left, top, left + CELL_WIDTH, top + CELL_HEIGHT))


def iter_cells(image: Image.Image) -> Iterator[tuple[int, int, bool, Image.Image]]:
    for spec in ROW_SPECS:
        for column in range(8):
            yield spec.index, column, column < spec.frames, get_cell(image, spec.index, column)


def transparent_rgb_residue(image: Image.Image) -> int:
    count = 0
    pixels = getattr(image, "get_flattened_data", image.getdata)()
    for red, green, blue, alpha in pixels:
        if alpha == 0 and (red or green or blue):
            count += 1
    return count


def save_webp(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "WEBP", lossless=True, method=6, exact=True)
