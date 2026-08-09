from __future__ import annotations

import pytest
from conftest import PluginFixtures

from starforge.core.biom import PlanetaryDataArchive
from starforge.core.session import StarForgeSession
from starforge.formats import PluginReader


def test_ba2_biom_extracts_known_planet(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    archive = PlanetaryDataArchive(plugin_fixtures.planet_archive)
    result = archive.extract_biom("Synthetic Prime", "SyntheticClone", tmp_path)
    assert result.output_path.exists()
    assert result.output_path.name == "SyntheticClone.biom"
    assert result.size > 0


def test_create_planet_clone_and_save(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    source_planet = next(item for item in session.view.source_planets if item.editor_id == "SyntheticPrimePlanetData")
    dest_star = next(item for item in session.view.stars if item.editor_id == "WorkshopStar")
    new_form_id, biom_result = session.create_planet_from_source(
        source_planet_form_id=source_planet.form_id,
        destination_star_form_id=dest_star.form_id,
        new_editor_id="VerdantiaClonePlanetData",
        new_display_name="VerdantiaClone",
        extract_biom=False,
    )
    assert biom_result is None
    output_path = tmp_path / "Pytheas_plus_planet.esp"
    session.save_as(output_path)

    reloaded = StarForgeSession(plugin_fixtures.source, output_path)
    cloned = next(item for item in reloaded.view.planets if item.form_id == new_form_id)
    assert cloned.display_name == "VerdantiaClone"
    assert cloned.system_id == dest_star.system_id


def test_planet_preview_does_not_mutate_and_staging_blocks_save(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    source_planet = next(item for item in session.view.source_planets if item.editor_id == "SyntheticPrimePlanetData")
    dest_star = next(item for item in session.view.stars if item.editor_id == "WorkshopStar")
    baseline_count = len(session.view.planets)

    preview = session.preview_planet_clone(
        source_planet_form_id=source_planet.form_id,
        destination_star_form_id=dest_star.form_id,
        new_editor_id="PreviewOnlyPlanetData",
        new_display_name="PreviewOnly",
        extract_biom=False,
    )
    assert not preview.hard_errors
    assert len(session.view.planets) == baseline_count

    session.stage_draft(preview)
    assert session.state.pending.staged_draft_ids == (preview.draft.draft_id,)
    with pytest.raises(ValueError, match="staged drafts"):
        session.save_as(tmp_path / "blocked.esp")


def test_create_star_clone_and_save(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    source_star = next(item for item in session.view.source_stars if item.editor_id == "SyntheticSourceStar")
    new_form_id = session.create_star_from_source(
        source_star_form_id=source_star.form_id,
        new_editor_id="PytheasTwinStar",
        new_display_name="Pytheas Twin",
        system_id=0x23456789,
    )
    output_path = tmp_path / "Pytheas_plus_star.esp"
    session.save_as(output_path)

    reloaded = StarForgeSession(plugin_fixtures.source, output_path)
    cloned = next(item for item in reloaded.view.stars if item.form_id == new_form_id)
    assert cloned.system_id == 0x23456789
    assert cloned.display_name == "Pytheas Twin"


def test_blank_plugin_can_save_new_star_with_groups_and_masters(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    source_path = plugin_fixtures.source
    destination_path = tmp_path / "empty_clone.esm"
    destination_path.write_bytes(plugin_fixtures.empty.read_bytes())
    session = StarForgeSession(source_path, destination_path)
    source_star = next(item for item in session.view.source_stars if item.editor_id == "SyntheticSourceStar")
    session.create_star_from_source(
        source_star_form_id=source_star.form_id,
        new_editor_id="BlankPluginStar",
        new_display_name="Blank Plugin Star",
        system_id=0x22222222,
    )
    output_path = tmp_path / "empty_plus_star.esm"
    session.save_as(output_path)

    assert output_path.stat().st_size > plugin_fixtures.empty.stat().st_size
    validation = session.model_io.validate_written_model(output_path, expected_groups=("STDT", "LCTN"))
    assert validation["is_valid"]
    assert "Starfield.esm" in validation["masters"]

    header = PluginReader().read_header(output_path)
    codes = header.subrecord_codes()
    assert "MAST" in codes
    # Starfield TES4 headers use MAST entries without legacy DATA companions.
    assert "DATA" not in codes

    reloaded = StarForgeSession(source_path, output_path)
    assert any(item.editor_id == "BlankPluginStar" for item in reloaded.view.stars)


def test_blank_plugin_can_save_star_and_planet_with_required_groups(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    source_path = plugin_fixtures.source
    destination_path = tmp_path / "empty_clone_planet.esm"
    destination_path.write_bytes(plugin_fixtures.empty.read_bytes())
    session = StarForgeSession(source_path, destination_path)
    source_star = next(item for item in session.view.source_stars if item.editor_id == "SyntheticSourceStar")
    new_star_form_id = session.create_star_from_source(
        source_star_form_id=source_star.form_id,
        new_editor_id="BlankSystemStar",
        new_display_name="Blank System",
        system_id=0x23333333,
    )
    source_planet = next(item for item in session.view.source_planets if item.editor_id == "SyntheticPrimePlanetData")
    session.create_planet_from_source(
        source_planet_form_id=source_planet.form_id,
        destination_star_form_id=new_star_form_id,
        new_editor_id="BlankSystemPlanetData",
        new_display_name="Blank Planet",
        extract_biom=False,
    )
    output_path = tmp_path / "empty_plus_star_planet.esm"
    session.save_as(output_path)

    expected_groups = ("STDT", "PNDT", "LCTN")
    validation = session.model_io.validate_written_model(output_path, expected_groups=expected_groups)
    assert all(group in validation["group_labels"] for group in expected_groups)

    reloaded = StarForgeSession(source_path, output_path)
    assert any(item.editor_id == "BlankSystemStar" for item in reloaded.view.stars)
    assert any(item.editor_id == "BlankSystemPlanetData" for item in reloaded.view.planets)
