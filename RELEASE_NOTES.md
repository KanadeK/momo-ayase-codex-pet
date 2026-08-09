# Momo Ayase Codex Pet + PetEase v0.1.2

This verified patch release contains:

- a complete Codex v2 Momo Ayase fan-made pet;
- a deterministic reduced-motion edition;
- PetEase 0.1.2 for structural and motion audits, HTML/JSON/SARIF reports,
  deterministic reduced-motion compilation, safe installation, and
  reproducible `.codex-pet` packaging;
- byte-reproducible Windows/Linux release archives through canonical ZIP
  metadata, LF text, portable audit roots, and isolated Python build inputs;
- a repository-scoped Git safety override so the tracked-asset release gate
  works in Windows sandbox and shared-drive checkouts while preserving Git
  failure diagnostics;
- checksums, audit evidence, Python wheel and source distribution.

Start with `momo-ayase-v0.1.2.codex-pet` or
`momo-ayase-reduced-v0.1.2.codex-pet`. Verify downloads against
`SHA256SUMS.txt`. This release supersedes v0.1.1 for local release-gate
compatibility in mixed-owner Windows checkouts; the v0.1.1 pet assets remain
valid.

This is an unofficial, non-commercial fan project. Software is MIT licensed;
fan-art terms are in `ASSET_LICENSE.md`.
