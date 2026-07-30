from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from petease.archive import ARCHIVE_TIMESTAMP, package_pet  # noqa: E402
from petease.audit import audit_package  # noqa: E402
from petease.compile import compile_reduced_motion  # noqa: E402
from petease.model import __version__  # noqa: E402
from petease.report import write_html_report, write_json_report  # noqa: E402
from petease.sarif import write_sarif_report  # noqa: E402

MARKER = ".petease-release-dir"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_output(output: Path, force: bool) -> None:
    output = output.resolve()
    forbidden = {ROOT.resolve(), ROOT.parent.resolve(), Path.home().resolve(), Path(output.anchor)}
    if output in forbidden:
        raise ValueError("Refusing to use a broad directory as release output")
    if output.exists() and any(output.iterdir()):
        if not force:
            raise FileExistsError(f"Release output is not empty: {output}")
        if not (output / MARKER).is_file():
            raise ValueError("Refusing to replace an output not created by this release builder")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / MARKER).write_text("PetEase release output\n", encoding="utf-8", newline="\n")


def add_file(archive: zipfile.ZipFile, source: Path, name: str) -> None:
    info = zipfile.ZipInfo(name, date_time=ARCHIVE_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, source.read_bytes())


def build_bundle(output: Path) -> Path:
    destination = output / f"momo-ayase-codex-pet-v{__version__}.zip"
    prefix = f"momo-ayase-codex-pet-v{__version__}"
    files = [
        ROOT / "ASSET_LICENSE.md",
        ROOT / "DEPENDENCIES.md",
        ROOT / "LICENSE",
        ROOT / "NOTICE.md",
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / "docs" / "ACCEPTANCE.md",
        ROOT / "docs" / "REPAIR.md",
    ]
    files.extend(sorted((ROOT / "pet").iterdir(), key=lambda item: item.name))
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(files, key=lambda item: item.as_posix()):
            if not source.is_file() or source.is_symlink():
                raise ValueError(f"Unexpected release bundle input: {source}")
            relative = source.relative_to(ROOT).as_posix()
            add_file(archive, source, f"{prefix}/{relative}")
    return destination


def build_python_distributions(output: Path) -> None:
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = "1767225600"
    subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output)],
        cwd=ROOT,
        env=environment,
        check=True,
    )


def write_checksums(output: Path) -> Path:
    assets = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name not in {MARKER, "SHA256SUMS.txt"}
    )
    destination = output / "SHA256SUMS.txt"
    destination.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in assets),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def build(output: Path, force: bool = False) -> list[Path]:
    prepare_output(output, force)
    report = audit_package(ROOT / "pet")
    if not report["summary"]["ok"]:
        raise ValueError("Cannot release a pet with structural audit errors")
    write_json_report(report, output / "audit.json")
    write_html_report(report, output / "audit.html")
    write_sarif_report(report, output / "audit.sarif")

    with tempfile.TemporaryDirectory(prefix="petease-release-") as temporary:
        reduced = Path(temporary) / "momo-ayase-reduced"
        compile_reduced_motion(ROOT / "pet", reduced)
        package_pet(
            reduced,
            output / f"momo-ayase-reduced-v{__version__}.codex-pet",
        )

    package_pet(
        ROOT / "pet",
        output / f"momo-ayase-v{__version__}.codex-pet",
    )
    build_bundle(output)
    build_python_distributions(output)
    shutil.copy2(ROOT / "DEPENDENCIES.md", output / "DEPENDENCIES.md")
    write_checksums(output)
    return sorted(path for path in output.iterdir() if path.is_file() and path.name != MARKER)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build every PetEase GitHub release asset.")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        assets = build(args.output, force=args.force)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"release build: FAIL: {exc}", file=sys.stderr)
        return 1
    for asset in assets:
        print(f"{sha256(asset)}  {asset.name}")
    print("release build: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
