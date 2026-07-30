from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

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
SOURCE_DATE_EPOCH = 1767225600
TEXT_SUFFIXES = {
    ".cfg",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_NAMES = {"LICENSE", "METADATA", "PKG-INFO", "RECORD", "WHEEL"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_text(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def is_text_name(name: str) -> bool:
    path = PurePosixPath(name)
    return path.name in TEXT_NAMES or path.suffix.lower() in TEXT_SUFFIXES


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=ARCHIVE_TIMESTAMP)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


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
    archive.writestr(zip_info(name), source.read_bytes())


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


def canonicalize_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise ValueError(f"Wheel contains duplicate entries: {path.name}")
        entries = {
            name: canonical_text(source.read(name)) if is_text_name(name) else source.read(name)
            for name in names
        }

    record_names = [name for name in entries if name.endswith(".dist-info/RECORD")]
    if len(record_names) != 1:
        raise ValueError(f"Wheel must contain exactly one RECORD: {path.name}")
    record_name = record_names[0]
    entries.pop(record_name)

    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name in sorted(entries):
        data = entries[name]
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        writer.writerow((name, f"sha256={digest.decode('ascii')}", len(data)))
    writer.writerow((record_name, "", ""))
    entries[record_name] = record.getvalue().encode("utf-8")

    temporary = path.with_name(path.name + ".canonical")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as destination:
            for name in sorted(entries):
                destination.writestr(zip_info(name), entries[name])
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def canonicalize_sdist(path: Path) -> None:
    members: list[tuple[str, bool, bytes]] = []
    with tarfile.open(path, "r:gz") as source:
        for member in source.getmembers():
            if member.isdir():
                members.append((member.name, True, b""))
                continue
            if not member.isfile():
                raise ValueError(f"Unsupported sdist member type: {member.name}")
            extracted = source.extractfile(member)
            if extracted is None:
                raise ValueError(f"Could not read sdist member: {member.name}")
            data = extracted.read()
            if is_text_name(member.name):
                data = canonical_text(data)
            members.append((member.name, False, data))

    temporary = path.with_name(path.name + ".canonical")
    if temporary.exists():
        temporary.unlink()
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=9,
                fileobj=raw,
                mtime=SOURCE_DATE_EPOCH,
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed,
                    mode="w",
                    format=tarfile.USTAR_FORMAT,
                ) as destination:
                    for name, is_directory, data in sorted(members):
                        info = tarfile.TarInfo(name)
                        info.mtime = SOURCE_DATE_EPOCH
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        if is_directory:
                            info.type = tarfile.DIRTYPE
                            info.mode = 0o755
                            destination.addfile(info)
                        else:
                            info.mode = 0o644
                            info.size = len(data)
                            destination.addfile(info, io.BytesIO(data))
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def python_distribution_sources() -> list[Path]:
    sources = [
        ROOT / "LICENSE",
        ROOT / "NOTICE.md",
        ROOT / "README.md",
        ROOT / "pyproject.toml",
    ]
    sources.extend(sorted((ROOT / "src" / "petease").glob("*.py")))
    sources.extend(sorted((ROOT / "tests").glob("*.py")))
    return sources


def build_python_distributions(output: Path) -> None:
    output = output.resolve()
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = str(SOURCE_DATE_EPOCH)
    environment["PYTHONUTF8"] = "1"
    with tempfile.TemporaryDirectory(prefix="petease-python-dist-") as temporary:
        staging = Path(temporary) / "source"
        staging.mkdir()
        for source in python_distribution_sources():
            if not source.is_file() or source.is_symlink():
                raise ValueError(f"Unexpected Python distribution input: {source}")
            destination = staging / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            if is_text_name(source.name):
                data = canonical_text(data)
            destination.write_bytes(data)
            os.utime(destination, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))

        subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output)],
            cwd=staging,
            env=environment,
            check=True,
        )

    wheels = list(output.glob(f"petease-{__version__}-*.whl"))
    sdists = list(output.glob(f"petease-{__version__}.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Python build did not produce exactly one wheel and one sdist")
    canonicalize_wheel(wheels[0])
    canonicalize_sdist(sdists[0])


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
    report["package"]["root"] = "pet"
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
