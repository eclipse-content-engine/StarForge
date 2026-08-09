from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..core.models import CloneDraft, ClonePreview, EditorState, OrbitalElements, SessionView
from ..core.session import StarForgeSession
from .models import CancellationToken, OperationResult, ProgressUpdate
from .service import StarForgeApplication

ProgressCallback = Callable[[ProgressUpdate], None]


class Workspace:
    """Stateful application facade shared by the desktop workflow."""

    def __init__(self, session: StarForgeSession) -> None:
        self._session = session
        self._applied_draft_summaries: list[str] = []

    @classmethod
    def open(
        cls,
        source_path: Path,
        destination_path: Path,
        *,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
    ) -> Workspace:
        token = cancellation or CancellationToken()
        if progress:
            progress(ProgressUpdate("workspace.open", 0.05, "Checking project inputs"))
        token.raise_if_cancelled()
        app = StarForgeApplication()
        app.inspect(source_path)
        app.inspect(destination_path)
        if source_path.resolve() == destination_path.resolve():
            from .models import ApplicationError, ExitCode

            raise ApplicationError(
                "Source and destination plugins must differ.",
                code="same_input_paths",
                exit_code=ExitCode.INPUT_ERROR,
            )
        if progress:
            progress(ProgressUpdate("workspace.open", 0.35, "Reading plugin records"))
        token.raise_if_cancelled()
        workspace = cls(StarForgeSession(source_path, destination_path))
        token.raise_if_cancelled()
        if progress:
            progress(ProgressUpdate("workspace.open", 1.0, "Project ready"))
        return workspace

    @property
    def view(self) -> SessionView:
        return self._session.view

    @property
    def state(self) -> EditorState:
        return self._session.state

    @property
    def source_path(self) -> Path:
        return self._session.source_path

    @property
    def destination_path(self) -> Path:
        return self._session.destination_path

    @property
    def drafts(self) -> tuple[CloneDraft, ...]:
        return self._session.state.draft_previews

    @property
    def pending_change_count(self) -> int:
        pending = self.state.pending
        return (
            len(pending.changed_star_ids)
            + len(pending.changed_orbits)
            + len(pending.staged_draft_ids)
            + len(self._applied_draft_summaries)
        )

    @property
    def applied_change_summaries(self) -> tuple[str, ...]:
        star_names = {star.form_id: star.display_name or star.editor_id for star in self.view.stars}
        planet_names = {planet.form_id: planet.display_name or planet.editor_id for planet in self.view.planets}
        summaries = [
            f"SYSTEM ID  {star_names.get(form_id) or 'Unnamed star'}  ·  Form 0x{form_id:08X}"
            for form_id in self.state.pending.changed_star_ids
        ]
        summaries.extend(
            f"ORBIT  {planet_names.get(form_id) or 'Unnamed body'}  ·  Form 0x{form_id:08X}"
            for form_id in self.state.pending.changed_orbits
        )
        summaries.extend(self._applied_draft_summaries)
        return tuple(summaries)

    def allocate_system_id(self) -> int:
        return self._session.allocate_system_id()

    def set_star_system_id(self, star_form_id: int, new_system_id: int) -> OperationResult:
        self._session.set_star_system_id(star_form_id, new_system_id)
        return OperationResult(
            "system-id.stage",
            {"star_form_id": star_form_id, "system_id": new_system_id},
            changed=True,
        )

    def set_planet_orbit(self, planet_form_id: int, orbit: OrbitalElements) -> OperationResult:
        self._session.set_planet_orbit(planet_form_id, orbit)
        return OperationResult(
            "orbit.stage",
            {"planet_form_id": planet_form_id, "orbit": orbit},
            changed=True,
        )

    def apply_preset(self, planet_form_id: int, preset_key: str) -> OrbitalElements:
        return self._session.apply_preset(planet_form_id, preset_key)

    def preview_star_clone(
        self,
        *,
        source_star_form_id: int,
        new_editor_id: str,
        new_display_name: str,
        system_id: int,
        position: tuple[float, float, float] | None = None,
    ) -> ClonePreview:
        return self._session.preview_star_clone(
            source_star_form_id=source_star_form_id,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            system_id=system_id,
            position=position,
        )

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
        return self._session.preview_planet_clone(
            source_planet_form_id=source_planet_form_id,
            destination_star_form_id=destination_star_form_id,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            extract_biom=extract_biom,
            orbit_override=orbit_override,
        )

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
        return self._session.preview_moon_clone(
            source_moon_form_id=source_moon_form_id,
            destination_parent_planet_form_id=destination_parent_planet_form_id,
            new_editor_id=new_editor_id,
            new_display_name=new_display_name,
            extract_biom=extract_biom,
            orbit_override=orbit_override,
        )

    def stage_draft(self, preview: ClonePreview) -> CloneDraft:
        return self._session.stage_draft(preview)

    def discard_draft(self, draft_id: str) -> None:
        self._session.discard_draft(draft_id)

    def apply_draft(self, draft_id: str) -> None:
        draft = next(draft for draft in self.drafts if draft.draft_id == draft_id)
        self._session.apply_draft(draft_id)
        self._applied_draft_summaries.append(
            f"CREATE {draft.kind.upper()}  {draft.new_display_name}  ·  Draft {draft.draft_id}"
        )

    def apply_all_drafts(self) -> None:
        drafts = self.drafts
        self._session.apply_all_drafts()
        self._applied_draft_summaries.extend(
            f"CREATE {draft.kind.upper()}  {draft.new_display_name}  ·  Draft {draft.draft_id}" for draft in drafts
        )

    def export(
        self,
        output_path: Path,
        *,
        overwrite: bool = False,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
    ) -> OperationResult:
        token = cancellation or CancellationToken()
        token.raise_if_cancelled()
        if progress:
            progress(ProgressUpdate("workspace.export", 0.1, "Preparing output"))
        StarForgeApplication().export_session(self._session, output_path, overwrite=overwrite, cancellation=token)
        self.state.output_path = output_path
        self.state.status_text = f"Validated output saved to {output_path}."
        if progress:
            progress(ProgressUpdate("workspace.export", 1.0, "Output validated and published"))
        return OperationResult(
            "workspace.export",
            {"pending_change_count": self.pending_change_count},
            changed=True,
            output_path=output_path,
        )
