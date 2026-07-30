# Release procedure

1. Run `python scripts/release_gate.py --json build/release-gate.json`.
2. Confirm the gate reports `ok: true`.
3. Inspect `git status`, author and committer identities, and
   `git shortlog -sne HEAD`.
4. Confirm no commit contains a `Co-authored-by` trailer.
5. Commit the exact source state and push `main`.
6. Wait for CI and Pages to pass on that commit.
7. Tag the verified commit with the intended `vX.Y.Z` version and push it.
8. Build release assets from the tagged checkout with
   `python scripts/build_release.py --force --output dist/release`.
9. Create the GitHub Release and upload every file in `dist/release/`.
10. Download the public assets into a clean directory and verify
    `SHA256SUMS.txt`, both `.codex-pet` archives, wheel metadata, and archive
    reproducibility.
11. Confirm the public contributor list contains only intended authors and the
    Pages lab loads from the release commit.

Do not move a tag silently. If an asset or commit is wrong, document the
correction and publish a new patch version.
