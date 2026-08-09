from __future__ import annotations

from pathlib import Path

from scripts.stage_release import RELEASE_FILES, stage_release
from scripts.verify_release import verify_bundle


def _complete_bundle(root: Path) -> Path:
    bundle = root / "StarForge"
    for relative in (
        "StarForge.exe",
        "starforge-cli.exe",
        "LICENSE",
        "README.md",
        "docs/QUICKSTART.md",
        "docs/CLI.md",
        "docs/TROUBLESHOOTING.md",
    ):
        path = bundle / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    return bundle


def test_release_verifier_accepts_complete_public_bundle(tmp_path: Path) -> None:
    bundle = _complete_bundle(tmp_path)

    assert verify_bundle(bundle) == ([], [])


def test_release_verifier_rejects_missing_and_proprietary_files(tmp_path: Path) -> None:
    bundle = _complete_bundle(tmp_path)
    (bundle / "StarForge.exe").unlink()
    leaked = bundle / "private.ba2"
    leaked.touch()

    missing, proprietary = verify_bundle(bundle)

    assert missing == [bundle / "StarForge.exe"]
    assert proprietary == [leaked]


def test_release_staging_copies_public_documents(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    bundle = tmp_path / "bundle"
    for relative in RELEASE_FILES:
        source = repository / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(relative, encoding="utf-8")

    stage_release(bundle, repository)

    for relative in RELEASE_FILES:
        assert (bundle / relative).read_text(encoding="utf-8") == relative
