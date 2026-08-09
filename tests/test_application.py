from __future__ import annotations

from pathlib import Path

import pytest
from conftest import PluginFixtures

from starforge.application import (
    ApplicationError,
    CancellationToken,
    CloneStarRequest,
    ExitCode,
    OrbitUpdateRequest,
    StarForgeApplication,
)


def _star_request(plugin_fixtures: PluginFixtures) -> CloneStarRequest:
    return CloneStarRequest(
        source_path=plugin_fixtures.source,
        destination_path=plugin_fixtures.destination,
        source_form_id=0x100,
        editor_id="ApplicationCloneStar",
        display_name="Application Clone",
        system_id=0x34567890,
    )


def test_inspect_returns_typed_public_summary(plugin_fixtures: PluginFixtures) -> None:
    result = StarForgeApplication().inspect(plugin_fixtures.destination)

    assert result.operation == "inspect"
    assert result.data["star_count"] == 1
    assert result.data["planet_count"] == 2
    assert result.to_dict()["schema_version"] == 1


def test_clone_preview_is_non_mutating(plugin_fixtures: PluginFixtures) -> None:
    before = plugin_fixtures.destination.read_bytes()
    result = StarForgeApplication().preview_clone_star(_star_request(plugin_fixtures))

    assert result.data["valid"] is True
    assert result.changed is False
    assert plugin_fixtures.destination.read_bytes() == before


def test_apply_clone_writes_atomically_without_overwriting_inputs(
    tmp_path: Path, plugin_fixtures: PluginFixtures
) -> None:
    output = tmp_path / "application-output.esp"
    app = StarForgeApplication()
    result = app.apply_clone_star(_star_request(plugin_fixtures), output)

    assert result.changed
    assert output.is_file()
    assert not list(tmp_path.glob("*.tmp"))
    assert app.inspect(output).data["star_count"] == 2

    with pytest.raises(ApplicationError) as raised:
        app.apply_clone_star(_star_request(plugin_fixtures), output)
    assert raised.value.exit_code == ExitCode.INPUT_ERROR
    assert raised.value.code == "output_exists"


def test_cancelled_apply_does_not_create_output(tmp_path: Path, plugin_fixtures: PluginFixtures) -> None:
    token = CancellationToken()
    token.cancel()
    output = tmp_path / "cancelled.esp"

    with pytest.raises(ApplicationError) as raised:
        StarForgeApplication().apply_clone_star(_star_request(plugin_fixtures), output, cancellation=token)
    assert raised.value.exit_code == ExitCode.CANCELLED
    assert not output.exists()


def test_project_round_trip(tmp_path: Path, plugin_fixtures: PluginFixtures) -> None:
    app = StarForgeApplication()
    project_path = tmp_path / "synthetic.starforge.json"
    app.create_project(project_path, plugin_fixtures.source, plugin_fixtures.destination)

    project = app.load_project(project_path)
    assert project.source_path == plugin_fixtures.source.resolve()
    assert project.destination_path == plugin_fixtures.destination.resolve()


def test_orbit_update_preview_and_apply(tmp_path: Path, plugin_fixtures: PluginFixtures) -> None:
    request = OrbitUpdateRequest(
        plugin_fixtures.source,
        plugin_fixtures.destination,
        0x202,
        major_axis=21_000.0,
    )
    app = StarForgeApplication()
    before = plugin_fixtures.destination.read_bytes()
    preview = app.preview_orbit_update(request)
    assert preview.data["orbit"].major_axis == 21_000.0
    assert plugin_fixtures.destination.read_bytes() == before

    output = tmp_path / "orbit-update.esp"
    app.apply_orbit_update(request, output)
    assert output.is_file()
