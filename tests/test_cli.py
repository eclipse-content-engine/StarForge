from __future__ import annotations

import json
from pathlib import Path

from conftest import PluginFixtures

from starforge.application import ExitCode
from starforge.cli import main


def test_inspect_json_contract(capsys, plugin_fixtures: PluginFixtures) -> None:
    exit_code = main(["--json", "inspect", str(plugin_fixtures.destination)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == ExitCode.SUCCESS
    assert payload["schema_version"] == 1
    assert payload["operation"] == "inspect"
    assert payload["success"] is True
    assert payload["data"]["star_count"] == 1


def test_invalid_input_has_stable_json_error(capsys, tmp_path: Path) -> None:
    exit_code = main(["--json", "inspect", str(tmp_path / "missing.esp")])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == ExitCode.INPUT_ERROR
    assert payload == {
        "schema_version": 1,
        "operation": "inspect",
        "success": False,
        "error": {
            "code": "input_not_found",
            "message": f"Plugin does not exist: {tmp_path / 'missing.esp'}",
        },
    }


def test_cli_preview_and_apply_star(capsys, tmp_path: Path, plugin_fixtures: PluginFixtures) -> None:
    common = [
        "--source",
        str(plugin_fixtures.source),
        "--destination",
        str(plugin_fixtures.destination),
        "--source-form-id",
        "0x100",
        "--editor-id",
        "CliCloneStar",
        "--display-name",
        "CLI Clone",
        "--system-id",
        "0x45678901",
    ]
    preview_exit = main(["--json", "preview", "star", *common])
    preview = json.loads(capsys.readouterr().out)
    assert preview_exit == ExitCode.SUCCESS
    assert preview["changed"] is False

    output = tmp_path / "cli-output.esp"
    apply_exit = main(["--json", "apply", "star", *common, "--output", str(output)])
    applied = json.loads(capsys.readouterr().out)
    assert apply_exit == ExitCode.SUCCESS
    assert applied["changed"] is True
    assert output.is_file()


def test_cli_orbit_preview_json(capsys, plugin_fixtures: PluginFixtures) -> None:
    exit_code = main(
        [
            "--json",
            "preview",
            "orbit",
            "--source",
            str(plugin_fixtures.source),
            "--destination",
            str(plugin_fixtures.destination),
            "--planet-form-id",
            "0x202",
            "--major-axis",
            "21000",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == ExitCode.SUCCESS
    assert payload["changed"] is False
    assert payload["data"]["orbit"]["major_axis"] == 21_000.0
