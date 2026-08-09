from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from ..formats import MutableSubrecord, PluginReader, SubrecordEntry
from .biom import BiomExtractResult, PlanetaryDataArchive
from .clone_fidelity import apply_component_fixups
from .location_index import LocationIndex
from .models import (
    CloneDraft,
    ClonePreview,
    ComponentRewriteWarning,
    DraftOrbitOverride,
    EditorState,
    OrbitalElements,
    PlacementSpec,
    PlanetRecord,
    SessionView,
    StarRecord,
    SystemIdUsage,
)
from .orbits import PRESETS, apply_preset, parse_enam, parse_fnam, serialize_enam, validate_orbit
from .plugin_model import MutablePluginModel, MutableRecord, StarForgePluginModelIO
from .system_ids import collect_system_id_usage

KW_LOC_TYPE_STAR_SYSTEM = 0x149F
KW_LOC_TYPE_PLANET = 0x14A0
KW_LOC_TYPE_MOON = 0x16010
KW_LOC_TYPE_MAJOR_ORBITAL = 0x70A54
KW_LOC_TYPE_SURFACE = 0x16503
KW_LOC_TYPE_ORBIT = 0x16504
FID_UNIVERSE = 0x1A53A


class StarForgeSession:
    def __init__(self, source_path: Path, destination_path: Path) -> None:
        self.source_path = source_path
        self.destination_path = destination_path
        self.reader = PluginReader()
        self.model_io = StarForgePluginModelIO()
        self.model: MutablePluginModel = self.model_io.load_model(destination_path)
        self.state = EditorState()
        self.location_index = LocationIndex.build(self.model)
        self.view = self._build_view()

    def _build_view(self) -> SessionView:
        self.location_index = LocationIndex.build(self.model)
        source_usage = [item for item in collect_system_id_usage([self.source_path]) if item.source_paths]
        return SessionView(
            source_path=self.source_path,
            destination_path=self.destination_path,
            source_stars=tuple(self._read_stars(self.source_path)),
            source_planets=tuple(self._read_planets(self.source_path)),
            stars=tuple(self._read_stars_from_model()),
            planets=tuple(self._read_planets_from_model()),
            used_system_ids=tuple(self._merge_system_usage(source_usage, self._collect_model_system_usage())),
        )

    def allocate_system_id(self) -> int:
        used = {item.system_id for item in self.view.used_system_ids}
        candidate = 0x1000
        while candidate in used:
            candidate += 1
        return candidate

    def set_star_system_id(self, star_form_id: int, new_system_id: int) -> None:
        star = next(item for item in self.view.stars if item.form_id == star_form_id)
        duplicate = next(
            (
                item
                for item in self.view.used_system_ids
                if item.system_id == new_system_id and star_form_id not in item.star_form_ids
            ),
            None,
        )
        if duplicate is not None:
            raise ValueError(f"System ID 0x{new_system_id:08X} is already in use.")
        old_system_id = star.system_id
        self.model_io.replace_subrecord(
            self.model, form_id=star_form_id, code="DNAM", payload=new_system_id.to_bytes(4, "little")
        )
        for planet in self.view.planets:
            if planet.system_id != old_system_id:
                continue
            payload = (
                new_system_id.to_bytes(4, "little")
                + planet.parent_local_id.to_bytes(4, "little")
                + planet.local_id.to_bytes(4, "little")
            )
            self.model_io.replace_subrecord(self.model, form_id=planet.form_id, code="GNAM", payload=payload, ordinal=1)
        for location in self.location_index.locations_by_form_id.values():
            if location.system_id != old_system_id:
                continue
            record = self.model.records_by_form_id[location.form_id]
            self._replace_subrecord_payload(record, "XNAM", new_system_id.to_bytes(4, "little"))
        changed = tuple(sorted(set(self.state.pending.changed_star_ids + (star_form_id,))))
        self.state.pending = replace(
            self.state.pending,
            changed_star_ids=changed,
            applied_change_count=self.state.pending.applied_change_count + 1,
        )
        self.view = self._build_view()
        self.state.status_text = f"Prepared system ID change for 0x{star_form_id:08X}."

    def set_planet_orbit(self, planet_form_id: int, orbit: OrbitalElements) -> None:
        planet = next(item for item in self.view.planets if item.form_id == planet_form_id)
        siblings = [
            item
            for item in self.view.planets
            if item.system_id == planet.system_id
            and item.parent_local_id == planet.parent_local_id
            and item.form_id != planet_form_id
        ]
        validation = validate_orbit(orbit, planet, siblings)
        if not validation.is_valid:
            raise ValueError("\n".join(validation.errors))
        self.model_io.replace_subrecord(self.model, form_id=planet_form_id, code="ENAM", payload=serialize_enam(orbit))
        changed = tuple(sorted(set(self.state.pending.changed_orbits + (planet_form_id,))))
        self.state.pending = replace(
            self.state.pending, changed_orbits=changed, applied_change_count=self.state.pending.applied_change_count + 1
        )
        self.view = self._build_view()
        self.state.status_text = f"Prepared orbital update for 0x{planet_form_id:08X}."

    def apply_preset(self, planet_form_id: int, preset_key: str) -> OrbitalElements:
        if preset_key not in {item.key for item in PRESETS}:
            raise ValueError(f"Unknown preset: {preset_key}")
        planet = next(item for item in self.view.planets if item.form_id == planet_form_id)
        if planet.orbit is None:
            raise ValueError("Planet record has no orbital data.")
        orbit = apply_preset(planet.orbit, preset_key, is_moon=planet.is_moon)
        self.set_planet_orbit(planet_form_id, orbit)
        return orbit

    def save_as(self, output_path: Path) -> None:
        if self.state.draft_previews:
            raise ValueError("Apply or discard staged drafts before saving.")
        self.model_io.write_model(output_path, self.model)
        self.state.output_path = output_path
        self.state.status_text = f"Saved edited plugin to {output_path}."

    def preview_star_clone(
        self,
        *,
        source_star_form_id: int,
        new_editor_id: str,
        new_display_name: str,
        system_id: int,
        position: tuple[float, float, float] | None = None,
    ) -> ClonePreview:
        source_star = next(item for item in self.view.source_stars if item.form_id == source_star_form_id)
        errors: list[str] = []
        duplicate = next((item for item in self.view.used_system_ids if item.system_id == system_id), None)
        if duplicate is not None:
            errors.append(f"System ID 0x{system_id:08X} is already in use.")
        placement = PlacementSpec(*(position or self._read_star_position(source_star_form_id)))
        reserved_form_ids = self._reserve_form_ids(2)
        draft = CloneDraft(
            draft_id=self._next_draft_id(),
            kind="star",
            source_form_id=source_star_form_id,
            source_editor_id=source_star.editor_id,
            source_display_name=source_star.display_name,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            system_id=system_id,
            placement=placement,
            reserved_form_ids=reserved_form_ids,
            preview_lines=(
                f"Create star '{new_display_name}' ({new_editor_id})",
                f"Source star: {source_star.display_name or source_star.editor_id or hex(source_star.form_id)}",
                f"System ID: 0x{system_id:08X}",
                f"Star record form ID: 0x{reserved_form_ids[0]:08X}",
                f"Star location form ID: 0x{reserved_form_ids[1]:08X}",
                f"Placement: x={placement.x:.3f} y={placement.y:.3f} z={placement.z:.3f}",
            ),
        )
        return self._with_clone_fixup_preview(ClonePreview(draft=draft, hard_errors=tuple(errors)))

    def preview_planet_clone(
        self,
        *,
        source_planet_form_id: int,
        destination_star_form_id: int,
        new_editor_id: str,
        new_display_name: str,
        extract_biom: bool = True,
        orbit_override: OrbitalElements | None = None,
    ) -> ClonePreview:
        source_planet = next(item for item in self.view.source_planets if item.form_id == source_planet_form_id)
        destination_star = next(item for item in self.view.stars if item.form_id == destination_star_form_id)
        errors: list[str] = []
        if source_planet.is_moon:
            errors.append("Select a non-moon source planet for planet creation.")
        local_id, local_updates = self._plan_local_id_changes(destination_star.system_id, is_moon=False)
        orbit_override_model = self._build_orbit_override(
            source_planet, destination_star.system_id, 0, local_id, orbit_override
        )
        reserved_form_ids = self._reserve_form_ids(4)
        biom_path = (
            self._predict_biom_output_path(new_display_name) if extract_biom and source_planet.has_biome else None
        )
        preview_lines = [
            f"Create planet '{new_display_name}' ({new_editor_id})",
            f"Source planet: {source_planet.display_name or source_planet.editor_id or hex(source_planet.form_id)}",
            "Destination star: "
            f"{destination_star.display_name or destination_star.editor_id or hex(destination_star.form_id)}",
            f"System ID: 0x{destination_star.system_id:08X}",
            f"Planned local ID: {local_id}",
            f"Planet record form ID: 0x{reserved_form_ids[0]:08X}",
            "Planet/Orbit/Surface locations: "
            f"0x{reserved_form_ids[1]:08X}, 0x{reserved_form_ids[2]:08X}, 0x{reserved_form_ids[3]:08X}",
        ]
        if local_updates:
            preview_lines.append(
                "Local ID shifts: "
                + ", ".join(
                    f"0x{form_id:08X}->{new_local_id}" for form_id, new_local_id in sorted(local_updates.items())
                )
            )
        if biom_path is not None:
            preview_lines.append(f"Biome extract: {biom_path}")
        if orbit_override_model is not None:
            preview_lines.append("Orbit override: use current orbital editor values")
        draft = CloneDraft(
            draft_id=self._next_draft_id(),
            kind="planet",
            source_form_id=source_planet_form_id,
            source_editor_id=source_planet.editor_id,
            source_display_name=source_planet.display_name,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            destination_star_form_id=destination_star_form_id,
            system_id=destination_star.system_id,
            local_id=local_id,
            extract_biom=extract_biom,
            reserved_form_ids=reserved_form_ids,
            orbit_override=orbit_override_model,
            preview_lines=tuple(preview_lines),
        )
        return self._with_clone_fixup_preview(ClonePreview(draft=draft, hard_errors=tuple(errors)))

    def preview_moon_clone(
        self,
        *,
        source_moon_form_id: int,
        destination_parent_planet_form_id: int,
        new_editor_id: str,
        new_display_name: str,
        extract_biom: bool = True,
        orbit_override: OrbitalElements | None = None,
    ) -> ClonePreview:
        source_moon = next(item for item in self.view.source_planets if item.form_id == source_moon_form_id)
        destination_parent = next(
            item for item in self.view.planets if item.form_id == destination_parent_planet_form_id
        )
        errors: list[str] = []
        if not source_moon.is_moon:
            errors.append("Select a moon source record for moon creation.")
        if destination_parent.is_moon:
            errors.append("Select a destination planet, not a moon.")
        local_id, _local_updates = self._plan_local_id_changes(destination_parent.system_id, is_moon=True)
        orbit_override_model = self._build_orbit_override(
            source_moon, destination_parent.system_id, destination_parent.local_id, local_id, orbit_override
        )
        reserved_form_ids = self._reserve_form_ids(4)
        biom_path = self._predict_biom_output_path(new_display_name) if extract_biom and source_moon.has_biome else None
        preview_lines = [
            f"Create moon '{new_display_name}' ({new_editor_id})",
            f"Source moon: {source_moon.display_name or source_moon.editor_id or hex(source_moon.form_id)}",
            "Parent planet: "
            f"{destination_parent.display_name or destination_parent.editor_id or hex(destination_parent.form_id)}",
            f"System ID: 0x{destination_parent.system_id:08X}",
            f"Parent local ID: {destination_parent.local_id}",
            f"Planned local ID: {local_id}",
            f"Moon record form ID: 0x{reserved_form_ids[0]:08X}",
            "Moon/Orbit/Surface locations: "
            f"0x{reserved_form_ids[1]:08X}, 0x{reserved_form_ids[2]:08X}, 0x{reserved_form_ids[3]:08X}",
        ]
        if biom_path is not None:
            preview_lines.append(f"Biome extract: {biom_path}")
        if orbit_override_model is not None:
            preview_lines.append("Orbit override: use current orbital editor values")
        draft = CloneDraft(
            draft_id=self._next_draft_id(),
            kind="moon",
            source_form_id=source_moon_form_id,
            source_editor_id=source_moon.editor_id,
            source_display_name=source_moon.display_name,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            destination_parent_planet_form_id=destination_parent_planet_form_id,
            system_id=destination_parent.system_id,
            local_id=local_id,
            extract_biom=extract_biom,
            reserved_form_ids=reserved_form_ids,
            orbit_override=orbit_override_model,
            preview_lines=tuple(preview_lines),
        )
        return self._with_clone_fixup_preview(ClonePreview(draft=draft, hard_errors=tuple(errors)))

    def stage_draft(self, preview: ClonePreview) -> CloneDraft:
        if preview.hard_errors:
            raise ValueError("\n".join(preview.hard_errors))
        drafts = self.state.draft_previews + (preview.draft,)
        self.state.draft_previews = drafts
        self.state.pending = replace(self.state.pending, staged_draft_ids=tuple(item.draft_id for item in drafts))
        self.state.status_text = f"Staged draft {preview.draft.draft_id}."
        return preview.draft

    def discard_draft(self, draft_id: str) -> None:
        drafts = tuple(item for item in self.state.draft_previews if item.draft_id != draft_id)
        self.state.draft_previews = drafts
        self.state.pending = replace(self.state.pending, staged_draft_ids=tuple(item.draft_id for item in drafts))
        self.state.status_text = f"Discarded draft {draft_id}."

    def apply_draft(self, draft_id: str) -> tuple[int, BiomExtractResult | None]:
        draft = next(item for item in self.state.draft_previews if item.draft_id == draft_id)
        result = self._apply_clone_draft(draft)
        self.discard_draft(draft_id)
        self.state.status_text = f"Applied draft {draft_id}."
        return result

    def apply_all_drafts(self) -> list[tuple[int, BiomExtractResult | None]]:
        results: list[tuple[int, BiomExtractResult | None]] = []
        for draft in list(self.state.draft_previews):
            results.append(self._apply_clone_draft(draft))
        self.state.draft_previews = ()
        self.state.pending = replace(self.state.pending, staged_draft_ids=())
        self.state.status_text = f"Applied {len(results)} staged drafts."
        return results

    def create_star_from_source(
        self,
        *,
        source_star_form_id: int,
        new_editor_id: str,
        new_display_name: str,
        system_id: int,
        position: tuple[float, float, float] | None = None,
    ) -> int:
        preview = self.preview_star_clone(
            source_star_form_id=source_star_form_id,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            system_id=system_id,
            position=position,
        )
        if preview.hard_errors:
            raise ValueError("\n".join(preview.hard_errors))
        form_id, _ = self._apply_clone_draft(preview.draft)
        self.state.status_text = f"Created star '{new_display_name}' in destination plugin."
        return form_id

    def create_planet_from_source(
        self,
        *,
        source_planet_form_id: int,
        destination_star_form_id: int,
        new_editor_id: str,
        new_display_name: str,
        extract_biom: bool = True,
    ) -> tuple[int, BiomExtractResult | None]:
        preview = self.preview_planet_clone(
            source_planet_form_id=source_planet_form_id,
            destination_star_form_id=destination_star_form_id,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            extract_biom=extract_biom,
        )
        if preview.hard_errors:
            raise ValueError("\n".join(preview.hard_errors))
        result = self._apply_clone_draft(preview.draft)
        self.state.status_text = f"Created planet '{new_display_name}' in destination plugin."
        return result

    def create_moon_from_source(
        self,
        *,
        source_moon_form_id: int,
        destination_parent_planet_form_id: int,
        new_editor_id: str,
        new_display_name: str,
        extract_biom: bool = True,
    ) -> tuple[int, BiomExtractResult | None]:
        preview = self.preview_moon_clone(
            source_moon_form_id=source_moon_form_id,
            destination_parent_planet_form_id=destination_parent_planet_form_id,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            extract_biom=extract_biom,
        )
        if preview.hard_errors:
            raise ValueError("\n".join(preview.hard_errors))
        result = self._apply_clone_draft(preview.draft)
        self.state.status_text = f"Created moon '{new_display_name}' in destination plugin."
        return result

    def extract_biom_for_clone(self, source_planet_name: str, destination_name: str) -> BiomExtractResult:
        archive = PlanetaryDataArchive(self.source_path.parent / "Starfield - PlanetData.ba2")
        return archive.extract_biom(source_planet_name, destination_name, self.destination_path.parent)

    def _apply_clone_draft(self, draft: CloneDraft) -> tuple[int, BiomExtractResult | None]:
        self._consume_reserved_form_ids(draft.reserved_form_ids)
        biom_result: BiomExtractResult | None = None
        if draft.kind == "star":
            source_record = self._load_record(self.source_path, "STDT", draft.source_form_id)
            cloned = self._clone_record(source_record, draft.reserved_form_ids[0])
            self._replace_cstring(cloned, "EDID", draft.new_editor_id)
            self._replace_cstring(cloned, "ANAM", draft.new_display_name)
            self._replace_payload(cloned, "DNAM", int(draft.system_id or 0).to_bytes(4, "little"))
            placement = draft.placement or PlacementSpec(*self._read_star_position(draft.source_form_id))
            self._replace_payload(cloned, "BNAM", struct.pack("<fff", placement.x, placement.y, placement.z))
            fixup_report = apply_component_fixups(
                cloned,
                source_candidates=self._source_name_candidates(draft.source_display_name, draft.source_editor_id),
                new_display_name=draft.new_display_name,
                new_editor_id=draft.new_editor_id,
            )
            star_loc = self._build_star_location(
                draft.new_display_name, int(draft.system_id or 0), form_id=draft.reserved_form_ids[1]
            )
            self.model_io.add_record(self.model, cloned)
            self.model_io.add_record(self.model, star_loc)
            self._count_applied_change(2)
            self.view = self._build_view()
            self.state.status_text = self._format_apply_status(draft, fixup_report.warnings, biom_result)
            return cloned.form_id, biom_result

        if draft.kind == "planet":
            source_planet = next(item for item in self.view.source_planets if item.form_id == draft.source_form_id)
            destination_star = next(item for item in self.view.stars if item.form_id == draft.destination_star_form_id)
            source_record = self._load_record(self.source_path, "PNDT", draft.source_form_id)
            local_id, local_updates = self._plan_local_id_changes(destination_star.system_id, is_moon=False)
            self._apply_local_id_updates(destination_star.system_id, local_updates)
            cloned = self._clone_record(source_record, draft.reserved_form_ids[0])
            self._replace_cstring(cloned, "EDID", draft.new_editor_id)
            self._replace_cstring(cloned, "ANAM", draft.new_display_name)
            self._replace_payload(
                cloned, "GNAM", struct.pack("<III", destination_star.system_id, 0, local_id), ordinal=1
            )
            if draft.orbit_override is not None:
                self._replace_payload(cloned, "ENAM", serialize_enam(draft.orbit_override.orbit))
            fixup_report = apply_component_fixups(
                cloned,
                source_candidates=self._source_name_candidates(source_planet.display_name, source_planet.editor_id),
                new_display_name=draft.new_display_name,
                new_editor_id=draft.new_editor_id,
            )
            star_loc_form_id = self._find_star_location_form_id(
                destination_star.system_id,
                star_name=destination_star.display_name or destination_star.editor_id,
            )
            planet_loc = self._build_planet_location(
                star_name=destination_star.display_name or destination_star.editor_id or "Star",
                planet_name=draft.new_display_name,
                system_id=destination_star.system_id,
                parent_loc_form_id=star_loc_form_id,
                local_id=local_id,
                is_moon=False,
                form_id=draft.reserved_form_ids[1],
            )
            destination_star_name = destination_star.display_name or destination_star.editor_id or "Star"
            orbit_loc = self._build_child_location(
                edid=f"S{destination_star_name}_P{draft.new_display_name}_Orbit",
                display_name=draft.new_display_name,
                system_id=destination_star.system_id,
                parent_loc_form_id=planet_loc.form_id,
                local_id=local_id,
                keyword=KW_LOC_TYPE_ORBIT,
                form_id=draft.reserved_form_ids[2],
            )
            surface_loc = self._build_child_location(
                edid=f"S{destination_star_name}_P{draft.new_display_name}_Surface",
                display_name=draft.new_display_name,
                system_id=destination_star.system_id,
                parent_loc_form_id=planet_loc.form_id,
                local_id=local_id,
                keyword=KW_LOC_TYPE_SURFACE,
                form_id=draft.reserved_form_ids[3],
            )
            for record in (cloned, planet_loc, orbit_loc, surface_loc):
                self.model_io.add_record(self.model, record)
            if draft.extract_biom and source_planet.has_biome:
                biom_result = self.extract_biom_for_clone(
                    source_planet.display_name or source_planet.editor_id or draft.new_display_name,
                    draft.new_display_name,
                )
            self._count_applied_change(4 + len(local_updates))
            self.view = self._build_view()
            self.state.status_text = self._format_apply_status(draft, fixup_report.warnings, biom_result)
            return cloned.form_id, biom_result

        source_moon = next(item for item in self.view.source_planets if item.form_id == draft.source_form_id)
        destination_parent = next(
            item for item in self.view.planets if item.form_id == draft.destination_parent_planet_form_id
        )
        source_record = self._load_record(self.source_path, "PNDT", draft.source_form_id)
        cloned = self._clone_record(source_record, draft.reserved_form_ids[0])
        local_id = draft.local_id or self._plan_local_id_changes(destination_parent.system_id, is_moon=True)[0]
        self._replace_cstring(cloned, "EDID", draft.new_editor_id)
        self._replace_cstring(cloned, "ANAM", draft.new_display_name)
        self._replace_payload(
            cloned,
            "GNAM",
            struct.pack("<III", destination_parent.system_id, destination_parent.local_id, local_id),
            ordinal=1,
        )
        if draft.orbit_override is not None:
            self._replace_payload(cloned, "ENAM", serialize_enam(draft.orbit_override.orbit))
        fixup_report = apply_component_fixups(
            cloned,
            source_candidates=self._source_name_candidates(source_moon.display_name, source_moon.editor_id),
            new_display_name=draft.new_display_name,
            new_editor_id=draft.new_editor_id,
        )
        star = next(item for item in self.view.stars if item.system_id == destination_parent.system_id)
        star_loc_form_id = self._find_star_location_form_id(
            destination_parent.system_id,
            star_name=star.display_name or star.editor_id,
        )
        moon_loc = self._build_planet_location(
            star_name=star.display_name or star.editor_id or "Star",
            planet_name=draft.new_display_name,
            system_id=destination_parent.system_id,
            parent_loc_form_id=star_loc_form_id,
            local_id=local_id,
            is_moon=True,
            parent_planet_name=destination_parent.display_name or destination_parent.editor_id or "Planet",
            form_id=draft.reserved_form_ids[1],
        )
        star_name = star.display_name or star.editor_id or "Star"
        parent_name = destination_parent.display_name or destination_parent.editor_id or "Planet"
        orbit_loc = self._build_child_location(
            edid=f"S{star_name}_P{parent_name}_M{draft.new_display_name}_Orbit",
            display_name=draft.new_display_name,
            system_id=destination_parent.system_id,
            parent_loc_form_id=moon_loc.form_id,
            local_id=local_id,
            keyword=KW_LOC_TYPE_ORBIT,
            form_id=draft.reserved_form_ids[2],
        )
        surface_loc = self._build_child_location(
            edid=f"S{star_name}_P{parent_name}_M{draft.new_display_name}_Surface",
            display_name=draft.new_display_name,
            system_id=destination_parent.system_id,
            parent_loc_form_id=moon_loc.form_id,
            local_id=local_id,
            keyword=KW_LOC_TYPE_SURFACE,
            form_id=draft.reserved_form_ids[3],
        )
        for record in (cloned, moon_loc, orbit_loc, surface_loc):
            self.model_io.add_record(self.model, record)
        if draft.extract_biom and source_moon.has_biome:
            biom_result = self.extract_biom_for_clone(
                source_moon.display_name or source_moon.editor_id or draft.new_display_name, draft.new_display_name
            )
        self._count_applied_change(4)
        self.view = self._build_view()
        self.state.status_text = self._format_apply_status(draft, fixup_report.warnings, biom_result)
        return cloned.form_id, biom_result

    def _format_apply_status(
        self,
        draft: CloneDraft,
        rewrite_warnings: tuple[ComponentRewriteWarning, ...],
        biom_result: BiomExtractResult | None,
    ) -> str:
        parts = [f"Applied {draft.kind} clone '{draft.new_display_name}'."]
        if rewrite_warnings:
            parts.append(
                "Warnings: " + "; ".join(f"{item.component_name}: {item.message}" for item in rewrite_warnings)
            )
        if biom_result is not None:
            parts.append(f"Biome: {biom_result.output_path}")
        return " ".join(parts)

    def _with_clone_fixup_preview(self, preview: ClonePreview) -> ClonePreview:
        if preview.hard_errors:
            return preview
        signature = "STDT" if preview.draft.kind == "star" else "PNDT"
        source_record = self._load_record(self.source_path, signature, preview.draft.source_form_id)
        cloned = self._clone_record(source_record, preview.draft.reserved_form_ids[0])
        self._replace_cstring(cloned, "EDID", preview.draft.new_editor_id)
        self._replace_cstring(cloned, "ANAM", preview.draft.new_display_name)
        report = apply_component_fixups(
            cloned,
            source_candidates=self._source_name_candidates(
                preview.draft.source_display_name, preview.draft.source_editor_id
            ),
            new_display_name=preview.draft.new_display_name,
            new_editor_id=preview.draft.new_editor_id,
        )
        preview_lines = list(preview.draft.preview_lines)
        if report.warnings:
            preview_lines.append("Metadata warnings:")
            preview_lines.extend(f"- {item.component_name}: {item.message}" for item in report.warnings)
        else:
            preview_lines.append("Metadata rewrites: TESFullName and detectable Houdini strings will be updated.")
        return ClonePreview(
            draft=replace(preview.draft, rewrite_warnings=report.warnings, preview_lines=tuple(preview_lines)),
            hard_errors=preview.hard_errors,
        )

    def _build_orbit_override(
        self,
        source_planet: PlanetRecord,
        system_id: int,
        parent_local_id: int,
        local_id: int,
        orbit_override: OrbitalElements | None,
    ) -> DraftOrbitOverride | None:
        if orbit_override is None:
            return None
        candidate = PlanetRecord(
            form_id=0,
            editor_id=source_planet.editor_id,
            display_name=source_planet.display_name,
            system_id=system_id,
            parent_local_id=parent_local_id,
            local_id=local_id,
            orbit=orbit_override,
            body=source_planet.body,
            is_moon=parent_local_id > 0,
            has_biome=source_planet.has_biome,
        )
        siblings = [
            item
            for item in self.view.planets
            if item.system_id == system_id and item.parent_local_id == parent_local_id
        ]
        validation = validate_orbit(orbit_override, candidate, siblings)
        if not validation.is_valid:
            raise ValueError("\n".join(validation.errors))
        return DraftOrbitOverride(orbit=orbit_override, validation_warnings=validation.warnings)

    def _count_applied_change(self, count: int) -> None:
        self.state.pending = replace(
            self.state.pending, applied_change_count=self.state.pending.applied_change_count + count
        )

    def _read_stars(self, path: Path) -> list[StarRecord]:
        rows: list[StarRecord] = []
        for record in self.reader._read_direct_records_with_payload(path, "STDT"):
            system_id = None
            display_name = None
            for entry in self.reader._scan_subrecord_entries(record.payload, record.offset):
                if entry.code == "DNAM" and len(entry.data) >= 4:
                    system_id = int.from_bytes(entry.data[:4], "little")
                elif entry.code == "ANAM":
                    display_name = self._decode_cstring(entry.data)
            if system_id is None:
                continue
            rows.append(
                StarRecord(
                    form_id=record.form_id,
                    editor_id=self.reader._extract_shallow_edid(record.payload),
                    display_name=display_name,
                    system_id=system_id,
                )
            )
        return rows

    def _read_planets(self, path: Path) -> list[PlanetRecord]:
        rows: list[PlanetRecord] = []
        for record in self.reader._read_direct_records_with_payload(path, "PNDT"):
            rows.append(
                self._planet_from_subrecords(
                    record.form_id,
                    [item for item in self.reader._scan_subrecord_entries(record.payload, record.offset)],
                )
            )
        return [item for item in rows if item.system_id != 0]

    def _read_stars_from_model(self) -> list[StarRecord]:
        rows: list[StarRecord] = []
        for record in self.model.records_by_form_id.values():
            if record.signature != "STDT":
                continue
            system_id = self._int_from_subrecord(record, "DNAM")
            if system_id is None:
                continue
            rows.append(
                StarRecord(
                    form_id=record.form_id,
                    editor_id=self._string_from_subrecord(record, "EDID"),
                    display_name=self._string_from_subrecord(record, "ANAM"),
                    system_id=system_id,
                )
            )
        return sorted(rows, key=lambda item: item.form_id)

    def _read_planets_from_model(self) -> list[PlanetRecord]:
        rows: list[PlanetRecord] = []
        for record in self.model.records_by_form_id.values():
            if record.signature != "PNDT":
                continue
            planet = self._planet_from_subrecords(record.form_id, record.subrecords)
            if planet.system_id != 0:
                rows.append(planet)
        return sorted(rows, key=lambda item: item.form_id)

    def _planet_from_subrecords(
        self, form_id: int, subrecords: Sequence[MutableSubrecord | SubrecordEntry]
    ) -> PlanetRecord:
        display_name = None
        orbit = None
        body = None
        system_id = 0
        parent_local_id = 0
        local_id = 0
        editor_id = None
        has_biome = False
        gnam_index = 0
        for entry in subrecords:
            code = entry.code
            payload = entry.raw_payload if isinstance(entry, MutableSubrecord) else entry.data
            if code == "EDID":
                editor_id = self._decode_cstring(payload)
            elif code == "ANAM":
                display_name = self._decode_cstring(payload)
            elif code == "ENAM":
                orbit = parse_enam(payload)
            elif code == "FNAM":
                try:
                    body = parse_fnam(payload)
                except ValueError:
                    body = None
            elif code == "GNAM":
                if gnam_index == 1 and len(payload) >= 12:
                    system_id = int.from_bytes(payload[:4], "little")
                    parent_local_id = int.from_bytes(payload[4:8], "little")
                    local_id = int.from_bytes(payload[8:12], "little")
                gnam_index += 1
            elif code == "PPBD":
                has_biome = True
        return PlanetRecord(
            form_id=form_id,
            editor_id=editor_id,
            display_name=display_name,
            system_id=system_id,
            parent_local_id=parent_local_id,
            local_id=local_id,
            orbit=orbit,
            body=body,
            is_moon=parent_local_id > 0,
            has_biome=has_biome,
        )

    def _collect_model_system_usage(self) -> list[SystemIdUsage]:
        usage: dict[int, dict[str, list[int]]] = {}
        for record in self.model.records_by_form_id.values():
            if record.signature == "STDT":
                system_id = self._int_from_subrecord(record, "DNAM")
                if system_id is None:
                    continue
                usage.setdefault(system_id, {"stars": [], "planets": [], "locations": []})["stars"].append(
                    record.form_id
                )
            elif record.signature == "PNDT":
                gnam = self._payload_from_subrecord(record, "GNAM", ordinal=1)
                if gnam is None or len(gnam) < 12:
                    continue
                system_id = int.from_bytes(gnam[:4], "little")
                usage.setdefault(system_id, {"stars": [], "planets": [], "locations": []})["planets"].append(
                    record.form_id
                )
        for location in self.location_index.locations_by_form_id.values():
            if location.system_id is None:
                continue
            usage.setdefault(location.system_id, {"stars": [], "planets": [], "locations": []})["locations"].append(
                location.form_id
            )
        return [
            SystemIdUsage(
                system_id=system_id,
                source_paths=(self.destination_path,),
                star_form_ids=tuple(sorted(values["stars"])),
                planet_form_ids=tuple(sorted(values["planets"])),
                location_form_ids=tuple(sorted(values["locations"])),
            )
            for system_id, values in sorted(usage.items())
        ]

    def _merge_system_usage(
        self, source_items: list[SystemIdUsage], model_items: list[SystemIdUsage]
    ) -> list[SystemIdUsage]:
        merged: dict[int, SystemIdUsage] = {}
        for item in source_items + model_items:
            previous = merged.get(item.system_id)
            if previous is None:
                merged[item.system_id] = item
                continue
            merged[item.system_id] = SystemIdUsage(
                system_id=item.system_id,
                source_paths=tuple(dict.fromkeys(previous.source_paths + item.source_paths)),
                star_form_ids=tuple(sorted(set(previous.star_form_ids + item.star_form_ids))),
                planet_form_ids=tuple(sorted(set(previous.planet_form_ids + item.planet_form_ids))),
                location_form_ids=tuple(sorted(set(previous.location_form_ids + item.location_form_ids))),
            )
        return [merged[key] for key in sorted(merged)]

    def _reserve_form_ids(self, count: int) -> tuple[int, ...]:
        reserved_count = sum(len(item.reserved_form_ids) for item in self.state.draft_previews)
        start = self.model.header.next_object_id + reserved_count
        return tuple(range(start, start + count))

    def _consume_reserved_form_ids(self, reserved_form_ids: tuple[int, ...]) -> None:
        if reserved_form_ids:
            self.model.header.next_object_id = max(self.model.header.next_object_id, max(reserved_form_ids) + 1)

    def _next_draft_id(self) -> str:
        return f"draft-{len(self.state.draft_previews) + 1:03d}"

    def _load_record(self, path: Path, signature: str, form_id: int) -> MutableRecord:
        data = path.read_bytes()
        for record in self.reader._read_direct_records_with_payload(path, signature):
            if record.form_id != form_id:
                continue
            header_values = self.model_io._record_header_values(data, record.offset)
            subrecords = [
                MutableSubrecord(code=item.code, raw_payload=item.data)
                for item in self.reader._scan_subrecord_entries(record.payload, record.offset)
            ]
            return MutableRecord(
                signature=signature,
                form_id=form_id,
                flags=header_values["flags"],
                revision=header_values["revision"],
                internal_version=header_values["internal_version"],
                unknown=header_values["unknown"],
                was_compressed=(header_values["flags"] & 0x00040000) != 0,
                subrecords=subrecords,
            )
        raise ValueError(f"Record 0x{form_id:08X} was not found in {path.name}.")

    def _clone_record(self, record: MutableRecord, new_form_id: int) -> MutableRecord:
        return MutableRecord(
            signature=record.signature,
            form_id=new_form_id,
            flags=record.flags,
            revision=record.revision,
            internal_version=record.internal_version,
            unknown=record.unknown,
            was_compressed=record.was_compressed,
            subrecords=[
                MutableSubrecord(code=item.code, raw_payload=bytes(item.raw_payload)) for item in record.subrecords
            ],
        )

    def _replace_cstring(self, record: MutableRecord, code: str, value: str, ordinal: int = 0) -> None:
        self._replace_payload(record, code, value.encode("utf-8") + b"\x00", ordinal=ordinal)

    def _replace_payload(self, record: MutableRecord, code: str, payload: bytes, ordinal: int = 0) -> None:
        found = 0
        for subrecord in record.subrecords:
            if subrecord.code != code:
                continue
            if found == ordinal:
                subrecord.raw_payload = payload
                return
            found += 1
        raise ValueError(f"Subrecord {code}[{ordinal}] not found for 0x{record.form_id:08X}")

    def _replace_subrecord_payload(self, record: MutableRecord, code: str, payload: bytes, ordinal: int = 0) -> None:
        self._replace_payload(record, code, payload, ordinal=ordinal)
        self.model.mutable_record_form_ids.add(record.form_id)

    def _payload_from_subrecord(self, record: MutableRecord, code: str, ordinal: int = 0) -> bytes | None:
        found = 0
        for subrecord in record.subrecords:
            if subrecord.code != code:
                continue
            if found == ordinal:
                return subrecord.raw_payload
            found += 1
        return None

    def _string_from_subrecord(self, record: MutableRecord, code: str, ordinal: int = 0) -> str | None:
        payload = self._payload_from_subrecord(record, code, ordinal)
        return None if payload is None else self._decode_cstring(payload)

    def _int_from_subrecord(self, record: MutableRecord, code: str, ordinal: int = 0) -> int | None:
        payload = self._payload_from_subrecord(record, code, ordinal)
        if payload is None or len(payload) < 4:
            return None
        return int.from_bytes(payload[:4], "little")

    def _find_star_location_form_id(self, system_id: int, star_name: str | None = None) -> int:
        location = self.location_index.star_location(system_id, star_name=star_name)
        if location is None:
            raise ValueError(f"Destination star location was not found for system 0x{system_id:08X}.")
        return location.form_id

    def _find_planet_locations_by_local_id(self, system_id: int, local_id: int) -> list[MutableRecord]:
        indexed = self.location_index.locations_for_local_id(system_id, local_id)
        matches: list[MutableRecord] = []
        for info in (indexed.main, indexed.orbit, indexed.surface):
            if info is not None:
                matches.append(self.model.records_by_form_id[info.form_id])
        return matches

    def _read_star_position(self, source_star_form_id: int) -> tuple[float, float, float]:
        record = self._load_record(self.source_path, "STDT", source_star_form_id)
        payload = self._payload_from_subrecord(record, "BNAM")
        if payload is None or len(payload) < 12:
            return (0.0, 0.0, 0.0)
        return struct.unpack("<fff", payload[:12])

    def _build_star_location(self, display_name: str, system_id: int, *, form_id: int) -> MutableRecord:
        return self._make_location_record(
            form_id=form_id,
            edid=f"S{display_name}",
            display_name=display_name,
            keywords=[KW_LOC_TYPE_STAR_SYSTEM],
            parent_loc_form_id=FID_UNIVERSE,
            system_id=system_id,
            planet_pos=0,
        )

    def _build_planet_location(
        self,
        *,
        star_name: str,
        planet_name: str,
        system_id: int,
        parent_loc_form_id: int,
        local_id: int,
        is_moon: bool,
        form_id: int,
        parent_planet_name: str | None = None,
    ) -> MutableRecord:
        if is_moon:
            edid = f"S{star_name}_P{parent_planet_name}_M{planet_name}"
            keywords = [KW_LOC_TYPE_MOON, KW_LOC_TYPE_MAJOR_ORBITAL]
        else:
            edid = f"S{star_name}_P{planet_name}"
            keywords = [KW_LOC_TYPE_PLANET, KW_LOC_TYPE_MAJOR_ORBITAL]
        return self._make_location_record(
            form_id=form_id,
            edid=edid,
            display_name=planet_name,
            keywords=keywords,
            parent_loc_form_id=parent_loc_form_id,
            system_id=system_id,
            planet_pos=local_id,
        )

    def _build_child_location(
        self,
        *,
        edid: str,
        display_name: str,
        system_id: int,
        parent_loc_form_id: int,
        local_id: int,
        keyword: int,
        form_id: int,
    ) -> MutableRecord:
        return self._make_location_record(
            form_id=form_id,
            edid=edid,
            display_name=display_name,
            keywords=[keyword],
            parent_loc_form_id=parent_loc_form_id,
            system_id=system_id,
            planet_pos=local_id,
        )

    def _make_location_record(
        self,
        *,
        form_id: int,
        edid: str,
        display_name: str,
        keywords: list[int],
        parent_loc_form_id: int,
        system_id: int,
        planet_pos: int,
    ) -> MutableRecord:
        return MutableRecord(
            signature="LCTN",
            form_id=form_id,
            flags=0,
            revision=0,
            internal_version=0,
            unknown=0,
            was_compressed=False,
            subrecords=[
                MutableSubrecord(code="EDID", raw_payload=edid.encode("utf-8") + b"\x00"),
                MutableSubrecord(code="FULL", raw_payload=display_name.encode("utf-8") + b"\x00"),
                MutableSubrecord(code="KSIZ", raw_payload=len(keywords).to_bytes(4, "little")),
                MutableSubrecord(code="KWDA", raw_payload=b"".join(item.to_bytes(4, "little") for item in keywords)),
                MutableSubrecord(code="DATA", raw_payload=b"\x00\x00\x00\x00\x00\x4b\x10\xff"),
                MutableSubrecord(code="PNAM", raw_payload=parent_loc_form_id.to_bytes(4, "little")),
                MutableSubrecord(code="ANAM", raw_payload=struct.pack("<f", 1.0)),
                MutableSubrecord(code="XNAM", raw_payload=system_id.to_bytes(4, "little")),
                MutableSubrecord(code="YNAM", raw_payload=planet_pos.to_bytes(4, "little")),
            ],
        )

    def _plan_local_id_changes(self, system_id: int, *, is_moon: bool) -> tuple[int, dict[int, int]]:
        in_system = sorted(
            [item for item in self.view.planets if item.system_id == system_id], key=lambda item: item.local_id
        )
        if is_moon:
            return (max((item.local_id for item in in_system), default=0) + 1, {})
        first_moon = next((item for item in in_system if item.is_moon), None)
        if first_moon is None:
            return (max((item.local_id for item in in_system), default=0) + 1, {})
        updates = {
            item.form_id: item.local_id + 1
            for item in in_system
            if item.is_moon and item.local_id >= first_moon.local_id
        }
        return first_moon.local_id, updates

    def _apply_local_id_updates(self, system_id: int, updates: dict[int, int]) -> None:
        for form_id, new_local_id in updates.items():
            record = self.model.records_by_form_id[form_id]
            payload = self._payload_from_subrecord(record, "GNAM", ordinal=1)
            if payload is None or len(payload) < 12:
                continue
            old_local_id = int.from_bytes(payload[8:12], "little")
            replacement = payload[:8] + new_local_id.to_bytes(4, "little")
            self._replace_subrecord_payload(record, "GNAM", replacement, ordinal=1)
            for location in self._find_planet_locations_by_local_id(system_id, old_local_id):
                self._replace_subrecord_payload(location, "YNAM", new_local_id.to_bytes(4, "little"))
        self.location_index = LocationIndex.build(self.model)

    def _source_name_candidates(self, display_name: str | None, editor_id: str | None) -> tuple[str, ...]:
        candidates: list[str] = []
        for item in (display_name, editor_id):
            if item and item not in candidates:
                candidates.append(item)
        return tuple(candidates)

    def _predict_biom_output_path(self, destination_name: str) -> Path:
        return self.destination_path.parent / "planetdata" / "biomemaps" / f"{destination_name}.biom"

    def _decode_cstring(self, payload: bytes) -> str:
        return payload.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
