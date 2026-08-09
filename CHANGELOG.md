# Changelog

All notable changes are recorded here.

## 0.1.2 — 2026-08-08

- Make the tracked-asset release check work in Windows sandbox and shared-drive
  checkouts by scoping Git's `safe.directory` override to the exact repository.
- Preserve Git command diagnostics in the release-gate JSON instead of
  returning an unexplained empty forbidden-file list.
- Add regression coverage for both the scoped Git invocation and its failure
  report.

## 0.1.1 — 2026-07-31

- Make `.codex-pet`, bundle ZIP, wheel, sdist, and reports byte-reproducible
  across Windows and Linux.
- Isolate Python distribution builds to an explicit source whitelist so
  ignored local directories cannot influence package discovery.
- Add regression tests for ZIP creator metadata, line endings, wheel records,
  tar ownership, permissions, and timestamps.
- Replace machine-specific release and Pages audit roots with portable paths.

## 0.1.0 — 2026-07-31

- Add complete Momo Ayase Codex v2 pet with nine animation states and sixteen
  look directions.
- Add PetEase structural and motion audit with JSON, HTML, and SARIF output.
- Add deterministic reduced-motion compiler with SHA-256 provenance.
- Add staged installer with dry run, checksum verification, backup, and
  rollback.
- Add deterministic `.codex-pet` packaging and verification.
- Add cross-platform CI, security scan, static preview, release automation,
  tests, example policy, acceptance commands, and repair procedures.
