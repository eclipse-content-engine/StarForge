from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path

import pytest
from conftest import PluginFixtures

from starforge.application import ApplicationError, RecoveryStore, StarForgeApplication, Workspace
from starforge.core.biom import PlanetaryDataArchive


def test_unicode_and_deep_paths_round_trip(tmp_path: Path, plugin_fixtures: PluginFixtures) -> None:
    deep = tmp_path / "星系工房"
    for index in range(4):
        deep /= f"long-project-segment-{index}"
    deep.mkdir(parents=True)
    source = deep / "源 master.esm"
    destination = deep / "目的地 plugin.esp"
    output = deep / "検証済み output.esp"
    shutil.copy2(plugin_fixtures.source, source)
    shutil.copy2(plugin_fixtures.destination, destination)

    workspace = Workspace.open(source, destination)
    workspace.set_star_system_id(workspace.view.stars[0].form_id, workspace.allocate_system_id())
    workspace.export(output)

    assert StarForgeApplication().validate(output).data["valid"] is True


def test_read_only_inputs_remain_unchanged(tmp_path: Path, plugin_fixtures: PluginFixtures) -> None:
    source = tmp_path / "readonly-source.esm"
    destination = tmp_path / "readonly-destination.esp"
    output = tmp_path / "readonly-output.esp"
    shutil.copy2(plugin_fixtures.source, source)
    shutil.copy2(plugin_fixtures.destination, destination)
    before = (source.read_bytes(), destination.read_bytes())
    source.chmod(stat.S_IREAD)
    destination.chmod(stat.S_IREAD)
    try:
        workspace = Workspace.open(source, destination)
        workspace.set_star_system_id(workspace.view.stars[0].form_id, workspace.allocate_system_id())
        workspace.export(output)
    finally:
        source.chmod(stat.S_IREAD | stat.S_IWRITE)
        destination.chmod(stat.S_IREAD | stat.S_IWRITE)

    assert (source.read_bytes(), destination.read_bytes()) == before
    assert output.is_file()


def test_malformed_plugin_is_blocked_with_plain_language_error(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.esp"
    malformed.write_bytes(b"not a plugin")

    with pytest.raises(ApplicationError) as error:
        StarForgeApplication().inspect(malformed)

    assert error.value.code == "invalid_plugin"
    assert str(error.value)


def test_unknown_or_corrupt_recovery_schema_is_ignored(tmp_path: Path) -> None:
    root = tmp_path / "recovery"
    root.mkdir()
    (root / "recovery-unknown.json").write_text('{"schema_version": 999}', encoding="utf-8")
    (root / "recovery-corrupt.json").write_text("not json", encoding="utf-8")

    assert RecoveryStore(root).latest() is None


def test_recovery_metadata_cannot_claim_or_delete_files_outside_its_store(tmp_path: Path) -> None:
    root = tmp_path / "recovery"
    root.mkdir()
    source = tmp_path / "source.esm"
    external = tmp_path / "keep-me.esp"
    source.write_bytes(b"source")
    external.write_bytes(b"external")
    store = RecoveryStore(root)
    manifest = root / f"recovery-{store.project_key(source, tmp_path / 'destination.esp')}.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_path": str(source),
                "destination_path": str(tmp_path / "destination.esp"),
                "recovery_path": str(external),
                "created_at": "2026-08-08T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    assert store.latest() is None
    store.clear(source, tmp_path / "destination.esp")
    assert external.read_bytes() == b"external"


def test_missing_biome_archive_has_an_actionable_failure(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "Starfield - PlanetData.ba2"

    with pytest.raises(FileNotFoundError, match="Starfield - PlanetData.ba2"):
        PlanetaryDataArchive(missing).extract_biom("Synthetic Prime", "Clone", tmp_path)


def test_failed_mutation_restores_the_pre_command_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    plugin_fixtures: PluginFixtures,
) -> None:
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    star = workspace.view.stars[0]
    original_system_id = star.system_id
    original_method = workspace._session.set_star_system_id

    def mutate_then_fail(form_id: int, system_id: int) -> None:
        original_method(form_id, system_id)
        raise FileNotFoundError("Starfield - PlanetData.ba2 is missing")

    monkeypatch.setattr(workspace._session, "set_star_system_id", mutate_then_fail)

    with pytest.raises(FileNotFoundError, match="Starfield - PlanetData.ba2"):
        workspace.set_star_system_id(star.form_id, workspace.allocate_system_id())

    assert workspace.view.stars[0].system_id == original_system_id
    assert workspace.pending_change_count == 0
    assert not workspace.can_undo


def test_interrupted_publish_preserves_existing_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    plugin_fixtures: PluginFixtures,
) -> None:
    output = tmp_path / "existing.esp"
    sentinel = b"existing validated user output"
    output.write_bytes(sentinel)
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    workspace.set_star_system_id(workspace.view.stars[0].form_id, workspace.allocate_system_id())

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("synthetic interrupted replace")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(ApplicationError) as error:
        workspace.export(output, overwrite=True)

    assert error.value.code == "output_write_failed"
    assert output.read_bytes() == sentinel
    assert not list(tmp_path.glob(".*.tmp.esp"))
