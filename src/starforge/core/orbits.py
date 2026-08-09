from __future__ import annotations

import math
import struct
from dataclasses import replace

from .models import OrbitalConstraintResult, OrbitalElements, OrbitedBodyInfo, PlanetOrbitPreset, PlanetRecord

_ENAM_STRUCT = struct.Struct("<ddddddffffII")
_FNAM_STRUCT = struct.Struct("<dfffi")

PRESETS: tuple[PlanetOrbitPreset, ...] = (
    PlanetOrbitPreset("circular_stable", "Circular Stable", "Locks the orbit to a circular, low-eccentricity path."),
    PlanetOrbitPreset("wide_stable", "Wide Stable", "Expands the semi-major axis while keeping the orbit stable."),
    PlanetOrbitPreset("eccentric", "Eccentric", "Adds moderate eccentricity while preserving a safe orbit."),
    PlanetOrbitPreset("close_moon", "Close Moon", "Tighter moon orbit for compact satellite systems."),
    PlanetOrbitPreset("wide_moon", "Wide Moon", "Wider moon orbit with more separation from siblings."),
)


def radians_to_degrees(value: float) -> float:
    return math.degrees(value)


def degrees_to_radians(value: float) -> float:
    return math.radians(value)


def parse_enam(payload: bytes) -> OrbitalElements:
    if len(payload) != _ENAM_STRUCT.size:
        raise ValueError(f"Expected ENAM payload size {_ENAM_STRUCT.size}, got {len(payload)}")
    values = _ENAM_STRUCT.unpack(payload)
    return OrbitalElements(
        major_axis=values[0],
        minor_axis=values[1],
        aphelion=values[2],
        eccentricity=values[3],
        incline_radians=values[4],
        mean_orbit=values[5],
        axial_tilt_radians=values[6],
        rotational_velocity=values[7],
        start_angle=values[8],
        perihelion_angle=values[9],
        apply_orbital_motion=bool(values[10]),
        geostationary=bool(values[11]),
    )


def serialize_enam(orbit: OrbitalElements) -> bytes:
    return _ENAM_STRUCT.pack(
        orbit.major_axis,
        orbit.minor_axis,
        orbit.aphelion,
        orbit.eccentricity,
        orbit.incline_radians,
        orbit.mean_orbit,
        orbit.axial_tilt_radians,
        orbit.rotational_velocity,
        orbit.start_angle,
        orbit.perihelion_angle,
        int(orbit.apply_orbital_motion),
        int(orbit.geostationary),
    )


def parse_fnam(payload: bytes) -> OrbitedBodyInfo:
    if len(payload) != _FNAM_STRUCT.size:
        raise ValueError(f"Expected FNAM payload size {_FNAM_STRUCT.size}, got {len(payload)}")
    gravity_well, mass_ratio, radius_km, surface_gravity, unknown = _FNAM_STRUCT.unpack(payload)
    return OrbitedBodyInfo(
        gravity_well=gravity_well,
        mass_ratio_to_earth=mass_ratio,
        radius_km=radius_km,
        surface_gravity=surface_gravity,
        unknown_fnam=unknown,
    )


def apply_preset(orbit: OrbitalElements, preset_key: str, *, is_moon: bool) -> OrbitalElements:
    if preset_key == "circular_stable":
        major = orbit.major_axis
        return replace(orbit, minor_axis=major, aphelion=major, eccentricity=0.0)
    if preset_key == "wide_stable":
        scale = 1.15 if is_moon else 1.25
        major = orbit.major_axis * scale
        return replace(orbit, major_axis=major, minor_axis=major, aphelion=major, eccentricity=0.0)
    if preset_key == "eccentric":
        ecc = min(max(orbit.eccentricity, 0.08), 0.25)
        major = orbit.major_axis
        minor = major * math.sqrt(max(1.0 - ecc * ecc, 0.01))
        aphelion = major * (1.0 + ecc)
        return replace(orbit, minor_axis=minor, aphelion=aphelion, eccentricity=ecc)
    if preset_key == "close_moon":
        major = max(orbit.major_axis * 0.9, 1.0)
        return replace(orbit, major_axis=major, minor_axis=major, aphelion=major, eccentricity=0.0)
    if preset_key == "wide_moon":
        major = orbit.major_axis * 1.2
        return replace(orbit, major_axis=major, minor_axis=major, aphelion=major, eccentricity=0.0)
    raise ValueError(f"Unknown preset: {preset_key}")


def validate_orbit(
    orbit: OrbitalElements,
    planet: PlanetRecord,
    siblings: list[PlanetRecord],
    parent_radius_km: float | None = None,
) -> OrbitalConstraintResult:
    errors: list[str] = []
    warnings: list[str] = []

    if orbit.major_axis <= 0:
        errors.append("Major axis must be greater than zero.")
    if orbit.minor_axis <= 0:
        errors.append("Minor axis must be greater than zero.")
    if not 0.0 <= orbit.eccentricity < 1.0:
        errors.append("Eccentricity must be in [0, 1).")

    expected_minor = orbit.major_axis * math.sqrt(max(1.0 - orbit.eccentricity * orbit.eccentricity, 0.0))
    if abs(expected_minor - orbit.minor_axis) > 25.0:
        errors.append("Minor axis is inconsistent with major axis and eccentricity.")

    expected_aphelion = orbit.major_axis * (1.0 + orbit.eccentricity)
    if abs(expected_aphelion - orbit.aphelion) > 25.0:
        errors.append("Aphelion is inconsistent with major axis and eccentricity.")

    body_radius = planet.body.radius_km if planet.body is not None else 0.0
    safe_min = body_radius * 2.5
    if parent_radius_km is not None:
        safe_min = max(safe_min, parent_radius_km * 1.25)
    perihelion = orbit.major_axis * (1.0 - orbit.eccentricity)
    if perihelion <= safe_min:
        errors.append("Perihelion is too small and would intersect the parent body safety band.")

    for sibling in siblings:
        if sibling.form_id == planet.form_id or sibling.orbit is None:
            continue
        sibling_perihelion = sibling.orbit.major_axis * (1.0 - sibling.orbit.eccentricity)
        sibling_aphelion = sibling.orbit.major_axis * (1.0 + sibling.orbit.eccentricity)
        if perihelion <= sibling_aphelion and orbit.aphelion >= sibling_perihelion:
            errors.append(
                f"Orbit overlaps sibling '{sibling.display_name or sibling.editor_id or hex(sibling.form_id)}'."
            )
            break

    if planet.is_moon and not orbit.apply_orbital_motion:
        warnings.append("Moon is geostationary only when orbital motion is disabled.")

    return OrbitalConstraintResult(is_valid=not errors, errors=tuple(errors), warnings=tuple(warnings))
