from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import pytest

SOURCE_SYSTEM_ID = 0x01002000
DESTINATION_SYSTEM_ID = 0x02003000


@dataclass(frozen=True)
class PluginFixtures:
    source: Path
    destination: Path
    empty: Path
    planet_archive: Path


def _subrecord(code: str, payload: bytes) -> bytes:
    return code.encode("ascii") + len(payload).to_bytes(2, "little") + payload


def _record(signature: str, form_id: int, subrecords: list[tuple[str, bytes]]) -> bytes:
    payload = b"".join(_subrecord(code, value) for code, value in subrecords)
    return (
        signature.encode("ascii")
        + len(payload).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + form_id.to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (0).to_bytes(2, "little")
        + payload
    )


def _group(signature: str, records: list[bytes]) -> bytes:
    content = b"".join(records)
    return (
        b"GRUP"
        + (24 + len(content)).to_bytes(4, "little")
        + signature.encode("ascii")
        + (0).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + content
    )


def _plugin(path: Path, groups: dict[str, list[bytes]], *, master: str | None = None) -> None:
    record_count = sum(len(records) for records in groups.values())
    header_subrecords = [
        ("HEDR", struct.pack("<fII", 1.0, record_count, 0x800)),
        ("CNAM", b"StarForge synthetic fixture\x00"),
    ]
    if master is not None:
        header_subrecords.append(("MAST", master.encode("utf-8") + b"\x00"))
    payload = b"".join(_subrecord(code, value) for code, value in header_subrecords)
    header = (
        b"TES4"
        + len(payload).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (0).to_bytes(2, "little")
        + payload
    )
    path.write_bytes(header + b"".join(_group(label, records) for label, records in groups.items()))


def _orbit(major_axis: float, eccentricity: float) -> bytes:
    minor_axis = major_axis * (1.0 - eccentricity * eccentricity) ** 0.5
    aphelion = major_axis * (1.0 + eccentricity)
    return struct.pack(
        "<ddddddffffII",
        major_axis,
        minor_axis,
        aphelion,
        eccentricity,
        0.1,
        0.5,
        0.2,
        1.0,
        0.0,
        0.0,
        1,
        0,
    )


def _body() -> bytes:
    return struct.pack("<dfffi", 10_883_000.0, 1.2, 5272.0, 0.9, 0)


def _star(form_id: int, editor_id: str, name: str, system_id: int) -> bytes:
    return _record(
        "STDT",
        form_id,
        [
            ("EDID", editor_id.encode() + b"\x00"),
            ("ANAM", name.encode() + b"\x00"),
            ("DNAM", system_id.to_bytes(4, "little")),
            ("BNAM", struct.pack("<fff", 10.0, 20.0, 30.0)),
        ],
    )


def _planet(
    form_id: int,
    editor_id: str,
    name: str,
    system_id: int,
    parent_local_id: int,
    local_id: int,
    major_axis: float,
) -> bytes:
    return _record(
        "PNDT",
        form_id,
        [
            ("EDID", editor_id.encode() + b"\x00"),
            ("ANAM", name.encode() + b"\x00"),
            ("GNAM", b"\x00" * 12),
            ("GNAM", struct.pack("<III", system_id, parent_local_id, local_id)),
            ("ENAM", _orbit(major_axis, 0.0069)),
            ("FNAM", _body()),
            ("BFCB", b"TESFullName_Component\x00"),
            ("FULL", name.encode() + b"\x00"),
            ("BFCE", b""),
        ],
    )


def _location(
    form_id: int,
    editor_id: str,
    name: str,
    system_id: int,
    local_id: int,
    keyword: int,
    parent_form_id: int,
) -> bytes:
    return _record(
        "LCTN",
        form_id,
        [
            ("EDID", editor_id.encode() + b"\x00"),
            ("FULL", name.encode() + b"\x00"),
            ("KSIZ", (1).to_bytes(4, "little")),
            ("KWDA", keyword.to_bytes(4, "little")),
            ("PNAM", parent_form_id.to_bytes(4, "little")),
            ("XNAM", system_id.to_bytes(4, "little")),
            ("YNAM", local_id.to_bytes(4, "little")),
        ],
    )


def _archive(path: Path) -> None:
    name = b"planetdata/biomemaps/Synthetic Prime.biom"
    payload = b"STARFORGE_SYNTHETIC_BIOM_FIXTURE"
    name_offset = 72
    data_offset = name_offset + 2 + len(name)
    header = struct.pack("<4sI4sIQQ", b"BTDX", 1, b"GNRL", 1, name_offset, 0) + b"\x00" * 4
    entry = struct.pack("<4sIIQIIQ", b"biom", 0, 0, data_offset, 0, len(payload), 0)
    path.write_bytes(header + entry + struct.pack("<H", len(name)) + name + payload)


@pytest.fixture(scope="session")
def plugin_fixtures(tmp_path_factory: pytest.TempPathFactory) -> PluginFixtures:
    root = tmp_path_factory.mktemp("starforge-public-fixtures")
    source = root / "source.esm"
    destination = root / "destination.esp"
    empty = root / "empty.esm"
    archive = root / "Starfield - PlanetData.ba2"

    source_star = _star(0x100, "SyntheticSourceStar", "Synthetic Source", SOURCE_SYSTEM_ID)
    source_planet = _planet(
        0x101,
        "SyntheticPrimePlanetData",
        "Synthetic Prime",
        SOURCE_SYSTEM_ID,
        0,
        1,
        80_000.0,
    )
    _plugin(source, {"STDT": [source_star], "PNDT": [source_planet]})

    destination_star = _star(0x200, "WorkshopStar", "Workshop", DESTINATION_SYSTEM_ID)
    destination_planet = _planet(
        0x201,
        "WorkshopPrimePlanetData",
        "Workshop Prime",
        DESTINATION_SYSTEM_ID,
        0,
        1,
        95_000.0,
    )
    destination_moon = _planet(
        0x202,
        "WorkshopMoonPlanetData",
        "Workshop Moon",
        DESTINATION_SYSTEM_ID,
        1,
        9,
        20_000.0,
    )
    star_location = _location(0x300, "SWorkshop", "Workshop", DESTINATION_SYSTEM_ID, 0, 0x149F, 0x1A53A)
    moon_location = _location(
        0x301, "SWorkshop_PWorkshopPrime_MWorkshopMoon", "Workshop Moon", DESTINATION_SYSTEM_ID, 9, 0x16010, 0x300
    )
    moon_orbit = _location(
        0x302, "SWorkshop_PWorkshopPrime_MWorkshopMoon_Orbit", "Workshop Moon", DESTINATION_SYSTEM_ID, 9, 0x16504, 0x301
    )
    moon_surface = _location(
        0x303,
        "SWorkshop_PWorkshopPrime_MWorkshopMoon_Surface",
        "Workshop Moon",
        DESTINATION_SYSTEM_ID,
        9,
        0x16503,
        0x301,
    )
    _plugin(
        destination,
        {
            "STDT": [destination_star],
            "PNDT": [destination_planet, destination_moon],
            "LCTN": [star_location, moon_location, moon_orbit, moon_surface],
        },
        master="Starfield.esm",
    )
    _plugin(empty, {})
    _archive(archive)
    return PluginFixtures(source, destination, empty, archive)
