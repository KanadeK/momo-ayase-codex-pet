# Security policy

## Supported versions

Security fixes are provided for the latest release.

## Report privately

Do not open a public issue for a vulnerability that could expose or overwrite
another user's files. Use GitHub's private vulnerability reporting on the
repository Security tab. Include:

- affected PetEase version and operating system;
- exact command and package layout;
- the smallest non-sensitive reproduction;
- expected and observed filesystem targets.

You should receive an acknowledgement within seven days.

## Threat model

PetEase treats every pet package as untrusted local input. Its safety controls
include contained relative sprite paths, no symlink installation, structural
audit before mutation, staged checksum verification, rollback, conservative
force behavior, deterministic archive entries, and archive path validation.

PetEase does not execute code from pet packages, access Codex conversations,
collect telemetry, or make network requests.

No parser can make opening arbitrary untrusted image files risk-free. Keep
Pillow current and run unknown packages with ordinary user privileges in an
isolated directory.
