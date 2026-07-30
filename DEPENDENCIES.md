# Dependency inventory

PetEase is a small Python package with one runtime dependency:

| Scope | Package | Declared range | Purpose | License |
| --- | --- | --- | --- | --- |
| Runtime | [Pillow](https://pypi.org/project/pillow/) | `>=10.0` | Lossless atlas decoding, metrics, and encoding | HPND |
| Development | [build](https://pypi.org/project/build/) | `>=1.2` | Wheel and source-distribution builds | MIT |
| Development | [coverage](https://pypi.org/project/coverage/) | `>=7.6` | Branch-aware test coverage | Apache-2.0 |
| Development | [Ruff](https://pypi.org/project/ruff/) | `>=0.9` | Static linting | MIT |
| Build | [setuptools](https://pypi.org/project/setuptools/) | `>=80` | Locked Python build backend | MIT |
| Build | [wheel](https://pypi.org/project/wheel/) | `>=0.45` | Locked wheel format support | MIT |

The authoritative dependency declarations are in
[`pyproject.toml`](pyproject.toml); [`uv.lock`](uv.lock) records resolved files
and hashes for reproducible CI and local verification. Release wheels contain
PetEase source and metadata; they do not vendor these third-party projects.
Codex pet archives contain only the manifest, spritesheet, provenance when
applicable, and the fan-art/legal notices.
