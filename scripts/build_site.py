from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from petease.audit import audit_package  # noqa: E402
from petease.model import __version__  # noqa: E402
from petease.report import write_json_report  # noqa: E402


def main() -> int:
    destination = ROOT / "_site"
    if destination.exists():
        resolved = destination.resolve()
        if resolved.parent != ROOT.resolve():
            raise RuntimeError(f"Refusing unsafe site clean target: {resolved}")
        shutil.rmtree(destination)
    shutil.copytree(ROOT / "site", destination)
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "pet" / "spritesheet.webp", destination / "spritesheet.webp")
    shutil.copy2(ROOT / "pet" / "spritesheet.webp", assets / "momo.webp")
    shutil.copy2(
        ROOT / "pet-reduced-motion" / "spritesheet.webp",
        assets / "momo-reduced.webp",
    )
    report = audit_package(ROOT / "pet")
    reduced = audit_package(ROOT / "pet-reduced-motion")
    report["package"]["root"] = "pet"
    reduced["package"]["root"] = "pet-reduced-motion"
    write_json_report(report, assets / "audit.json")
    write_json_report(reduced, assets / "audit-reduced.json")
    summary = {
        "normal": report["summary"],
        "reduced": reduced["summary"],
        "version": __version__,
    }
    (assets / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"ok": True, "output": str(destination)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
