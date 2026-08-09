from __future__ import annotations

from conftest import PluginFixtures

from starforge.core.orbits import parse_enam, serialize_enam
from starforge.core.session import StarForgeSession


def test_parse_enam_round_trip_from_synthetic_fixture(plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    planet = next(item for item in session.view.planets if item.editor_id == "WorkshopMoonPlanetData")
    assert planet.orbit is not None
    encoded = serialize_enam(planet.orbit)
    assert parse_enam(encoded) == planet.orbit
    assert round(planet.orbit.major_axis, 5) == 20000.0
    assert round(planet.orbit.eccentricity, 4) == 0.0069


def test_parse_fnam_from_synthetic_fixture(plugin_fixtures: PluginFixtures) -> None:
    session = StarForgeSession(plugin_fixtures.source, plugin_fixtures.destination)
    planet = next(item for item in session.view.planets if item.editor_id == "WorkshopMoonPlanetData")
    assert planet.body is not None
    assert round(planet.body.gravity_well, 2) == 10883000.0
    assert round(planet.body.radius_km, 2) == 5272.0
