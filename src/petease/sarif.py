from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_sarif(report: dict[str, Any]) -> dict[str, Any]:
    issues = report.get("issues", [])
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for issue in issues:
        code = str(issue["code"])
        rules.setdefault(
            code,
            {
                "id": code,
                "name": code.replace("-", " ").title(),
                "shortDescription": {"text": str(issue["message"])},
                "help": {"text": str(issue.get("repair", ""))},
            },
        )
        location: dict[str, Any] = {
            "physicalLocation": {
                "artifactLocation": {
                    "uri": str(report.get("package", {}).get("spritesheet", "pet.json"))
                }
            }
        }
        if "row" in issue:
            location["logicalLocations"] = [
                {
                    "name": f"row-{issue['row']}",
                    "fullyQualifiedName": (
                        f"row-{issue['row']}.column-"
                        f"{issue.get('column', issue.get('from_frame', 0))}"
                    ),
                }
            ]
        results.append(
            {
                "ruleId": code,
                "level": "error" if issue["severity"] == "error" else "warning",
                "message": {"text": str(issue["message"])},
                "locations": [location],
            }
        )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PetEase",
                        "informationUri": "https://github.com/KanadeK/momo-ayase-codex-pet",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def write_sarif_report(report: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(to_sarif(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
