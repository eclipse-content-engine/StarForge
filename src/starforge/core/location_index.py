from __future__ import annotations

from dataclasses import dataclass

from .models import IndexedLocationSet, LocationRecordInfo
from .plugin_model import MutablePluginModel, MutableRecord

KW_LOC_TYPE_STAR_SYSTEM = 0x149F
KW_LOC_TYPE_PLANET = 0x14A0
KW_LOC_TYPE_MOON = 0x16010
KW_LOC_TYPE_SURFACE = 0x16503
KW_LOC_TYPE_ORBIT = 0x16504


@dataclass(frozen=True)
class LocationIndex:
    locations_by_form_id: dict[int, LocationRecordInfo]
    star_by_system_id: dict[int, LocationRecordInfo]
    by_system_local_id: dict[tuple[int, int], IndexedLocationSet]

    @classmethod
    def build(cls, model: MutablePluginModel) -> LocationIndex:
        locations_by_form_id: dict[int, LocationRecordInfo] = {}
        for record in model.records_by_form_id.values():
            if record.signature != "LCTN":
                continue
            info = _info_from_record(record)
            locations_by_form_id[info.form_id] = info

        star_by_system_id: dict[int, LocationRecordInfo] = {}
        by_system_local_id: dict[tuple[int, int], IndexedLocationSet] = {}
        for info in locations_by_form_id.values():
            if info.system_id is None:
                continue
            if info.role == "star":
                star_by_system_id[info.system_id] = info
                continue
            if info.local_id is None:
                continue
            key = (info.system_id, info.local_id)
            current = by_system_local_id.get(key, IndexedLocationSet())
            if info.role == "orbit":
                current = IndexedLocationSet(main=current.main, orbit=info, surface=current.surface)
            elif info.role == "surface":
                current = IndexedLocationSet(main=current.main, orbit=current.orbit, surface=info)
            else:
                current = IndexedLocationSet(main=info, orbit=current.orbit, surface=current.surface)
            by_system_local_id[key] = current
        return cls(
            locations_by_form_id=locations_by_form_id,
            star_by_system_id=star_by_system_id,
            by_system_local_id=by_system_local_id,
        )

    def star_location(self, system_id: int, *, star_name: str | None = None) -> LocationRecordInfo | None:
        info = self.star_by_system_id.get(system_id)
        if info is not None:
            return info
        if star_name is None:
            return None
        expected = f"S{star_name}"
        for location in self.locations_by_form_id.values():
            if location.role == "star" and location.editor_id == expected:
                return location
        return None

    def locations_for_local_id(self, system_id: int, local_id: int) -> IndexedLocationSet:
        return self.by_system_local_id.get((system_id, local_id), IndexedLocationSet())


def _payload(record: MutableRecord, code: str, ordinal: int = 0) -> bytes | None:
    found = 0
    for subrecord in record.subrecords:
        if subrecord.code != code:
            continue
        if found == ordinal:
            return subrecord.raw_payload
        found += 1
    return None


def _decode(payload: bytes | None) -> str | None:
    if payload is None:
        return None
    return payload.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def _int(payload: bytes | None) -> int | None:
    if payload is None or len(payload) < 4:
        return None
    return int.from_bytes(payload[:4], "little")


def _keywords(record: MutableRecord) -> tuple[int, ...]:
    payload = _payload(record, "KWDA")
    if payload is None:
        return ()
    return tuple(int.from_bytes(payload[i : i + 4], "little") for i in range(0, len(payload), 4))


def _role(record: MutableRecord, keywords: tuple[int, ...], editor_id: str | None) -> str:
    if KW_LOC_TYPE_STAR_SYSTEM in keywords:
        return "star"
    if KW_LOC_TYPE_ORBIT in keywords:
        return "orbit"
    if KW_LOC_TYPE_SURFACE in keywords:
        return "surface"
    if KW_LOC_TYPE_PLANET in keywords:
        return "planet"
    if KW_LOC_TYPE_MOON in keywords:
        return "moon"
    if editor_id and editor_id.endswith("_Orbit"):
        return "orbit"
    if editor_id and editor_id.endswith("_Surface"):
        return "surface"
    return "main"


def _info_from_record(record: MutableRecord) -> LocationRecordInfo:
    keywords = _keywords(record)
    editor_id = _decode(_payload(record, "EDID"))
    return LocationRecordInfo(
        form_id=record.form_id,
        editor_id=editor_id,
        display_name=_decode(_payload(record, "FULL")),
        system_id=_int(_payload(record, "XNAM")),
        local_id=_int(_payload(record, "YNAM")),
        parent_form_id=_int(_payload(record, "PNAM")),
        keywords=keywords,
        role=_role(record, keywords, editor_id),
    )
