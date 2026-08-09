from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import IntEnum
from pathlib import Path
from threading import Event
from typing import Any

from ..core.models import OrbitalElements


class ExitCode(IntEnum):
    SUCCESS = 0
    USAGE = 2
    INPUT_ERROR = 3
    VALIDATION_ERROR = 4
    CANCELLED = 5
    INTERNAL_ERROR = 10


@dataclass(frozen=True)
class OperationWarning:
    code: str
    message: str


@dataclass(frozen=True)
class ProgressUpdate:
    operation: str
    fraction: float
    message: str


@dataclass(frozen=True)
class OperationResult:
    operation: str
    data: dict[str, Any]
    changed: bool = False
    output_path: Path | None = None
    warnings: tuple[OperationWarning, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "operation": self.operation,
            "success": True,
            "changed": self.changed,
            "output_path": str(self.output_path) if self.output_path else None,
            "warnings": to_json_value(self.warnings),
            "data": to_json_value(self.data),
        }


@dataclass(frozen=True)
class ProjectSpec:
    source_path: Path
    destination_path: Path
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_path": str(self.source_path),
            "destination_path": str(self.destination_path),
        }


@dataclass(frozen=True)
class CloneStarRequest:
    source_path: Path
    destination_path: Path
    source_form_id: int
    editor_id: str
    display_name: str
    system_id: int
    position: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class ClonePlanetRequest:
    source_path: Path
    destination_path: Path
    source_form_id: int
    destination_form_id: int
    editor_id: str
    display_name: str
    extract_biom: bool = False


@dataclass(frozen=True)
class OrbitPresetRequest:
    source_path: Path
    destination_path: Path
    planet_form_id: int
    preset: str


@dataclass(frozen=True)
class OrbitUpdateRequest:
    source_path: Path
    destination_path: Path
    planet_form_id: int
    major_axis: float | None = None
    minor_axis: float | None = None
    aphelion: float | None = None
    eccentricity: float | None = None
    incline_radians: float | None = None
    mean_orbit: float | None = None
    axial_tilt_radians: float | None = None
    rotational_velocity: float | None = None
    start_angle: float | None = None
    perihelion_angle: float | None = None
    apply_orbital_motion: bool | None = None
    geostationary: bool | None = None

    def apply_to(self, orbit: OrbitalElements) -> OrbitalElements:
        values = {
            field: value
            for field, value in self.__dict__.items()
            if field not in {"source_path", "destination_path", "planet_form_id"} and value is not None
        }
        if not values:
            raise ValueError("At least one orbital field must be supplied.")
        from dataclasses import replace
        from math import sqrt

        major = float(values.get("major_axis", orbit.major_axis))
        eccentricity = float(values.get("eccentricity", orbit.eccentricity))
        if "minor_axis" not in values and ("major_axis" in values or "eccentricity" in values):
            values["minor_axis"] = major * sqrt(max(1.0 - eccentricity * eccentricity, 0.0))
        if "aphelion" not in values and ("major_axis" in values or "eccentricity" in values):
            values["aphelion"] = major * (1.0 + eccentricity)
        return replace(orbit, **values)


class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise OperationCancelledError()


class ApplicationError(Exception):
    def __init__(self, message: str, *, code: str, exit_code: ExitCode) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code

    def to_dict(self, operation: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "operation": operation,
            "success": False,
            "error": {"code": self.code, "message": str(self)},
        }


class OperationCancelledError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("Operation cancelled.", code="operation_cancelled", exit_code=ExitCode.CANCELLED)


def to_json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {key: to_json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [to_json_value(item) for item in value]
    return value
