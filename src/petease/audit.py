from __future__ import annotations

import math
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

from .atlas import PetPackageError, get_cell, load_package, transparent_rgb_residue
from .model import OPTIONAL_CELLS, ROW_SPECS, AuditPolicy, __version__

REPAIRS: dict[str, str] = {
    "blank-used-cell": "Regenerate or restore the required frame, then rebuild the atlas.",
    "edge-contact": "Re-center or scale the frame so every opaque pixel has transparent padding.",
    "motion-area-delta-ratio": "Normalize character scale across the flagged frame pair.",
    "motion-changed-area-ratio": (
        "Reduce the area that changes at once, or compile a reduced-motion variant."
    ),
    "motion-centroid-shift-px": (
        "Align the character baseline and center across the flagged frame pair."
    ),
    "motion-luminance-delta": "Reduce abrupt brightness changes between the flagged frames.",
    "motion-mean-pixel-delta": "Add an in-between pose or reduce the visual jump between frames.",
    "nonempty-unused-cell": "Clear the unused cell to fully transparent RGBA pixels.",
    "package-invalid": (
        "Run `petease doctor <package>` and fix the manifest, path, or atlas size shown."
    ),
    "transparent-rgb-residue": (
        "Zero RGB channels wherever alpha is zero, then save lossless PNG or lossless WebP."
    ),
}


def _nonzero_alpha_count(cell: Image.Image) -> int:
    histogram = cell.getchannel("A").histogram()
    return sum(histogram[1:])


def _edge_alpha_count(cell: Image.Image) -> int:
    alpha = cell.getchannel("A")
    width, height = alpha.size
    edges = (
        alpha.crop((0, 0, width, 1)),
        alpha.crop((0, height - 1, width, height)),
        alpha.crop((0, 1, 1, height - 1)),
        alpha.crop((width - 1, 1, width, height - 1)),
    )
    return sum(sum(piece.histogram()[1:]) for piece in edges)


def _alpha_bbox_stats(
    cell: Image.Image,
) -> tuple[tuple[int, int, int, int] | None, float, float, int]:
    alpha = cell.getchannel("A")
    bbox = alpha.getbbox()
    area = _nonzero_alpha_count(cell)
    if bbox is None:
        return None, 0.0, 0.0, area
    return bbox, (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2, area


def _interior_transparent_pixels(cell: Image.Image) -> int:
    alpha = cell.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return 0
    cropped = alpha.crop(bbox)
    width, height = cropped.size
    raw = cropped.tobytes()
    seen = bytearray(width * height)
    queue: deque[int] = deque()

    def add_if_clear(x: int, y: int) -> None:
        index = y * width + x
        if raw[index] == 0 and not seen[index]:
            seen[index] = 1
            queue.append(index)

    for x in range(width):
        add_if_clear(x, 0)
        add_if_clear(x, height - 1)
    for y in range(height):
        add_if_clear(0, y)
        add_if_clear(width - 1, y)

    while queue:
        index = queue.popleft()
        x = index % width
        y = index // width
        if x:
            add_if_clear(x - 1, y)
        if x + 1 < width:
            add_if_clear(x + 1, y)
        if y:
            add_if_clear(x, y - 1)
        if y + 1 < height:
            add_if_clear(x, y + 1)

    return sum(1 for index, value in enumerate(raw) if value == 0 and not seen[index])


def _composite_gray(cell: Image.Image) -> Image.Image:
    background = Image.new("RGBA", cell.size, (127, 127, 127, 255))
    return Image.alpha_composite(background, cell).convert("L")


def pair_metrics(first: Image.Image, second: Image.Image) -> dict[str, float]:
    rgba_diff = ImageChops.difference(first, second)
    mean_channels = ImageStat.Stat(rgba_diff).mean
    mean_pixel_delta = sum(mean_channels) / (len(mean_channels) * 255)
    changed = rgba_diff.convert("L").point(lambda value: 255 if value >= 32 else 0)
    changed_area_ratio = sum(changed.histogram()[1:]) / (first.width * first.height)

    gray_diff = ImageChops.difference(_composite_gray(first), _composite_gray(second))
    luminance_delta = ImageStat.Stat(gray_diff).mean[0] / 255

    _, x1, y1, area1 = _alpha_bbox_stats(first)
    _, x2, y2, area2 = _alpha_bbox_stats(second)
    centroid_shift = math.hypot(x2 - x1, y2 - y1)
    area_delta_ratio = abs(area2 - area1) / max(area1, area2, 1)

    return {
        "mean_pixel_delta": round(mean_pixel_delta, 6),
        "changed_area_ratio": round(changed_area_ratio, 6),
        "luminance_delta": round(luminance_delta, 6),
        "centroid_shift_px": round(centroid_shift, 4),
        "area_delta_ratio": round(area_delta_ratio, 6),
    }


def _issue(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    **context: Any,
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "repair": REPAIRS.get(
                code, "Review and repair the flagged frames, then rerun the audit."
            ),
            **context,
        }
    )


def audit_package(
    package_dir: str | Path,
    policy: AuditPolicy | None = None,
) -> dict[str, Any]:
    active_policy = policy or AuditPolicy()
    package, image = load_package(package_dir)
    issues: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    used_cells = 0
    unused_cells = 0
    optional_cells = 0
    populated_optional_cells = 0

    residue = transparent_rgb_residue(image)
    if residue > active_policy.transparent_rgb_error:
        _issue(
            issues,
            "error",
            "transparent-rgb-residue",
            f"{residue} fully transparent pixels retain non-zero RGB values",
            pixels=residue,
        )

    for spec in ROW_SPECS:
        frames = [get_cell(image, spec.index, column) for column in range(spec.frames)]
        row_pairs: list[dict[str, Any]] = []
        row_edge_contacts = 0
        row_holes = 0

        for column in range(8):
            cell = get_cell(image, spec.index, column)
            alpha_count = _nonzero_alpha_count(cell)
            is_optional = (spec.index, column) in OPTIONAL_CELLS
            if column < spec.frames:
                used_cells += 1
                if alpha_count == 0:
                    _issue(
                        issues,
                        "error",
                        "blank-used-cell",
                        f"{spec.state} frame {column} is blank",
                        row=spec.index,
                        column=column,
                    )
                edge_count = _edge_alpha_count(cell)
                row_edge_contacts += edge_count
                if edge_count > active_policy.edge_contact_error:
                    _issue(
                        issues,
                        "error",
                        "edge-contact",
                        f"{spec.state} frame {column} touches its cell boundary",
                        row=spec.index,
                        column=column,
                        pixels=edge_count,
                    )
                row_holes += _interior_transparent_pixels(cell)
            elif is_optional:
                optional_cells += 1
                if alpha_count:
                    populated_optional_cells += 1
                    edge_count = _edge_alpha_count(cell)
                    row_edge_contacts += edge_count
                    if edge_count > active_policy.edge_contact_error:
                        _issue(
                            issues,
                            "error",
                            "edge-contact",
                            f"{spec.state} optional neutral cell touches its boundary",
                            row=spec.index,
                            column=column,
                            pixels=edge_count,
                        )
                    row_holes += _interior_transparent_pixels(cell)
            else:
                unused_cells += 1
                if alpha_count:
                    _issue(
                        issues,
                        "error",
                        "nonempty-unused-cell",
                        f"{spec.state} unused frame {column} is not transparent",
                        row=spec.index,
                        column=column,
                        pixels=alpha_count,
                    )

        if spec.index < 9:
            for index in range(len(frames)):
                metrics = pair_metrics(frames[index], frames[(index + 1) % len(frames)])
                pair = {"from": index, "to": (index + 1) % len(frames), **metrics}
                row_pairs.append(pair)
                checks = (
                    ("mean_pixel_delta", active_policy.mean_pixel_delta_warning),
                    ("changed_area_ratio", active_policy.changed_area_ratio_warning),
                    ("luminance_delta", active_policy.luminance_delta_warning),
                    ("centroid_shift_px", active_policy.centroid_shift_px_warning),
                    ("area_delta_ratio", active_policy.area_delta_ratio_warning),
                )
                for metric, threshold in checks:
                    if metrics[metric] > threshold:
                        _issue(
                            issues,
                            "warning",
                            f"motion-{metric.replace('_', '-')}",
                            (
                                f"{spec.state} frames {index}->{(index + 1) % len(frames)} "
                                f"exceed {metric} policy"
                            ),
                            row=spec.index,
                            from_frame=index,
                            to_frame=(index + 1) % len(frames),
                            value=metrics[metric],
                            threshold=threshold,
                        )

        rows.append(
            {
                "row": spec.index,
                "state": spec.state,
                "frames": spec.frames,
                "edge_contact_pixels": row_edge_contacts,
                "interior_transparent_pixels": row_holes,
                "pairs": row_pairs,
            }
        )

    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    return {
        "schema_version": 1,
        "tool": {"name": "PetEase", "version": __version__},
        "package": {
            "id": package.manifest["id"],
            "display_name": package.manifest["displayName"],
            "root": str(package.root),
            "spritesheet": package.manifest["spritesheetPath"],
            "spritesheet_sha256": package.image_sha256,
            "dimensions": [image.width, image.height],
            "mode": "RGBA",
            "sprite_version_number": package.manifest["spriteVersionNumber"],
        },
        "policy": {
            "mean_pixel_delta_warning": active_policy.mean_pixel_delta_warning,
            "changed_area_ratio_warning": active_policy.changed_area_ratio_warning,
            "luminance_delta_warning": active_policy.luminance_delta_warning,
            "centroid_shift_px_warning": active_policy.centroid_shift_px_warning,
            "area_delta_ratio_warning": active_policy.area_delta_ratio_warning,
            "edge_contact_error": active_policy.edge_contact_error,
            "transparent_rgb_error": active_policy.transparent_rgb_error,
        },
        "summary": {
            "ok": errors == 0,
            "accessible_motion": warnings == 0,
            "errors": errors,
            "warnings": warnings,
            "used_cells": used_cells,
            "unused_cells": unused_cells,
            "optional_cells": optional_cells,
            "populated_optional_cells": populated_optional_cells,
            "transparent_rgb_residue": residue,
        },
        "rows": rows,
        "issues": issues,
    }


def safe_audit_package(
    package_dir: str | Path,
    policy: AuditPolicy | None = None,
) -> dict[str, Any]:
    try:
        return audit_package(package_dir, policy)
    except (PetPackageError, OSError, ValueError) as exc:
        return {
            "schema_version": 1,
            "tool": {"name": "PetEase", "version": __version__},
            "summary": {
                "ok": False,
                "accessible_motion": False,
                "errors": 1,
                "warnings": 0,
                "used_cells": 0,
                "unused_cells": 0,
                "optional_cells": 0,
                "populated_optional_cells": 0,
            },
            "rows": [],
            "issues": [
                {
                    "severity": "error",
                    "code": "package-invalid",
                    "message": str(exc),
                    "repair": REPAIRS["package-invalid"],
                }
            ],
        }
