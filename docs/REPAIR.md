# Failure repair guide

Do not delete an existing Codex pet when diagnosing a failure. Start with a
dry run and an isolated `--codex-home`.

## Finding codes

| Code | Cause | Repair |
| --- | --- | --- |
| `package-invalid` | Missing/invalid JSON, unsafe path, unsupported version, unreadable or wrong-size atlas | Fix the exact loader message; keep the sprite beside `pet.json`; rerun `doctor` |
| `blank-used-cell` | A required frame is empty | Restore or regenerate that row and rebuild the atlas |
| `nonempty-unused-cell` | Pixels exist after a row's declared frame count | Clear that entire 192×208 cell to RGBA `(0,0,0,0)` |
| `edge-contact` | Opaque pixels touch a cell boundary | Re-center or scale the frame with transparent padding |
| `transparent-rgb-residue` | Invisible pixels retain color | Set RGB to zero wherever alpha is zero; save lossless |
| `motion-mean-pixel-delta` | Abrupt total visual change | Add an in-between pose or reduce pose/background changes |
| `motion-changed-area-ratio` | Too much of the cell changes at once | Reduce simultaneous motion or compile the reduced-motion edition |
| `motion-luminance-delta` | Abrupt brightness change | Stabilize shading and highlight intensity |
| `motion-centroid-shift-px` | Character jumps within its cell | Align baseline and center between flagged frames |
| `motion-area-delta-ratio` | Character scale changes | Normalize visible bounds without stretching identity |

## Audit fails but the image looks correct

```bash
petease doctor pet
petease audit pet --json-out build/audit.json
```

Inspect `issues`, including row and column. Confirm the atlas is genuinely
1536×2288 rather than an image viewer's scaled display. Do not turn structural
errors into warnings by changing policy; policy only controls motion
thresholds.

## Strict audit exits with 2

The package is structurally valid, but motion warnings crossed the selected
policy. Open the HTML report, identify the maximum pair, and decide whether to:

1. repair the animation;
2. document a deliberate high-energy motion;
3. use a project-specific threshold in `examples/policy.json`.

Never increase a threshold only to make CI green without inspecting the pair.

## Reduced-motion compile refuses the output

- If the directory exists, choose a new output.
- `--force` only replaces an empty directory or one containing
  `petease-provenance.json`.
- Source and output must be different.
- Broad locations such as the filesystem root, home, or current repository
  root are rejected.

Recovery:

```bash
petease compile-reduced pet build/momo-reduced-new
petease audit build/momo-reduced-new --strict
```

## Installation fails

First:

```bash
petease install pet --codex-home build/codex-home --dry-run
```

Common repairs:

- close processes holding files under the target pet directory;
- ensure the selected Codex home is writable;
- remove or replace a symlinked `pets` directory only after confirming where it
  points;
- fix audit errors before retrying.

If failure occurs after an existing install is backed up, PetEase attempts an
automatic rollback. Backups are siblings named
`.momo-ayase.backup-YYYYMMDDTHHMMSSffffffZ`. Verify the destination checksum before
manually restoring anything.

## Pet installs but does not appear

1. Confirm the destination is `<active CODEX_HOME>/pets/momo-ayase`.
2. Confirm it contains `pet.json` and the exact `spritesheetPath`.
3. Restart Codex completely.
4. Open Settings → Pets and refresh/select the pet.
5. Test with a newly created isolated Codex home to separate package problems
   from local app state.

Runtime support can differ across Codex builds and operating systems. A clean
PetEase audit proves package conformance, not that every Codex build implements
every v2 behavior.

## Archive hashes differ

Run two builds in separate, empty directories:

```bash
petease package pet build-a/momo.codex-pet
petease package pet build-b/momo.codex-pet
petease verify-archive build-a/momo.codex-pet
petease verify-archive build-b/momo.codex-pet
```

If bytes differ, compare entry names and source file bytes. Do not regenerate
the atlas between builds. The release gate treats any mismatch as a failure.

## CI-only failure

Reproduce the failing operating-system/Python combination shown in the job
matrix. Download the JSON/SARIF artifacts. If the failure is path-related,
verify that the test uses `pathlib` and does not assume `/` or a drive letter.

After repair, rerun the full release gate rather than only the previously
failing test.

## `uv` cache fails on Windows with OS error 183

This usually means another process left a conflicting entry in uv's shared
user cache. Keep the repository reproducible by switching only this checkout
to a local cache, then retry the locked install:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD ".uv-cache"
uv sync --locked --extra dev
```

Do not delete the shared cache as a first response. If the local cache also
fails, close concurrent uv processes, remove only this repository's
`.uv-cache`, recreate it, and rerun the full release gate.
