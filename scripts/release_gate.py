from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from petease.archive import package_pet, verify_archive  # noqa: E402
from petease.atlas import load_package  # noqa: E402
from petease.audit import audit_package  # noqa: E402
from petease.compile import compile_reduced_motion  # noqa: E402
from petease.install import install_package  # noqa: E402


def run_command(arguments: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "ok": completed.returncode == 0,
        "command": arguments,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def tracked_asset_check() -> dict[str, Any]:
    result = run_command(["git", "ls-files"])
    tracked = result["stdout"].splitlines() if result["ok"] else []
    forbidden = [
        name
        for name in tracked
        if name.startswith("artwork/private-reference/") or name.startswith("artwork/hatch-run/")
    ]
    return {"ok": result["ok"] and not forbidden, "forbidden": forbidden}


def gate() -> dict[str, Any]:
    normal = ROOT / "pet"
    committed_reduced = ROOT / "pet-reduced-motion"
    normal_report = audit_package(normal)
    reduced_report = audit_package(committed_reduced)
    coverage_erase = run_command([sys.executable, "-m", "coverage", "erase"])
    checks: dict[str, Any] = {
        "ruff": run_command([sys.executable, "-m", "ruff", "check", "."]),
        "coverage_erase": coverage_erase,
        "unit_tests": run_command(
            [sys.executable, "-m", "coverage", "run", "-m", "unittest", "discover", "-v"]
        ),
        "compileall": run_command([sys.executable, "-m", "compileall", "-q", "src", "scripts"]),
        "normal_pet": normal_report["summary"],
        "reduced_pet": reduced_report["summary"],
        "tracked_assets": tracked_asset_check(),
    }
    checks["coverage"] = run_command([sys.executable, "-m", "coverage", "report", "-m"])

    with tempfile.TemporaryDirectory(prefix="petease-release-gate-") as temporary:
        scratch = Path(temporary)
        compiled = scratch / "compiled"
        provenance = compile_reduced_motion(normal, compiled)
        committed_package, _ = load_package(committed_reduced)
        compiled_package, _ = load_package(compiled)
        checks["reduced_reproducible"] = {
            "ok": committed_package.image_sha256 == compiled_package.image_sha256,
            "committed_sha256": committed_package.image_sha256,
            "compiled_sha256": compiled_package.image_sha256,
            "provenance": provenance,
        }

        first_archive = scratch / "first.codex-pet"
        second_archive = scratch / "second.codex-pet"
        first = package_pet(normal, first_archive)
        time.sleep(1.1)
        second = package_pet(normal, second_archive)
        checks["archive_reproducible"] = {
            "ok": first_archive.read_bytes() == second_archive.read_bytes(),
            "first_sha256": first["sha256"],
            "second_sha256": second["sha256"],
            "verification": verify_archive(first_archive),
        }

        codex_home = scratch / "codex-home"
        dry_run = install_package(normal, codex_home=codex_home, dry_run=True)
        first_install = install_package(normal, codex_home=codex_home)
        second_install = install_package(normal, codex_home=codex_home)
        checks["transactional_install"] = {
            "ok": (
                dry_run["dry_run"]
                and Path(first_install["destination"]).is_dir()
                and second_install["backup"] is not None
                and Path(second_install["backup"]).is_dir()
            ),
            "dry_run": dry_run,
            "first": first_install,
            "second": second_install,
        }

    booleans = [
        checks["ruff"]["ok"],
        checks["coverage_erase"]["ok"],
        checks["unit_tests"]["ok"],
        checks["coverage"]["ok"],
        checks["compileall"]["ok"],
        checks["normal_pet"]["ok"],
        checks["reduced_pet"]["ok"],
        checks["reduced_pet"]["accessible_motion"],
        checks["tracked_assets"]["ok"],
        checks["reduced_reproducible"]["ok"],
        checks["archive_reproducible"]["ok"],
        checks["transactional_install"]["ok"],
    ]
    return {
        "schema_version": 1,
        "ok": all(booleans),
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH", "1767225600"),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete local release acceptance gate.")
    parser.add_argument("--json", dest="json_path")
    arguments = parser.parse_args()
    try:
        report = gate()
    except Exception as exc:  # noqa: BLE001
        report = {
            "schema_version": 1,
            "ok": False,
            "fatal": {"type": type(exc).__name__, "message": str(exc)},
        }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.json_path:
        destination = Path(arguments.json_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
