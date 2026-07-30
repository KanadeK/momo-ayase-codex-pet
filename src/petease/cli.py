from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .archive import package_pet, verify_archive
from .audit import safe_audit_package
from .compile import compile_reduced_motion
from .install import install_package, resolve_codex_home
from .model import AuditPolicy, __version__
from .report import write_html_report, write_json_report
from .sarif import write_sarif_report


def _load_policy(path: str | None) -> AuditPolicy:
    if path is None:
        return AuditPolicy()
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Policy file must contain one JSON object")
    return AuditPolicy.from_dict(value)


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _audit_command(args: argparse.Namespace) -> int:
    report = safe_audit_package(args.package, _load_policy(args.policy))
    if args.json_out:
        write_json_report(report, args.json_out)
    if args.html_out:
        write_html_report(report, args.html_out)
    if args.sarif_out:
        write_sarif_report(report, args.sarif_out)
    _print(report["summary"])
    if not report["summary"]["ok"]:
        return 1
    if args.strict and report["summary"]["warnings"]:
        return 2
    return 0


def _compile_command(args: argparse.Namespace) -> int:
    provenance = compile_reduced_motion(args.package, args.output, force=args.force)
    report = safe_audit_package(args.output, _load_policy(args.policy))
    if args.json_out:
        write_json_report(report, args.json_out)
    _print({"provenance": provenance, "audit": report["summary"]})
    return 0 if report["summary"]["ok"] else 1


def _install_command(args: argparse.Namespace) -> int:
    result = install_package(
        args.package,
        codex_home=args.codex_home,
        dry_run=args.dry_run,
    )
    _print(result)
    return 0


def _doctor_command(args: argparse.Namespace) -> int:
    report = safe_audit_package(args.package, _load_policy(args.policy))
    result = {
        "tool_version": __version__,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "codex_home": str(resolve_codex_home(args.codex_home)),
        "package": report["summary"],
    }
    _print(result)
    return 0 if report["summary"]["ok"] else 1


def _package_command(args: argparse.Namespace) -> int:
    result = package_pet(args.package, args.output, force=args.force)
    _print(result)
    return 0


def _verify_archive_command(args: argparse.Namespace) -> int:
    _print(verify_archive(args.archive))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="petease",
        description="Audit Codex pet motion and compile reduced-motion variants.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit structure and motion metrics.")
    audit.add_argument("package")
    audit.add_argument("--policy")
    audit.add_argument("--json-out")
    audit.add_argument("--html-out")
    audit.add_argument("--sarif-out")
    audit.add_argument("--strict", action="store_true")
    audit.set_defaults(handler=_audit_command)

    compile_parser = subparsers.add_parser(
        "compile-reduced",
        help="Compile a structurally valid reduced-motion pet package.",
    )
    compile_parser.add_argument("package")
    compile_parser.add_argument("output")
    compile_parser.add_argument("--policy")
    compile_parser.add_argument("--json-out")
    compile_parser.add_argument("--force", action="store_true")
    compile_parser.set_defaults(handler=_compile_command)

    install = subparsers.add_parser("install", help="Install with backup and rollback.")
    install.add_argument("package")
    install.add_argument("--codex-home")
    install.add_argument("--dry-run", action="store_true")
    install.set_defaults(handler=_install_command)

    doctor = subparsers.add_parser("doctor", help="Inspect runtime and package health.")
    doctor.add_argument("package")
    doctor.add_argument("--codex-home")
    doctor.add_argument("--policy")
    doctor.set_defaults(handler=_doctor_command)

    package_parser = subparsers.add_parser(
        "package",
        help="Build a deterministic .codex-pet archive after a structural audit.",
    )
    package_parser.add_argument("package")
    package_parser.add_argument("output")
    package_parser.add_argument("--force", action="store_true")
    package_parser.set_defaults(handler=_package_command)

    verify = subparsers.add_parser(
        "verify-archive",
        help="Check archive safety, contents, and checksum.",
    )
    verify.add_argument("archive")
    verify.set_defaults(handler=_verify_archive_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.handler(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"petease: {exc}", file=sys.stderr)
        return 1
