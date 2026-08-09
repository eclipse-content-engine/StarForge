from __future__ import annotations

import sys
from pathlib import Path


def verify_bundle(bundle: Path) -> tuple[list[Path], list[Path]]:
    required = (
        bundle / "StarForge.exe",
        bundle / "starforge-cli.exe",
        bundle / "LICENSE",
        bundle / "README.md",
        bundle / "docs" / "QUICKSTART.md",
        bundle / "docs" / "CLI.md",
        bundle / "docs" / "TROUBLESHOOTING.md",
    )
    missing = [path for path in required if not path.is_file()]
    prohibited = {".esm", ".esp", ".esl", ".ba2", ".biom"}
    leaked = [path for path in bundle.rglob("*") if path.is_file() and path.suffix.casefold() in prohibited]
    return missing, leaked


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_release.py BUNDLE_DIRECTORY", file=sys.stderr)
        return 2
    bundle = Path(sys.argv[1])
    missing, leaked = verify_bundle(bundle)
    if missing:
        print("Missing release files:\n" + "\n".join(map(str, missing)), file=sys.stderr)
        return 1
    if leaked:
        print(
            "Proprietary or generated data found in release:\n" + "\n".join(map(str, leaked)),
            file=sys.stderr,
        )
        return 1
    print(f"Release bundle verified: {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
