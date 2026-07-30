.PHONY: audit build lint release-check test

test:
	python -m unittest discover -v

lint:
	python -m ruff check .

audit:
	petease audit pet --json-out build/audit.json --html-out build/audit.html --sarif-out build/audit.sarif --strict

release-check:
	python scripts/release_gate.py --json build/release-gate.json

build:
	python scripts/build_release.py --force --output dist/release
