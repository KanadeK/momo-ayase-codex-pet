# Accessibility method

PetEase is an engineering risk screen for small looping sprites. It does not
diagnose a medical condition and does not certify WCAG compliance.

## Default thresholds

| Metric | Default warning | Meaning |
| --- | ---: | --- |
| Mean pixel delta | 0.24 | Normalized RGBA change across the whole cell |
| Changed-area ratio | 0.38 | Cell area whose visual difference is at least 32/255 |
| Luminance delta | 0.18 | Mean grayscale change after compositing on mid-gray |
| Centroid shift | 18 px | Bounding-box center movement |
| Opaque-area delta | 0.24 | Relative silhouette-area change |

Every row also checks edge contact, blank used cells, non-empty unused cells,
and non-zero RGB hidden under alpha zero.

## Policy file

```json
{
  "thresholds": {
    "mean_pixel_delta_warning": 0.2,
    "changed_area_ratio_warning": 0.3,
    "luminance_delta_warning": 0.14,
    "centroid_shift_px_warning": 14,
    "area_delta_ratio_warning": 0.2,
    "edge_contact_error": 0,
    "transparent_rgb_error": 0
  }
}
```

Run it with:

```bash
petease audit pet --policy examples/strict-policy.json --strict
```

Warnings identify review targets. Human review still decides whether an
animation is comfortable, semantically readable, and appropriate in context.
The bundled reduced-motion edition removes continuous standard-row motion
without deleting the 16 look states.
