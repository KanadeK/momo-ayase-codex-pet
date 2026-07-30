from __future__ import annotations

import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .atlas import load_package, sha256_file
from .audit import audit_package

ARCHIVE_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
OPTIONAL_NAMES = {
    "ASSET_LICENSE.md",
    "FAN_ART_NOTICE.md",
    "NOTICE.md",
    "petease-provenance.json",
}


def package_pet(
    package_dir: str | Path,
    output_path: str | Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    package, _ = load_package(package_dir)
    report = audit_package(package.root)
    if not report["summary"]["ok"]:
        raise ValueError("Refusing to package a pet with structural audit errors")

    destination = Path(output_path).expanduser().resolve()
    if destination.suffix != ".codex-pet":
        raise ValueError("Output filename must end in .codex-pet")
    if destination.exists() and not force:
        raise FileExistsError(f"Output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    sprite_name = PurePosixPath(package.manifest["spritesheetPath"]).as_posix()
    if PurePosixPath(sprite_name).suffix.lower() not in {".png", ".webp"}:
        raise ValueError("Packaged spritesheet must use .png or .webp")
    lexical_sprite = package.root.joinpath(*PurePosixPath(sprite_name).parts)
    cursor = package.root
    for part in lexical_sprite.relative_to(package.root).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError(f"Symlinks are not allowed in pet packages: {sprite_name}")

    selected = [
        (package.manifest_path, "pet.json"),
        (package.spritesheet_path, sprite_name),
    ]
    for candidate in sorted(package.root.iterdir(), key=lambda item: item.name):
        if candidate.is_symlink():
            raise ValueError(f"Symlinks are not allowed in pet packages: {candidate.name}")
        if candidate.is_file() and candidate.name in OPTIONAL_NAMES:
            selected.append((candidate, candidate.name))

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for source, name in sorted(selected, key=lambda item: item[1]):
                info = zipfile.ZipInfo(name, date_time=ARCHIVE_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, source.read_bytes())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "schema_version": 1,
        "id": package.manifest["id"],
        "archive": str(destination),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "entries": sorted(name for _, name in selected),
    }


def verify_archive(path: str | Path) -> dict[str, Any]:
    archive_path = Path(path).expanduser().resolve()
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError("Archive entries must be unique and lexically sorted")
        if "pet.json" not in names:
            raise ValueError("Archive is missing pet.json")
        unsafe = [
            name
            for name in names
            if "\\" in name
            or PurePosixPath(name).is_absolute()
            or any(part in {"", ".", ".."} for part in PurePosixPath(name).parts)
        ]
        if unsafe:
            raise ValueError(f"Archive has unsafe entries: {', '.join(unsafe)}")
        try:
            manifest = json.loads(archive.read("pet.json"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Archive has invalid pet.json: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ValueError("Archive pet.json must contain one JSON object")
        spritesheet = manifest.get("spritesheetPath")
        if not isinstance(spritesheet, str) or not spritesheet:
            raise ValueError("Archive manifest has an invalid spritesheetPath")
        sprite_path = PurePosixPath(spritesheet)
        if (
            "\\" in spritesheet
            or sprite_path.is_absolute()
            or any(part in {"", ".", ".."} for part in sprite_path.parts)
            or sprite_path.suffix.lower() not in {".png", ".webp"}
        ):
            raise ValueError("Archive manifest has an unsafe spritesheetPath")
        if spritesheet not in names:
            raise ValueError("Archive is missing the manifest spritesheet")
        unknown = sorted(set(names) - (OPTIONAL_NAMES | {"pet.json", spritesheet}))
        if unknown:
            raise ValueError(f"Archive has unexpected entries: {', '.join(unknown)}")
        oversized = [
            info.filename for info in archive.infolist() if info.file_size > 32 * 1024 * 1024
        ]
        if oversized:
            raise ValueError(f"Archive entries exceed 32 MiB: {', '.join(oversized)}")
        for info in archive.infolist():
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError(f"Archive contains a symlink: {info.filename}")
    return {
        "ok": True,
        "archive": str(archive_path),
        "sha256": sha256_file(archive_path),
        "entries": names,
    }
