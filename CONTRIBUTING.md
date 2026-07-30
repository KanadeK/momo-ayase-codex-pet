# Contributing

Issues and focused pull requests are welcome for PetEase, documentation, tests,
and original compatibility fixtures.

Do not submit official DANDADAN images, traced frames, logos, ripped game/anime
assets, or artwork you cannot lawfully contribute. New fan-art changes must
state their provenance and remain outside the MIT code license.

## Development

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m unittest discover -v
python -m coverage run -m unittest discover
python -m coverage report
python -m ruff check .
python scripts/release_check.py
```

Add a regression test for every bug fix. Preserve stable finding codes and CLI
exit codes unless the change is explicitly documented as breaking.

Commits must be your own work. Do not add fabricated authors, automated
co-author trailers, or contributor identities.
