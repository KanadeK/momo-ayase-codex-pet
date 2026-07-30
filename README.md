# Momo Ayase for Codex with PetEase

[![CI](https://github.com/KanadeK/momo-ayase-codex-pet/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/momo-ayase-codex-pet/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/KanadeK/momo-ayase-codex-pet)](https://github.com/KanadeK/momo-ayase-codex-pet/releases)
[![License: MIT code](https://img.shields.io/badge/code-MIT-2f855a.svg)](LICENSE)

An unofficial, hand-QA'd **Momo Ayase** fan pet for Codex, plus **PetEase**:
an accessibility-focused toolkit that audits real Codex v2 sprite atlases, detects
motion hazards, compiles deterministic reduced-motion editions, installs with
backup and rollback, and builds reproducible release archives.

This is not a reskin around an empty page. The repository ships one complete
1536×2288, 8×11 Codex v2 atlas with nine animated states, sixteen look
directions, a tested Python CLI, machine-readable reports, CI, sample policy,
and reproducible packages.

> Unofficial fan project. Momo Ayase and DANDADAN belong to their respective
> rights holders. The software is MIT-licensed; artwork has separate terms in
> [ASSET_LICENSE.md](ASSET_LICENSE.md).

![Momo Ayase waving in the Codex v2 pet format](artwork/qa/previews/waving.gif)

[简体中文](README.zh-CN.md) · [Acceptance](docs/ACCEPTANCE.md) ·
[Repair guide](docs/REPAIR.md) · [Architecture](docs/ARCHITECTURE.md)

## What ships

- `pet/`: installable Momo Ayase Codex v2 pet, with transparent lossless WebP.
- `petease audit`: validates manifest safety, atlas dimensions, required/unused
  cells, transparent RGB residue, cell-edge clipping, motion jumps, luminance
  changes, centroid shifts, and scale changes.
- `petease compile-reduced`: replaces each animated state with a deterministic
  representative still while preserving all sixteen look-direction cells.
- `petease install`: refuses structurally broken pets, performs a staged copy,
  verifies the sprite checksum, backs up an existing install, and rolls back on
  failure.
- `petease package` / `verify-archive`: creates and verifies deterministic
  `.codex-pet` transport archives.
- JSON, HTML, and SARIF output for people, CI, and GitHub code scanning.
- Tests with synthetic valid and malicious packages; no copyrighted fixture
  images are needed to exercise the tool.
- Committed [visual QA evidence](artwork/qa/), including contact sheets,
  direction semantics, continuity metrics, and three-reviewer blind validation.

## Install the pet

Download `momo-ayase-codex-pet-v0.1.1.zip` and
`petease-0.1.1-py3-none-any.whl` from the same Release, extract the pet bundle,
then:

```powershell
py -m pip install .\petease-0.1.1-py3-none-any.whl
petease install .\pet --dry-run
petease install .\pet
```

Restart Codex, open **Settings → Pets**, and select **Momo Ayase**. PetEase
installs into the selected `CODEX_HOME` (or `~/.codex`) and preserves an
existing pet as a timestamped sibling backup.

To install into an isolated directory first:

```powershell
petease install .\pet --codex-home .\.acceptance-codex --dry-run
petease install .\pet --codex-home .\.acceptance-codex
```

## Audit any Codex v2 pet

PetEase is character-agnostic. Point it at any directory containing `pet.json`
and its v2 atlas:

```bash
petease audit pet \
  --json-out build/audit.json \
  --html-out build/audit.html \
  --sarif-out build/audit.sarif \
  --strict
```

Exit codes are stable:

- `0`: structurally valid; in strict mode, no motion warnings.
- `1`: invalid package or structural error.
- `2`: structurally valid, but strict motion policy reported warnings.

Tune warning thresholds without weakening structural checks:

```bash
petease audit pet --policy examples/policy.json --strict
```

## Compile a reduced-motion edition

```bash
petease compile-reduced pet build/momo-reduced \
  --json-out build/reduced-audit.json
petease audit build/momo-reduced --strict
```

The compiler chooses a deterministic medoid pose for each animated state
(`idle` intentionally uses frame zero), repeats it across that state's used
cells, preserves look-direction cells, records source/output SHA-256 values,
and writes `petease-provenance.json`.

It will not overwrite an arbitrary non-empty directory, even with `--force`.

## Build a reproducible transport archive

```bash
petease package pet dist/momo-ayase.codex-pet
petease verify-archive dist/momo-ayase.codex-pet
```

Entries are lexically sorted, timestamps and permissions are normalized, unsafe
paths and symlinks are rejected, and the command prints the archive SHA-256.

## Develop and verify

Python 3.10+ is supported.

To reproduce the locked CI environment:

```bash
uv sync --locked --extra dev
uv run python scripts/release_gate.py --json build/release-gate.json
```

The equivalent standard-library/pip workflow is:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m unittest discover -v
python -m coverage run -m unittest discover
python -m coverage report
python -m ruff check .
python scripts/release_gate.py --json build/release-gate.json
```

The exact public-release acceptance sequence and expected artifacts are in
[docs/ACCEPTANCE.md](docs/ACCEPTANCE.md). If anything fails, use the
code-indexed procedures in [docs/REPAIR.md](docs/REPAIR.md).

## Why Momo, and why this tool?

The character is not invented for this repository. Momo is a lead character in
[DANDADAN's official character roster](https://anime-dandadan.com/en/character/).
Before implementation, repository and code searches across the main Codex pet
lists found no existing Momo Ayase pet, while several other popular candidates
already had implementations.

The tool addresses a separate gap: existing pet repositories mostly validate
layout or preview animation, while PetEase treats motion comfort and safe,
reproducible transformation as first-class build outputs. The research record,
search queries, date, and limits are preserved in
[docs/RESEARCH.md](docs/RESEARCH.md).

Popularity and careful execution can improve discoverability, but no project can
honestly guarantee stars or views.

## Privacy and security

PetEase is offline by default. It does not send telemetry, inspect Codex
conversations, or need network access. Installation is restricted to a single
validated pet ID under the selected Codex home. Package sprite paths cannot be
absolute or escape their directory. See [SECURITY.md](SECURITY.md).

## Credits and rights

PetEase code and original documentation: © 2026 KanadeK, MIT.

Momo Ayase and DANDADAN are owned by their respective rights holders. Generated
fan art is not covered by the MIT license. No official reference image is
committed, packaged, or published. See [NOTICE.md](NOTICE.md) and
[ASSET_LICENSE.md](ASSET_LICENSE.md).
