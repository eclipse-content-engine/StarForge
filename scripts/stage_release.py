from __future__ import annotations

import shutil
import sys
from pathlib import Path

RELEASE_FILES = (
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "docs/QUICKSTART.md",
    "docs/CLI.md",
    "docs/TROUBLESHOOTING.md",
    "docs/SUPPORTED_OPERATIONS.md",
)


def stage_release(bundle: Path, repository: Path) -> None:
    for relative in RELEASE_FILES:
        source = repository / relative
        destination = bundle / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: stage_release.py BUNDLE_DIRECTORY", file=sys.stderr)
        return 2
    repository = Path(__file__).resolve().parent.parent
    stage_release(Path(sys.argv[1]), repository)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
