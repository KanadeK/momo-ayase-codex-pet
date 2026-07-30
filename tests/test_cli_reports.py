from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from petease.audit import audit_package
from petease.cli import main
from petease.report import write_html_report, write_json_report
from petease.sarif import to_sarif, write_sarif_report

from .helpers import make_package


class CliReportTests(unittest.TestCase):
    def test_report_writers_escape_html_and_emit_sarif(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = make_package(root / "pet")
            manifest_path = package / "pet.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["displayName"] = "<Momo & test>"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = audit_package(package)

            json_path = root / "report.json"
            html_path = root / "report.html"
            sarif_path = root / "report.sarif"
            write_json_report(report, json_path)
            write_html_report(report, html_path)
            write_sarif_report(report, sarif_path)
            self.assertTrue(json.loads(json_path.read_text(encoding="utf-8"))["summary"]["ok"])
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("&lt;Momo &amp; test&gt;", html)
            self.assertNotIn("<Momo & test>", html)
            sarif = json.loads(sarif_path.read_text(encoding="utf-8"))
            self.assertEqual(sarif["version"], "2.1.0")
            self.assertEqual(to_sarif(report)["runs"][0]["results"], [])

    def test_cli_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = make_package(root / "pet")
            reduced = root / "reduced"
            archive = root / "pet.codex-pet"
            report = root / "report.json"
            html = root / "report.html"
            sarif = root / "report.sarif"
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "audit",
                            str(package),
                            "--json-out",
                            str(report),
                            "--html-out",
                            str(html),
                            "--sarif-out",
                            str(sarif),
                            "--strict",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(["compile-reduced", str(package), str(reduced)]),
                    0,
                )
                self.assertEqual(main(["package", str(package), str(archive)]), 0)
                self.assertEqual(main(["verify-archive", str(archive)]), 0)
                self.assertEqual(
                    main(
                        ["install", str(package), "--codex-home", str(root / "home"), "--dry-run"]
                    ),
                    0,
                )
                self.assertEqual(main(["doctor", str(package)]), 0)
            self.assertIn('"ok": true', output.getvalue().lower())

    def test_cli_failure_is_actionable(self) -> None:
        error = StringIO()
        with redirect_stderr(error):
            exit_code = main(["audit", "does-not-exist"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(error.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
