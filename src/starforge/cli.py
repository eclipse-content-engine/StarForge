from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Never

from .application import (
    ApplicationError,
    ClonePlanetRequest,
    CloneStarRequest,
    ExitCode,
    OrbitPresetRequest,
    OrbitUpdateRequest,
    StarForgeApplication,
)


class StarForgeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ApplicationError(message, code="invalid_arguments", exit_code=ExitCode.USAGE)


def _integer(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc


def _add_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", type=Path, required=True, help="Source plugin used for clone templates")
    parser.add_argument("--destination", type=Path, required=True, help="Destination plugin to edit in memory")


def _add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", type=Path, required=True, help="New plugin path")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly allow replacement of an existing output")


def _add_clone_identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-form-id", type=_integer, required=True)
    parser.add_argument("--editor-id", required=True)
    parser.add_argument("--display-name", required=True)


def _add_orbit_fields(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--planet-form-id", type=_integer, required=True)
    for field in (
        "major-axis",
        "minor-axis",
        "aphelion",
        "eccentricity",
        "incline-radians",
        "mean-orbit",
        "axial-tilt-radians",
        "rotational-velocity",
        "start-angle",
        "perihelion-angle",
    ):
        parser.add_argument(f"--{field}", type=float)
    parser.add_argument("--apply-orbital-motion", action=argparse.BooleanOptionalAction)
    parser.add_argument("--geostationary", action=argparse.BooleanOptionalAction)


def build_parser() -> argparse.ArgumentParser:
    parser = StarForgeArgumentParser(prog="starforge", description="Safe Starfield plugin authoring")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit stable machine-readable JSON")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Never prompt (currently the default for every CLI operation)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_parser = commands.add_parser("inspect", help="Inspect a plugin without modifying it")
    inspect_parser.add_argument("plugin", type=Path)

    validate_parser = commands.add_parser("validate", help="Validate that a plugin can be parsed")
    validate_parser.add_argument("plugin", type=Path)

    project_parser = commands.add_parser("project", help="Manage StarForge project files")
    project_commands = project_parser.add_subparsers(dest="project_command", required=True)
    project_create = project_commands.add_parser("create", help="Create a project file")
    project_create.add_argument("project", type=Path)
    _add_inputs(project_create)
    project_create.add_argument("--overwrite", action="store_true")
    project_show = project_commands.add_parser("show", help="Show resolved project inputs")
    project_show.add_argument("project", type=Path)

    preview_parser = commands.add_parser("preview", help="Create a non-mutating clone preview")
    preview_commands = preview_parser.add_subparsers(dest="preview_command", required=True)
    for kind in ("star", "planet", "moon"):
        clone = preview_commands.add_parser(kind)
        _add_inputs(clone)
        _add_clone_identity(clone)
        if kind == "star":
            clone.add_argument("--system-id", type=_integer, required=True)
            clone.add_argument("--position", nargs=3, type=float, metavar=("X", "Y", "Z"))
        else:
            clone.add_argument(
                "--destination-form-id",
                type=_integer,
                required=True,
                help="Destination star form ID for planets or parent planet form ID for moons",
            )
            clone.add_argument("--extract-biom", action="store_true")
    orbit_preview = preview_commands.add_parser("orbit", help="Validate an orbit edit without writing")
    _add_inputs(orbit_preview)
    _add_orbit_fields(orbit_preview)

    apply_parser = commands.add_parser("apply", help="Apply one edit and atomically write a new plugin")
    apply_commands = apply_parser.add_subparsers(dest="apply_command", required=True)
    for kind in ("star", "planet", "moon"):
        clone = apply_commands.add_parser(kind)
        _add_inputs(clone)
        _add_output(clone)
        _add_clone_identity(clone)
        if kind == "star":
            clone.add_argument("--system-id", type=_integer, required=True)
            clone.add_argument("--position", nargs=3, type=float, metavar=("X", "Y", "Z"))
        else:
            clone.add_argument("--destination-form-id", type=_integer, required=True)
            clone.add_argument("--extract-biom", action="store_true")

    orbit_parser = commands.add_parser("orbit", help="Edit orbital data")
    orbit_commands = orbit_parser.add_subparsers(dest="orbit_command", required=True)
    orbit_preset = orbit_commands.add_parser("preset", help="Apply a named orbit preset")
    _add_inputs(orbit_preset)
    _add_output(orbit_preset)
    orbit_preset.add_argument("--planet-form-id", type=_integer, required=True)
    orbit_preset.add_argument("--preset", required=True)
    orbit_set = orbit_commands.add_parser("set", help="Set one or more orbital fields")
    _add_inputs(orbit_set)
    _add_output(orbit_set)
    _add_orbit_fields(orbit_set)

    system_parser = commands.add_parser("system-id", help="Change a star system ID")
    _add_inputs(system_parser)
    _add_output(system_parser)
    system_parser.add_argument("--star-form-id", type=_integer, required=True)
    system_parser.add_argument("--system-id", type=_integer, required=True)

    commands.add_parser("gui", help="Launch the desktop application")
    return parser


def _star_request(args: argparse.Namespace) -> CloneStarRequest:
    return CloneStarRequest(
        source_path=args.source,
        destination_path=args.destination,
        source_form_id=args.source_form_id,
        editor_id=args.editor_id,
        display_name=args.display_name,
        system_id=args.system_id,
        position=tuple(args.position) if args.position else None,
    )


def _planet_request(args: argparse.Namespace) -> ClonePlanetRequest:
    return ClonePlanetRequest(
        source_path=args.source,
        destination_path=args.destination,
        source_form_id=args.source_form_id,
        destination_form_id=args.destination_form_id,
        editor_id=args.editor_id,
        display_name=args.display_name,
        extract_biom=args.extract_biom,
    )


def _orbit_request(args: argparse.Namespace) -> OrbitUpdateRequest:
    return OrbitUpdateRequest(
        source_path=args.source,
        destination_path=args.destination,
        planet_form_id=args.planet_form_id,
        major_axis=args.major_axis,
        minor_axis=args.minor_axis,
        aphelion=args.aphelion,
        eccentricity=args.eccentricity,
        incline_radians=args.incline_radians,
        mean_orbit=args.mean_orbit,
        axial_tilt_radians=args.axial_tilt_radians,
        rotational_velocity=args.rotational_velocity,
        start_angle=args.start_angle,
        perihelion_angle=args.perihelion_angle,
        apply_orbital_motion=args.apply_orbital_motion,
        geostationary=args.geostationary,
    )


def _execute(args: argparse.Namespace, application: StarForgeApplication) -> Any:
    if args.command == "inspect":
        return application.inspect(args.plugin)
    if args.command == "validate":
        return application.validate(args.plugin)
    if args.command == "project":
        if args.project_command == "create":
            return application.create_project(args.project, args.source, args.destination, overwrite=args.overwrite)
        project = application.load_project(args.project)
        from .application.models import OperationResult

        return OperationResult("project.show", project.to_dict())
    if args.command == "preview":
        if args.preview_command == "orbit":
            return application.preview_orbit_update(_orbit_request(args))
        if args.preview_command == "star":
            return application.preview_clone_star(_star_request(args))
        return application.preview_clone_planet(_planet_request(args), moon=args.preview_command == "moon")
    if args.command == "apply":
        if args.apply_command == "star":
            return application.apply_clone_star(
                _star_request(args), args.output, overwrite=args.overwrite, progress=_progress(args)
            )
        return application.apply_clone_planet(
            _planet_request(args),
            args.output,
            moon=args.apply_command == "moon",
            overwrite=args.overwrite,
            progress=_progress(args),
        )
    if args.command == "orbit":
        if args.orbit_command == "set":
            return application.apply_orbit_update(_orbit_request(args), args.output, overwrite=args.overwrite)
        request = OrbitPresetRequest(args.source, args.destination, args.planet_form_id, args.preset)
        return application.apply_orbit_preset(request, args.output, overwrite=args.overwrite)
    if args.command == "system-id":
        return application.apply_system_id(
            args.source,
            args.destination,
            args.star_form_id,
            args.system_id,
            args.output,
            overwrite=args.overwrite,
        )
    if args.command == "gui":
        from .ui.app import run as run_gui

        return run_gui()
    raise ApplicationError("Unknown command.", code="invalid_arguments", exit_code=ExitCode.USAGE)


def _progress(args: argparse.Namespace) -> Any:
    if args.json_output:
        return None

    def report(update: Any) -> None:
        print(f"[{update.fraction:>4.0%}] {update.message}", file=sys.stderr)

    return report


def _print_result(result: Any, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return
    print(f"{result.operation}: success")
    if result.output_path:
        print(f"Output: {result.output_path}")
    for warning in result.warnings:
        print(f"Warning: {warning.message}", file=sys.stderr)
    for key, value in result.data.items():
        if key == "draft" and hasattr(value, "preview_lines"):
            for line in value.preview_lines:
                print(f"  {line}")
        else:
            print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    operation = "cli"
    json_output = "--json" in (argv if argv is not None else sys.argv[1:])
    try:
        args = parser.parse_args(argv)
        json_output = args.json_output
        operation = args.command
        result = _execute(args, StarForgeApplication())
        if isinstance(result, int):
            return result
        _print_result(result, json_output=json_output)
        return ExitCode.SUCCESS
    except ApplicationError as exc:
        if json_output:
            print(json.dumps(exc.to_dict(operation), indent=2, sort_keys=True))
        else:
            print(f"Error [{exc.code}]: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        error = ApplicationError("Operation cancelled.", code="operation_cancelled", exit_code=ExitCode.CANCELLED)
        if json_output:
            print(json.dumps(error.to_dict(operation), indent=2, sort_keys=True))
        else:
            print("Operation cancelled.", file=sys.stderr)
        return ExitCode.CANCELLED
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        error = ApplicationError(
            f"Unexpected internal error: {exc}", code="internal_error", exit_code=ExitCode.INTERNAL_ERROR
        )
        if json_output:
            print(json.dumps(error.to_dict(operation), indent=2, sort_keys=True))
        else:
            print(f"Error [{error.code}]: {error}", file=sys.stderr)
        return ExitCode.INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
