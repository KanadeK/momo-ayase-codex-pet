from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atlas import load_package, sha256_file
from .audit import audit_package


def resolve_codex_home(value: str | Path | None = None) -> Path:
    if value is not None:
        return Path(value).expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def install_package(
    package_dir: str | Path,
    *,
    codex_home: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    package, _ = load_package(package_dir)
    report = audit_package(package.root)
    if not report["summary"]["ok"]:
        raise ValueError("Refusing to install a package with structural audit errors")

    root = resolve_codex_home(codex_home)
    pets_dir = root / "pets"
    destination = pets_dir / package.manifest["id"]
    if pets_dir.exists() and pets_dir.is_symlink():
        raise ValueError("Refusing to install through a symlinked pets directory")
    if destination.exists() and destination.is_symlink():
        raise ValueError("Refusing to replace a symlinked pet destination")
    plan = {
        "ok": True,
        "dry_run": dry_run,
        "package_id": package.manifest["id"],
        "source": str(package.root),
        "destination": str(destination),
        "source_sha256": package.image_sha256,
        "backup": None,
    }
    if dry_run:
        return plan

    pets_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{package.manifest['id']}.installing-", dir=pets_dir))
    backup: Path | None = None
    installed_staging = False
    try:
        for source in package.root.rglob("*"):
            if source.is_symlink():
                raise ValueError(
                    f"Symlinks are not allowed in pet packages: {source.relative_to(package.root)}"
                )
            relative = source.relative_to(package.root)
            target = staging / relative
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        staged_package, _ = load_package(staging)
        if staged_package.image_sha256 != package.image_sha256:
            raise OSError("Staged spritesheet checksum does not match the source")

        if destination.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = pets_dir / f".{package.manifest['id']}.backup-{stamp}"
            if backup.exists():
                raise FileExistsError(f"Backup already exists: {backup}")
            destination.replace(backup)
            plan["backup"] = str(backup)
        staging.replace(destination)
        installed_staging = True
        state = {
            "schema_version": 1,
            "installed_from": str(package.root),
            "spritesheet_sha256": sha256_file(destination / package.manifest["spritesheetPath"]),
            "backup": str(backup) if backup else None,
        }
        (destination / ".petease-install.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return plan
    except Exception:
        if installed_staging and destination.exists():
            shutil.rmtree(destination)
        if backup is not None and backup.exists() and not destination.exists():
            backup.replace(destination)
        if staging.exists():
            shutil.rmtree(staging)
        raise
