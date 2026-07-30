from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

__version__ = "0.1.1"

CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_COLUMNS = 8
ATLAS_ROWS = 11
ATLAS_WIDTH = CELL_WIDTH * ATLAS_COLUMNS
ATLAS_HEIGHT = CELL_HEIGHT * ATLAS_ROWS


@dataclass(frozen=True)
class RowSpec:
    index: int
    state: str
    frames: int
    durations_ms: tuple[int, ...]


ROW_SPECS: tuple[RowSpec, ...] = (
    RowSpec(0, "idle", 6, (280, 110, 110, 140, 140, 320)),
    RowSpec(1, "running-right", 8, (120, 120, 120, 120, 120, 120, 120, 220)),
    RowSpec(2, "running-left", 8, (120, 120, 120, 120, 120, 120, 120, 220)),
    RowSpec(3, "waving", 4, (140, 140, 140, 280)),
    RowSpec(4, "jumping", 5, (140, 140, 140, 140, 280)),
    RowSpec(5, "failed", 8, (140, 140, 140, 140, 140, 140, 140, 240)),
    RowSpec(6, "waiting", 6, (150, 150, 150, 150, 150, 260)),
    RowSpec(7, "running", 6, (120, 120, 120, 120, 120, 220)),
    RowSpec(8, "review", 6, (150, 150, 150, 150, 150, 280)),
    RowSpec(9, "look-a", 8, (0, 0, 0, 0, 0, 0, 0, 0)),
    RowSpec(10, "look-b", 8, (0, 0, 0, 0, 0, 0, 0, 0)),
)

# Codex v2 reserves row 0, column 6 for a neutral/default look pose. It is
# allowed but not required, so it is neither a required animation frame nor an
# unused cell.
OPTIONAL_CELLS: frozenset[tuple[int, int]] = frozenset({(0, 6)})


@dataclass(frozen=True)
class AuditPolicy:
    mean_pixel_delta_warning: float = 0.24
    changed_area_ratio_warning: float = 0.38
    luminance_delta_warning: float = 0.18
    centroid_shift_px_warning: float = 18.0
    area_delta_ratio_warning: float = 0.24
    edge_contact_error: int = 0
    transparent_rgb_error: int = 0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AuditPolicy:
        thresholds = value.get("thresholds", value)
        if not isinstance(thresholds, dict):
            raise ValueError("Policy thresholds must contain one JSON object")
        allowed = {field for field in cls.__dataclass_fields__}
        unknown = set(thresholds) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown policy threshold(s): {names}")
        count_fields = {"edge_contact_error", "transparent_rgb_error"}
        ratio_fields = {
            "mean_pixel_delta_warning",
            "changed_area_ratio_warning",
            "luminance_delta_warning",
            "area_delta_ratio_warning",
        }
        normalized: dict[str, int | float] = {}
        for key, raw in thresholds.items():
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError(f"Policy threshold {key} must be numeric")
            if raw < 0:
                raise ValueError(f"Policy threshold {key} must be non-negative")
            if key in count_fields:
                if not isinstance(raw, int):
                    raise ValueError(f"Policy threshold {key} must be an integer")
                normalized[key] = raw
            else:
                if key in ratio_fields and raw > 1:
                    raise ValueError(f"Policy threshold {key} must be between 0 and 1")
                normalized[key] = float(raw)
        return cls(**normalized)


@dataclass(frozen=True)
class PetPackage:
    root: Path
    manifest_path: Path
    spritesheet_path: Path
    manifest: dict[str, Any]
    image_sha256: str
