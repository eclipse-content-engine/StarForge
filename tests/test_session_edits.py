from __future__ import annotations

import math
from dataclasses import replace

from conftest import PluginFixtures

from starforge.core.session import StarForgeSession


def test_session_can_write_orbital_edit(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    planet = next(item for item in session.view.planets if item.editor_id == "WorkshopMoonPlanetData")
    assert planet.orbit is not None
    eccentricity = planet.orbit.eccentricity
    new_major = planet.orbit.major_axis + 1000.0
    updated = replace(
        planet.orbit,
        major_axis=new_major,
        minor_axis=new_major * math.sqrt(1.0 - eccentricity * eccentricity),
        aphelion=new_major * (1.0 + eccentricity),
    )
    session.set_planet_orbit(planet.form_id, updated)
    output_path = tmp_path / "Pytheas_orbit.esm"
    session.save_as(output_path)

    reloaded = StarForgeSession(plugin_fixtures.source, output_path)
    reloaded_planet = next(item for item in reloaded.view.planets if item.editor_id == "WorkshopMoonPlanetData")
    assert reloaded_planet.orbit is not None
    assert round(reloaded_planet.orbit.major_axis, 4) == round(updated.major_axis, 4)


def test_session_can_write_system_id_edit(tmp_path, plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    star = next(item for item in session.view.stars if item.editor_id == "WorkshopStar")
    new_system_id = 0x12345678
    session.set_star_system_id(star.form_id, new_system_id)
    output_path = tmp_path / "Pytheas_system.esm"
    session.save_as(output_path)

    reloaded = StarForgeSession(plugin_fixtures.source, output_path)
    reloaded_star = next(item for item in reloaded.view.stars if item.editor_id == "WorkshopStar")
    assert reloaded_star.system_id == new_system_id
    assert any(item.system_id == new_system_id for item in reloaded.view.planets)


def test_non_moon_clone_shifts_existing_moons_and_preview_reports_metadata(plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    source_planet = next(item for item in session.view.source_planets if item.editor_id == "SyntheticPrimePlanetData")
    dest_star = next(item for item in session.view.stars if item.editor_id == "WorkshopStar")
    before_moon = next(item for item in session.view.planets if item.editor_id == "WorkshopMoonPlanetData")

    preview = session.preview_planet_clone(
        source_planet_form_id=source_planet.form_id,
        destination_star_form_id=dest_star.form_id,
        new_editor_id="PytheasInsertedPlanetData",
        new_display_name="PytheasInserted",
        extract_biom=False,
    )

    assert not preview.hard_errors
    assert any("Local ID shifts:" in line for line in preview.draft.preview_lines)
    assert any("Metadata" in line for line in preview.draft.preview_lines)

    session._apply_clone_draft(preview.draft)
    after_moon = next(item for item in session.view.planets if item.editor_id == "WorkshopMoonPlanetData")
    inserted = next(item for item in session.view.planets if item.editor_id == "PytheasInsertedPlanetData")
    assert inserted.local_id == 9
    assert after_moon.local_id == before_moon.local_id + 1


def test_location_index_exposes_new_planet_main_orbit_and_surface_locations(plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    source_planet = next(item for item in session.view.source_planets if item.editor_id == "SyntheticPrimePlanetData")
    dest_star = next(item for item in session.view.stars if item.editor_id == "WorkshopStar")
    preview = session.preview_planet_clone(
        source_planet_form_id=source_planet.form_id,
        destination_star_form_id=dest_star.form_id,
        new_editor_id="LocationShiftPlanetData",
        new_display_name="LocationShift",
        extract_biom=False,
    )
    session._apply_clone_draft(preview.draft)

    indexed_locations = session.location_index.locations_for_local_id(dest_star.system_id, 9)
    assert indexed_locations.main is not None
    assert indexed_locations.orbit is not None
    assert indexed_locations.surface is not None
    assert indexed_locations.main.editor_id == "SWorkshop_PLocationShift"
