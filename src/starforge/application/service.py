from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from ..core.models import ClonePreview
from ..core.session import StarForgeSession
from ..formats import PluginReader
from ..formats.exceptions import PluginFormatError
from .models import (
    ApplicationError,
    CancellationToken,
    ClonePlanetRequest,
    CloneStarRequest,
    ExitCode,
    OperationResult,
    OperationWarning,
    OrbitPresetRequest,
    OrbitUpdateRequest,
    ProgressUpdate,
    ProjectSpec,
    to_json_value,
)

ProgressCallback = Callable[[ProgressUpdate], None]


class StarForgeApplication:
    def inspect(self, plugin_path: Path) -> OperationResult:
        path = self._require_plugin(plugin_path)
        try:
            reader = PluginReader()
            header = reader.read_header(path)
            stars = reader.read_direct_records(path, "STDT")
            planets = reader.read_direct_records(path, "PNDT")
            session = StarForgeSession(path, path)
        except (OSError, PluginFormatError, ValueError) as exc:
            raise ApplicationError(str(exc), code="invalid_plugin", exit_code=ExitCode.INPUT_ERROR) from exc
        return OperationResult(
            operation="inspect",
            data={
                "path": path,
                "size": path.stat().st_size,
                "masters": header.masters,
                "record_count": header.hedr.record_count if header.hedr else None,
                "next_object_id": header.hedr.next_object_id if header.hedr else None,
                "star_count": len(stars),
                "planet_count": len(planets),
                "stars": session.view.stars,
                "planets": session.view.planets,
            },
        )

    def validate(self, plugin_path: Path) -> OperationResult:
        inspected = self.inspect(plugin_path)
        return OperationResult(operation="validate", data={"valid": True, **inspected.data})

    def create_project(
        self, project_path: Path, source_path: Path, destination_path: Path, *, overwrite: bool = False
    ) -> OperationResult:
        source = self._require_plugin(source_path)
        destination = self._require_plugin(destination_path)
        if source.resolve() == destination.resolve():
            raise ApplicationError(
                "Source and destination plugins must differ.",
                code="same_input_paths",
                exit_code=ExitCode.INPUT_ERROR,
            )
        project = ProjectSpec(source.resolve(), destination.resolve())
        self._atomic_json_write(project_path, project.to_dict(), overwrite=overwrite)
        return OperationResult("project.create", project.to_dict(), changed=True, output_path=project_path)

    def load_project(self, project_path: Path) -> ProjectSpec:
        try:
            data = json.loads(project_path.read_text(encoding="utf-8"))
            if data.get("schema_version") != 1:
                raise ValueError("Unsupported project schema version.")
            return ProjectSpec(
                source_path=self._require_plugin(Path(data["source_path"])),
                destination_path=self._require_plugin(Path(data["destination_path"])),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ApplicationError(str(exc), code="invalid_project", exit_code=ExitCode.INPUT_ERROR) from exc

    def preview_clone_star(self, request: CloneStarRequest) -> OperationResult:
        session = self._session(request.source_path, request.destination_path)
        try:
            preview = session.preview_star_clone(
                source_star_form_id=request.source_form_id,
                new_editor_id=request.editor_id,
                new_display_name=request.display_name,
                system_id=request.system_id,
                position=request.position,
            )
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        return self._preview_result("clone.star.preview", preview)

    def preview_clone_planet(self, request: ClonePlanetRequest, *, moon: bool = False) -> OperationResult:
        session = self._session(request.source_path, request.destination_path)
        try:
            if moon:
                preview = session.preview_moon_clone(
                    source_moon_form_id=request.source_form_id,
                    destination_parent_planet_form_id=request.destination_form_id,
                    new_editor_id=request.editor_id,
                    new_display_name=request.display_name,
                    extract_biom=request.extract_biom,
                )
            else:
                preview = session.preview_planet_clone(
                    source_planet_form_id=request.source_form_id,
                    destination_star_form_id=request.destination_form_id,
                    new_editor_id=request.editor_id,
                    new_display_name=request.display_name,
                    extract_biom=request.extract_biom,
                )
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        return self._preview_result(f"clone.{'moon' if moon else 'planet'}.preview", preview)

    def apply_clone_star(
        self,
        request: CloneStarRequest,
        output_path: Path,
        *,
        overwrite: bool = False,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
    ) -> OperationResult:
        token = cancellation or CancellationToken()
        self._progress(progress, "clone.star.apply", 0.0, "Loading plugins")
        token.raise_if_cancelled()
        session = self._session(request.source_path, request.destination_path)
        try:
            preview = session.preview_star_clone(
                source_star_form_id=request.source_form_id,
                new_editor_id=request.editor_id,
                new_display_name=request.display_name,
                system_id=request.system_id,
                position=request.position,
            )
            if preview.hard_errors:
                raise ValueError("\n".join(preview.hard_errors))
            token.raise_if_cancelled()
            new_form_id = session.create_star_from_source(
                source_star_form_id=request.source_form_id,
                new_editor_id=request.editor_id,
                new_display_name=request.display_name,
                system_id=request.system_id,
                position=request.position,
            )
            self._progress(progress, "clone.star.apply", 0.65, "Writing output")
            self._atomic_session_write(session, output_path, overwrite=overwrite, cancellation=token)
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        self._progress(progress, "clone.star.apply", 1.0, "Complete")
        return OperationResult(
            "clone.star.apply",
            {"form_id": new_form_id, "preview": preview.draft.preview_lines},
            changed=True,
            output_path=output_path,
            warnings=self._clone_warnings(preview),
        )

    def apply_clone_planet(
        self,
        request: ClonePlanetRequest,
        output_path: Path,
        *,
        moon: bool = False,
        overwrite: bool = False,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
    ) -> OperationResult:
        token = cancellation or CancellationToken()
        operation = f"clone.{'moon' if moon else 'planet'}.apply"
        self._progress(progress, operation, 0.0, "Loading plugins")
        token.raise_if_cancelled()
        session = self._session(request.source_path, request.destination_path)
        try:
            preview_result = self.preview_clone_planet(request, moon=moon)
            if not preview_result.data["valid"]:
                raise ValueError("\n".join(preview_result.data["errors"]))
            if moon:
                preview = session.preview_moon_clone(
                    source_moon_form_id=request.source_form_id,
                    destination_parent_planet_form_id=request.destination_form_id,
                    new_editor_id=request.editor_id,
                    new_display_name=request.display_name,
                    extract_biom=request.extract_biom,
                )
            else:
                preview = session.preview_planet_clone(
                    source_planet_form_id=request.source_form_id,
                    destination_star_form_id=request.destination_form_id,
                    new_editor_id=request.editor_id,
                    new_display_name=request.display_name,
                    extract_biom=request.extract_biom,
                )
            token.raise_if_cancelled()
            if moon:
                new_form_id, biom = session.create_moon_from_source(
                    source_moon_form_id=request.source_form_id,
                    destination_parent_planet_form_id=request.destination_form_id,
                    new_editor_id=request.editor_id,
                    new_display_name=request.display_name,
                    extract_biom=request.extract_biom,
                )
            else:
                new_form_id, biom = session.create_planet_from_source(
                    source_planet_form_id=request.source_form_id,
                    destination_star_form_id=request.destination_form_id,
                    new_editor_id=request.editor_id,
                    new_display_name=request.display_name,
                    extract_biom=request.extract_biom,
                )
            self._progress(progress, operation, 0.65, "Writing output")
            self._atomic_session_write(session, output_path, overwrite=overwrite, cancellation=token)
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        self._progress(progress, operation, 1.0, "Complete")
        return OperationResult(
            operation,
            {"form_id": new_form_id, "biom": to_json_value(biom), "preview": preview.draft.preview_lines},
            changed=True,
            output_path=output_path,
            warnings=self._clone_warnings(preview),
        )

    def apply_orbit_preset(
        self,
        request: OrbitPresetRequest,
        output_path: Path,
        *,
        overwrite: bool = False,
        cancellation: CancellationToken | None = None,
    ) -> OperationResult:
        token = cancellation or CancellationToken()
        token.raise_if_cancelled()
        session = self._session(request.source_path, request.destination_path)
        try:
            orbit = session.apply_preset(request.planet_form_id, request.preset)
            self._atomic_session_write(session, output_path, overwrite=overwrite, cancellation=token)
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        return OperationResult(
            "orbit.preset.apply",
            {"planet_form_id": request.planet_form_id, "preset": request.preset, "orbit": orbit},
            changed=True,
            output_path=output_path,
        )

    def preview_orbit_update(self, request: OrbitUpdateRequest) -> OperationResult:
        session = self._session(request.source_path, request.destination_path)
        try:
            planet = next(item for item in session.view.planets if item.form_id == request.planet_form_id)
            if planet.orbit is None:
                raise ValueError("Planet record has no orbital data.")
            orbit = request.apply_to(planet.orbit)
            session.set_planet_orbit(request.planet_form_id, orbit)
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        return OperationResult("orbit.update.preview", {"planet_form_id": request.planet_form_id, "orbit": orbit})

    def apply_orbit_update(
        self,
        request: OrbitUpdateRequest,
        output_path: Path,
        *,
        overwrite: bool = False,
        cancellation: CancellationToken | None = None,
    ) -> OperationResult:
        token = cancellation or CancellationToken()
        token.raise_if_cancelled()
        session = self._session(request.source_path, request.destination_path)
        try:
            planet = next(item for item in session.view.planets if item.form_id == request.planet_form_id)
            if planet.orbit is None:
                raise ValueError("Planet record has no orbital data.")
            orbit = request.apply_to(planet.orbit)
            session.set_planet_orbit(request.planet_form_id, orbit)
            self._atomic_session_write(session, output_path, overwrite=overwrite, cancellation=token)
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        return OperationResult(
            "orbit.update.apply",
            {"planet_form_id": request.planet_form_id, "orbit": orbit},
            changed=True,
            output_path=output_path,
        )

    def apply_system_id(
        self,
        source_path: Path,
        destination_path: Path,
        star_form_id: int,
        system_id: int,
        output_path: Path,
        *,
        overwrite: bool = False,
    ) -> OperationResult:
        session = self._session(source_path, destination_path)
        try:
            session.set_star_system_id(star_form_id, system_id)
            self._atomic_session_write(session, output_path, overwrite=overwrite)
        except (KeyError, StopIteration, ValueError) as exc:
            raise self._validation_error(exc) from exc
        return OperationResult(
            "system-id.apply",
            {"star_form_id": star_form_id, "system_id": system_id},
            changed=True,
            output_path=output_path,
        )

    def _session(self, source_path: Path, destination_path: Path) -> StarForgeSession:
        source = self._require_plugin(source_path)
        destination = self._require_plugin(destination_path)
        if source.resolve() == destination.resolve():
            raise ApplicationError(
                "Source and destination plugins must differ.",
                code="same_input_paths",
                exit_code=ExitCode.INPUT_ERROR,
            )
        try:
            return StarForgeSession(source, destination)
        except (OSError, ValueError) as exc:
            raise ApplicationError(str(exc), code="invalid_plugin", exit_code=ExitCode.INPUT_ERROR) from exc

    def _atomic_session_write(
        self,
        session: StarForgeSession,
        output_path: Path,
        *,
        overwrite: bool,
        cancellation: CancellationToken | None = None,
    ) -> None:
        output = output_path.resolve()
        source = session.source_path.resolve()
        destination = session.destination_path.resolve()
        if output == source:
            raise ApplicationError(
                "The source plugin can never be overwritten.",
                code="source_overwrite_blocked",
                exit_code=ExitCode.INPUT_ERROR,
            )
        if output.exists() and not overwrite:
            raise ApplicationError(
                f"Output already exists: {output}. Pass --overwrite to replace it.",
                code="output_exists",
                exit_code=ExitCode.INPUT_ERROR,
            )
        if output == destination and not overwrite:
            raise ApplicationError(
                "The destination input is not overwritten by default. Choose another output or pass --overwrite.",
                code="destination_overwrite_blocked",
                exit_code=ExitCode.INPUT_ERROR,
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.stem}.{uuid4().hex}.tmp{output.suffix}")
        try:
            if cancellation:
                cancellation.raise_if_cancelled()
            session.save_as(temporary)
            self.validate(temporary)
            if cancellation:
                cancellation.raise_if_cancelled()
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)

    def _atomic_json_write(self, path: Path, data: dict[str, object], *, overwrite: bool) -> None:
        output = path.resolve()
        if output.exists() and not overwrite:
            raise ApplicationError(
                f"Output already exists: {output}. Pass --overwrite to replace it.",
                code="output_exists",
                exit_code=ExitCode.INPUT_ERROR,
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)

    def _require_plugin(self, path: Path) -> Path:
        candidate = path.expanduser()
        if not candidate.is_file():
            raise ApplicationError(
                f"Plugin does not exist: {candidate}", code="input_not_found", exit_code=ExitCode.INPUT_ERROR
            )
        return candidate

    def _preview_result(self, operation: str, preview: ClonePreview) -> OperationResult:
        hard_errors = preview.hard_errors
        draft = preview.draft
        return OperationResult(
            operation,
            {"valid": not hard_errors, "errors": hard_errors, "draft": draft},
            warnings=self._clone_warnings(preview),
        )

    def _clone_warnings(self, preview: ClonePreview) -> tuple[OperationWarning, ...]:
        draft = preview.draft
        return tuple(OperationWarning("component_rewrite", item.message) for item in draft.rewrite_warnings)

    def _validation_error(self, error: Exception) -> ApplicationError:
        return ApplicationError(str(error), code="validation_failed", exit_code=ExitCode.VALIDATION_ERROR)

    def _progress(self, callback: ProgressCallback | None, operation: str, fraction: float, message: str) -> None:
        if callback:
            callback(ProgressUpdate(operation, fraction, message))
