"""Data models shared by StarForge's plugin reader and writer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class PluginType(StrEnum):
    ESM = ".esm"
    ESP = ".esp"
    ESL = ".esl"


@dataclass(frozen=True)
class Subrecord:
    code: str
    size: int
    raw_payload: bytes = field(default_factory=bytes, repr=False)


@dataclass(frozen=True)
class HEDRInfo:
    version: float
    record_count: int
    next_object_id: int


@dataclass(frozen=True)
class PluginHeader:
    source_path: Path
    plugin_type: PluginType
    signature: str
    record_size: int
    flags: int
    form_id: int
    revision: int
    internal_version: int
    unknown: int
    subrecords: list[Subrecord] = field(default_factory=list)
    masters: list[str] = field(default_factory=list)
    hedr: HEDRInfo | None = None

    def subrecord_codes(self) -> list[str]:
        return [item.code for item in self.subrecords]


@dataclass
class MutableSubrecord:
    code: str
    raw_payload: bytes


@dataclass
class MutableHeader:
    source_header: PluginHeader
    subrecords: list[MutableSubrecord]
    version: float
    record_count: int
    next_object_id: int


@dataclass(frozen=True)
class RecordPayload:
    signature: str
    form_id: int
    offset: int
    payload_size: int
    decoded_payload_size: int
    flags: int
    internal_version: int
    payload: bytes


@dataclass(frozen=True)
class SubrecordEntry:
    code: str
    size: int
    offset_within_record: int
    data: bytes
