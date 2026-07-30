# Acceptance

Run from the repository root with Python 3.10 or later.

For the same resolved dependencies as CI:

```bash
uv sync --locked --extra dev
```

## One-command release gate

```bash
python scripts/release_gate.py --json build/release-gate.json
```

Success writes JSON with `"ok": true` and exits with code `0`. The gate performs:

1. source and test discovery checks;
2. unit tests;
3. structural and motion audit of the shipped pet;
4. deterministic reduced-motion compilation and strict re-audit;
5. isolated dry-run and real installation;
6. deterministic archive builds in separate directories;
7. byte-for-byte and SHA-256 comparison;
8. archive safety verification;
9. tracked-file checks that reject private generation references;
10. comparison of the committed reduced atlas with a fresh compilation.

## Manual commands

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -v
python -m coverage run -m unittest discover
python -m coverage report
python -m ruff check .
```

```bash
petease audit pet \
  --json-out build/audit.json \
  --html-out build/audit.html \
  --sarif-out build/audit.sarif \
  --strict
```

```bash
petease compile-reduced pet build/momo-reduced \
  --json-out build/reduced-audit.json
petease audit build/momo-reduced --strict
```

```bash
petease install pet --codex-home build/codex-home --dry-run
petease install pet --codex-home build/codex-home
```

```bash
petease package pet dist/momo-ayase.codex-pet
petease verify-archive dist/momo-ayase.codex-pet
```

## Expected release files

- `momo-ayase-v0.1.1.codex-pet`
- `momo-ayase-reduced-v0.1.1.codex-pet`
- `momo-ayase-codex-pet-v0.1.1.zip`
- `petease-0.1.1-py3-none-any.whl`
- `petease-0.1.1.tar.gz`
- `audit.json`
- `audit.html`
- `audit.sarif`
- `DEPENDENCIES.md`
- `SHA256SUMS.txt`

## Public-release verification

Local success is not public delivery. After pushing the tag:

1. Open the repository anonymously and confirm it is public.
2. Confirm CI, security scan, Pages, and release workflows are green.
3. Download every release asset from GitHub.
4. Compare downloaded hashes with `SHA256SUMS.txt`.
5. Compare the downloaded `SHA256SUMS.txt` with a clean local release build;
   Windows and Linux must produce the same asset hashes.
6. Confirm the tag and release both point to the intended commit.
7. Inspect `git shortlog -sne HEAD` and the GitHub contributors page.
8. Search the commit history for `Co-authored-by` trailers.
9. Open the published preview and exercise row, frame, speed, and
   reduced-motion controls.

## Visual acceptance

The final artwork is accepted only when:

- every standard row has exactly its contract frame count;
- every frame is 192×208 and has transparent padding;
- identity, outfit, earrings, hair, scale, and baseline remain stable;
- right and left motion read correctly;
- sixteen look directions progress clockwise with no duplicate or reversed
  cardinal directions;
- three independent blind reviewers pass both standard-row and look-direction
  comparisons;
- final contact sheet and animated previews are inspected at native and 2×
  scale.
