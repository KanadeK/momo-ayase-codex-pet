from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.release_gate import ROOT, tracked_asset_check


class ReleaseGateTests(unittest.TestCase):
    def test_tracked_asset_check_scopes_git_safety_to_repository(self) -> None:
        completed = {
            "ok": True,
            "command": [],
            "returncode": 0,
            "stdout": "pet/pet.json\nREADME.md\n",
            "stderr": "",
        }

        with patch("scripts.release_gate.run_command", return_value=completed) as run:
            report = tracked_asset_check()

        run.assert_called_once_with(
            ["git", "-c", f"safe.directory={ROOT.resolve().as_posix()}", "ls-files"]
        )
        self.assertTrue(report["ok"])
        self.assertEqual(report["forbidden"], [])

    def test_tracked_asset_check_preserves_git_failure_details(self) -> None:
        completed = {
            "ok": False,
            "command": ["git", "ls-files"],
            "returncode": 128,
            "stdout": "",
            "stderr": "fatal: unable to read index",
        }

        with patch("scripts.release_gate.run_command", return_value=completed):
            report = tracked_asset_check()

        self.assertFalse(report["ok"])
        self.assertEqual(report["returncode"], 128)
        self.assertEqual(report["stderr"], "fatal: unable to read index")


if __name__ == "__main__":
    unittest.main()
