"""Fail when tracked repository content violates the publication policy."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_SUFFIXES = {".ba2", ".biom", ".esm", ".esl", ".esp"}
MAX_TRACKED_SIZE = 10 * 1024 * 1024
ABSOLUTE_USER_PATH = re.compile(rb"[A-Za-z]:\\Users\\[^\\\r\n]+")


def publication_candidates() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def main() -> int:
    failures: list[str] = []
    candidates = publication_candidates()
    for path in candidates:
        if path.suffix.lower() in PROHIBITED_SUFFIXES:
            failures.append(f"prohibited game-data extension: {path.relative_to(ROOT)}")
        if path.stat().st_size > MAX_TRACKED_SIZE:
            failures.append(f"tracked file exceeds 10 MiB: {path.relative_to(ROOT)}")
        if path.suffix.lower() in {".md", ".py", ".toml", ".yaml", ".yml", ".txt"}:
            match = ABSOLUTE_USER_PATH.search(path.read_bytes())
            if match:
                failures.append(f"absolute user path in {path.relative_to(ROOT)}")
    if failures:
        print("Publication audit failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Publication audit passed for {len(candidates)} candidate files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
