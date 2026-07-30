from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json_report(report: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_html_report(report: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    package = report.get("package", {})
    summary = report["summary"]
    rows = []
    for row in report.get("rows", []):
        pairs = row.get("pairs", [])
        max_motion = max((pair["mean_pixel_delta"] for pair in pairs), default=0)
        max_changed = max((pair["changed_area_ratio"] for pair in pairs), default=0)
        max_luminance = max((pair["luminance_delta"] for pair in pairs), default=0)
        max_shift = max((pair["centroid_shift_px"] for pair in pairs), default=0)
        rows.append(
            "<tr>"
            f"<th scope='row'>{html.escape(row['state'])}</th>"
            f"<td>{row['frames']}</td>"
            f"<td>{max_motion:.3f}</td>"
            f"<td>{max_changed:.3f}</td>"
            f"<td>{max_luminance:.3f}</td>"
            f"<td>{max_shift:.2f}px</td>"
            f"<td>{row['edge_contact_pixels']}</td>"
            "</tr>"
        )
    issues = (
        "".join(
            "<li>"
            f"<strong>{html.escape(issue['severity'])}</strong> "
            f"{html.escape(issue['code'])}: {html.escape(issue['message'])}"
            "</li>"
            for issue in report.get("issues", [])
        )
        or "<li>No issues recorded.</li>"
    )
    status = "Pass" if summary["ok"] else "Fail"
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PetEase report: {html.escape(str(package.get("display_name", "pet")))}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
    body {{ max-width: 76rem; margin: 0 auto; padding: 2rem; line-height: 1.5; }}
    h1 {{ max-width: 22ch; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
      gap: 1rem; margin: 2rem 0; }}
    .summary div {{ border: 1px solid currentColor; border-radius: .75rem; padding: 1rem; }}
    .summary strong {{ display: block; font-size: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; overflow-x: auto; display: block; }}
    th, td {{ padding: .7rem; border-bottom: 1px solid color-mix(in srgb, currentColor 24%,
      transparent); text-align: right; white-space: nowrap; }}
    th:first-child, td:first-child {{ text-align: left; }}
    a:focus-visible {{ outline: 3px solid #d03b72; outline-offset: 3px; }}
  </style>
</head>
<body>
  <main>
    <p>PetEase deterministic audit</p>
    <h1>{html.escape(str(package.get("display_name", "Unknown pet")))}</h1>
    <div class="summary">
      <div><span>Structural status</span><strong>{status}</strong></div>
      <div><span>Errors</span><strong>{summary["errors"]}</strong></div>
      <div><span>Motion warnings</span><strong>{summary["warnings"]}</strong></div>
      <div><span>Used cells</span><strong>{summary["used_cells"]}</strong></div>
      <div><span>Optional cells</span><strong>{summary.get("populated_optional_cells", 0)}
        / {summary.get("optional_cells", 0)}</strong></div>
    </div>
    <h2>Animation rows</h2>
    <table>
      <thead><tr><th>State</th><th>Frames</th><th>Pixel delta</th><th>Changed area</th>
        <th>Luminance delta</th><th>Centroid shift</th><th>Edge pixels</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    <h2>Findings</h2>
    <ul>{issues}</ul>
  </main>
</body>
</html>
"""
    destination.write_text(document, encoding="utf-8")
