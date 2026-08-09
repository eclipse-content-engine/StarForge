from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from ..formats import PluginReader
from .models import SystemIdUsage


class _UsageBucket(TypedDict):
    source_paths: set[Path]
    star_form_ids: set[int]
    planet_form_ids: set[int]
    location_form_ids: set[int]


@dataclass
class SystemIdAllocator:
    used_ids: set[int]
    _random: random.Random = random.Random()

    def allocate_random(self) -> int:
        while True:
            candidate = self._random.randint(1, 0x7FFFFFFF)
            if candidate not in self.used_ids:
                self.used_ids.add(candidate)
                return candidate

    def validate(self, candidate: int) -> bool:
        return candidate > 0 and candidate not in self.used_ids


def collect_system_id_usage(paths: list[Path]) -> list[SystemIdUsage]:
    reader = PluginReader()
    buckets: dict[int, _UsageBucket] = {}
    for path in paths:
        if not path.exists():
            continue
        for record in reader._read_direct_records_with_payload(path, "STDT"):
            system_id = _find_stdt_system_id(reader, record.payload, record.offset)
            if system_id is None:
                continue
            bucket = buckets.setdefault(system_id, _empty_bucket())
            bucket["source_paths"].add(path)
            bucket["star_form_ids"].add(record.form_id)
        for record in reader._read_direct_records_with_payload(path, "PNDT"):
            system_id = _find_pndt_system_id(reader, record.payload, record.offset)
            if system_id is None:
                continue
            bucket = buckets.setdefault(system_id, _empty_bucket())
            bucket["source_paths"].add(path)
            bucket["planet_form_ids"].add(record.form_id)
        for record in reader._read_direct_records_with_payload(path, "LCTN"):
            system_id = _find_lctn_system_id(reader, record.payload, record.offset)
            if system_id is None:
                continue
            bucket = buckets.setdefault(system_id, _empty_bucket())
            bucket["source_paths"].add(path)
            bucket["location_form_ids"].add(record.form_id)
    return [
        SystemIdUsage(
            system_id=system_id,
            source_paths=tuple(sorted(bucket["source_paths"])),
            star_form_ids=tuple(sorted(bucket["star_form_ids"])),
            planet_form_ids=tuple(sorted(bucket["planet_form_ids"])),
            location_form_ids=tuple(sorted(bucket["location_form_ids"])),
        )
        for system_id, bucket in sorted(buckets.items())
    ]


def allocator_from_usage(usage: list[SystemIdUsage]) -> SystemIdAllocator:
    return SystemIdAllocator({item.system_id for item in usage})


def _empty_bucket() -> _UsageBucket:
    return {
        "source_paths": set(),
        "star_form_ids": set(),
        "planet_form_ids": set(),
        "location_form_ids": set(),
    }


def _find_stdt_system_id(reader: PluginReader, payload: bytes, offset: int) -> int | None:
    for entry in reader._scan_subrecord_entries(payload, offset):
        if entry.code == "DNAM" and len(entry.data) >= 4:
            return int.from_bytes(entry.data[:4], "little")
    return None


def _find_pndt_system_id(reader: PluginReader, payload: bytes, offset: int) -> int | None:
    gnam_payloads = [entry.data for entry in reader._scan_subrecord_entries(payload, offset) if entry.code == "GNAM"]
    for candidate in reversed(gnam_payloads):
        if len(candidate) >= 12:
            return int.from_bytes(candidate[:4], "little")
    return None


def _find_lctn_system_id(reader: PluginReader, payload: bytes, offset: int) -> int | None:
    for entry in reader._scan_subrecord_entries(payload, offset):
        if entry.code == "XNAM" and len(entry.data) >= 4:
            return int.from_bytes(entry.data[:4], "little")
    return None
