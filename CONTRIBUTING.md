# Contributing to StarForge

Thank you for helping make StarForge safer and easier to use.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Before opening a pull request, run:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy src/starforge
python -m pytest
python scripts/check_publication.py
python -m build
```

## Game-data policy

Never commit or attach Bethesda-owned plugins, archives, extracted assets, or
record payloads. This includes ESM, ESP, ESL, BA2, and BIOM files. Tests must use
fixtures generated from invented values by this repository.

Private compatibility tests may use a local game installation, but must remain
opt-in and must not run in public CI.

## Pull requests

- Keep domain behavior out of the UI layer.
- Add or update tests for behavior changes.
- Preview and validation operations must remain non-mutating.
- Describe format assumptions and compatibility risks explicitly.
- Confirm that `python scripts/check_publication.py` passes.

By contributing, you agree that your contribution is licensed under the MIT
License included with the project.
