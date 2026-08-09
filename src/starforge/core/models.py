from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class OrbitalElements:
    major_axis: float
    minor_axis: float
    aphelion: float
    eccentricity: float
    incline_radians: float
    mean_orbit: float
    axial_tilt_radians: float
    rotational_velocity: float
    start_angle: float
    perihelion_angle: float
    apply_orbital_motion: bool
    geostationary: bool


@dataclass(frozen=True)
class OrbitedBodyInfo:
    gravity_well: float
    mass_ratio_to_earth: float | None
    radius_km: float
    surface_gravity: float
    unknown_fnam: int


@dataclass(frozen=True)
class OrbitalConstraintResult:
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanetOrbitPreset:
    key: str
    label: str
    description: str


@dataclass(frozen=True)
class PlanetRecord:
    form_id: int
    editor_id: str | None
    display_name: str | None
    system_id: int
    parent_local_id: int
    local_id: int
    orbit: OrbitalElements | None
    body: OrbitedBodyInfo | None
    is_moon: bool
    has_biome: bool


@dataclass(frozen=True)
class StarRecord:
    form_id: int
    editor_id: str | None
    display_name: str | None
    system_id: int


@dataclass(frozen=True)
class SystemIdUsage:
    system_id: int
    source_paths: tuple[Path, ...] = ()
    star_form_ids: tuple[int, ...] = ()
    planet_form_ids: tuple[int, ...] = ()
    location_form_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ComponentRewriteWarning:
    component_name: str
    message: str


@dataclass(frozen=True)
class CloneFixupReport:
    rewritten_components: tuple[str, ...] = ()
    unchanged_components: tuple[str, ...] = ()
    warnings: tuple[ComponentRewriteWarning, ...] = ()


@dataclass(frozen=True)
class LocationRecordInfo:
    form_id: int
    editor_id: str | None
    display_name: str | None
    system_id: int | None
    local_id: int | None
    parent_form_id: int | None
    keywords: tuple[int, ...]
    role: str


@dataclass(frozen=True)
class IndexedLocationSet:
    main: LocationRecordInfo | None = None
    orbit: LocationRecordInfo | None = None
    surface: LocationRecordInfo | None = None


@dataclass(frozen=True)
class PlacementSpec:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class DraftOrbitOverride:
    orbit: OrbitalElements
    validation_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CloneDraft:
    draft_id: str
    kind: str
    source_form_id: int
    source_editor_id: str | None
    source_display_name: str | None
    new_editor_id: str
    new_display_name: str
    destination_star_form_id: int | None = None
    destination_parent_planet_form_id: int | None = None
    system_id: int | None = None
    placement: PlacementSpec | None = None
    local_id: int | None = None
    extract_biom: bool = False
    reserved_form_ids: tuple[int, ...] = ()
    orbit_override: DraftOrbitOverride | None = None
    rewrite_warnings: tuple[ComponentRewriteWarning, ...] = ()
    preview_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClonePreview:
    draft: CloneDraft
    hard_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionView:
    source_path: Path
    destination_path: Path
    source_stars: tuple[StarRecord, ...] = ()
    source_planets: tuple[PlanetRecord, ...] = ()
    stars: tuple[StarRecord, ...] = ()
    planets: tuple[PlanetRecord, ...] = ()
    used_system_ids: tuple[SystemIdUsage, ...] = ()


@dataclass(frozen=True)
class PendingEditSummary:
    changed_star_ids: tuple[int, ...] = ()
    changed_orbits: tuple[int, ...] = ()
    staged_draft_ids: tuple[str, ...] = ()
    applied_change_count: int = 0


@dataclass
class EditorState:
    selected_star_form_id: int | None = None
    selected_planet_form_id: int | None = None
    output_path: Path | None = None
    status_text: str = "Open a source and destination plugin to begin."
    pending: PendingEditSummary = field(default_factory=PendingEditSummary)
    draft_previews: tuple[CloneDraft, ...] = ()
