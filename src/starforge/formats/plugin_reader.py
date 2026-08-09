"""Narrow preserve-first reader for the records StarForge edits."""

from __future__ import annotations

import struct
from pathlib import Path

from .binary import (
    RECORD_HEADER_SIZE,
    RECORD_SIGNATURE_TES4,
    SUBRECORD_HEADER_SIZE,
    SUPPORTED_EXTENSIONS,
    BinaryReader,
    normalize_record_payload,
    read_bytes,
)
from .exceptions import PluginParseError, TruncatedDataError, UnexpectedRecordError, UnsupportedPluginTypeError
from .models import HEDRInfo, PluginHeader, PluginType, RecordPayload, Subrecord, SubrecordEntry


class PluginReader:
    """Read TES4 headers and direct records without workspace dependencies."""

    def __init__(self) -> None:
        self._bytes_cache: dict[Path, bytes] = {}
        self._header_cache: dict[Path, PluginHeader] = {}
        self._group_cache: dict[tuple[Path, str], list[RecordPayload]] = {}

    def _read_path_bytes(self, path: Path) -> bytes:
        key = path.resolve()
        if key not in self._bytes_cache:
            self._bytes_cache[key] = read_bytes(path)
        return self._bytes_cache[key]

    def read_header(self, path: Path) -> PluginHeader:
        path = Path(path)
        cache_key = path.resolve()
        if cache_key in self._header_cache:
            return self._header_cache[cache_key]
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise UnsupportedPluginTypeError(f"Unsupported plugin extension: {path.suffix}")
        data = self._read_path_bytes(path)
        reader = BinaryReader(data)
        if reader.remaining() < RECORD_HEADER_SIZE:
            raise TruncatedDataError("File is too short to contain a record header")
        signature_raw = reader.read(4)
        if signature_raw != RECORD_SIGNATURE_TES4:
            signature = signature_raw.decode("ascii", errors="replace")
            raise UnexpectedRecordError(f"First record must be TES4, got {signature!r}")
        record_size = reader.read_uint32()
        flags = reader.read_uint32()
        form_id = reader.read_uint32()
        revision = reader.read_uint32()
        internal_version = reader.read_uint16()
        unknown = reader.read_uint16()
        if reader.remaining() < record_size:
            raise TruncatedDataError(f"TES4 payload is truncated: needed {record_size} bytes")
        subrecords, masters, hedr = self._parse_tes4_payload(reader.read(record_size))
        header = PluginHeader(
            source_path=path,
            plugin_type=PluginType(path.suffix.lower()),
            signature="TES4",
            record_size=record_size,
            flags=flags,
            form_id=form_id,
            revision=revision,
            internal_version=internal_version,
            unknown=unknown,
            subrecords=subrecords,
            masters=masters,
            hedr=hedr,
        )
        self._header_cache[cache_key] = header
        return header

    def iter_top_level_entries(self, data: bytes, header: PluginHeader):
        reader = BinaryReader(data)
        reader.seek(RECORD_HEADER_SIZE + header.record_size)
        while reader.remaining() >= 8:
            entry_start = reader.tell()
            signature = reader.read(4)
            size_value = reader.read_uint32()
            entry_size = size_value if signature == b"GRUP" else RECORD_HEADER_SIZE + size_value
            minimum = 24 if signature == b"GRUP" else RECORD_HEADER_SIZE
            if entry_size < minimum or entry_start + entry_size > len(data):
                break
            yield entry_start, signature, size_value
            reader.seek(entry_start + entry_size)

    def read_direct_records(self, path: Path, group_label: str) -> list[RecordPayload]:
        cache_key = (Path(path).resolve(), group_label)
        if cache_key in self._group_cache:
            return self._group_cache[cache_key]
        header = self.read_header(path)
        data = self._read_path_bytes(path)
        for entry_start, signature, size_value in self.iter_top_level_entries(data, header):
            if signature != b"GRUP":
                continue
            entry_end = entry_start + size_value
            if size_value < 24 or entry_end > len(data):
                raise TruncatedDataError(f"Malformed top-level GRUP at offset {entry_start}")
            if data[entry_start + 8 : entry_start + 12].decode("ascii", errors="replace") != group_label:
                continue
            records: list[RecordPayload] = []
            cursor = BinaryReader(data)
            cursor.seek(entry_start + 24)
            while cursor.tell() + 8 <= entry_end:
                record_start = cursor.tell()
                record_signature = cursor.read(4)
                payload_size = cursor.read_uint32()
                if record_signature == b"GRUP":
                    nested_end = record_start + payload_size
                    if payload_size < 24 or nested_end > entry_end:
                        raise TruncatedDataError(f"Malformed nested GRUP at offset {record_start}")
                    cursor.seek(nested_end)
                    continue
                record_end = record_start + RECORD_HEADER_SIZE + payload_size
                if record_end > entry_end:
                    raise TruncatedDataError(f"Record at offset {record_start} overruns group boundary")
                record_header = BinaryReader(data)
                record_header.seek(record_start + 8)
                flags = record_header.read_uint32()
                form_id = record_header.read_uint32()
                record_header.read_uint32()
                internal_version = record_header.read_uint16()
                record_header.read_uint16()
                raw_payload = data[record_start + RECORD_HEADER_SIZE : record_end]
                payload = normalize_record_payload(raw_payload, flags, record_start)
                records.append(
                    RecordPayload(
                        signature=record_signature.decode("ascii", errors="replace"),
                        form_id=form_id,
                        offset=record_start,
                        payload_size=payload_size,
                        decoded_payload_size=len(payload),
                        flags=flags,
                        internal_version=internal_version,
                        payload=payload,
                    )
                )
                cursor.seek(record_end)
            self._group_cache[cache_key] = records
            return records
        self._group_cache[cache_key] = []
        return []

    def scan_subrecords(self, payload: bytes, record_offset: int) -> list[SubrecordEntry]:
        reader = BinaryReader(payload)
        entries: list[SubrecordEntry] = []
        pending_extended_size: int | None = None
        while reader.remaining() > 0:
            if reader.remaining() < SUBRECORD_HEADER_SIZE:
                raise TruncatedDataError(f"Truncated subrecord header in record at offset {record_offset}")
            offset = RECORD_HEADER_SIZE + reader.tell()
            code = reader.read_fourcc()
            size = reader.read_uint16()
            if code == "XXXX":
                if size != 4 or reader.remaining() < 4:
                    raise PluginParseError(f"Malformed XXXX subrecord in record at offset {record_offset}")
                pending_extended_size = reader.read_uint32()
                continue
            effective_size = pending_extended_size if pending_extended_size is not None else size
            if reader.remaining() < effective_size:
                raise TruncatedDataError(f"Subrecord {code} overruns payload in record at offset {record_offset}")
            entries.append(SubrecordEntry(code, effective_size, offset, reader.read(effective_size)))
            pending_extended_size = None
        if pending_extended_size is not None:
            raise PluginParseError(f"Dangling XXXX in record at offset {record_offset}")
        return entries

    def extract_shallow_edid(self, payload: bytes, max_scan_bytes: int = 2048) -> str | None:
        reader = BinaryReader(payload)
        limit = min(len(payload), max_scan_bytes)
        pending_extended_size: int | None = None
        while reader.tell() + SUBRECORD_HEADER_SIZE <= limit:
            code = reader.read_fourcc()
            size = reader.read_uint16()
            if code == "XXXX":
                if size != 4 or reader.tell() + 4 > limit:
                    return None
                pending_extended_size = reader.read_uint32()
                continue
            effective_size = pending_extended_size if pending_extended_size is not None else size
            if reader.tell() + effective_size > limit or reader.tell() + effective_size > len(payload):
                return None
            value = reader.read(effective_size)
            pending_extended_size = None
            if code == "EDID":
                return value.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        return None

    # Compatibility aliases retained while the core API is decomposed in Phase 2.
    _iter_top_level_entries = iter_top_level_entries
    _read_direct_records_with_payload = read_direct_records
    _scan_subrecord_entries = scan_subrecords
    _extract_shallow_edid = extract_shallow_edid

    def _parse_tes4_payload(self, payload: bytes) -> tuple[list[Subrecord], list[str], HEDRInfo | None]:
        reader = BinaryReader(payload)
        subrecords: list[Subrecord] = []
        masters: list[str] = []
        hedr: HEDRInfo | None = None
        while reader.remaining() > 0:
            if reader.remaining() < SUBRECORD_HEADER_SIZE:
                raise TruncatedDataError("Truncated TES4 subrecord header")
            code = reader.read_fourcc()
            size = reader.read_uint16()
            raw_payload = reader.read(size)
            subrecords.append(Subrecord(code, size, raw_payload))
            if code == "MAST":
                masters.append(raw_payload.split(b"\x00", 1)[0].decode("utf-8", errors="replace"))
            elif code == "HEDR":
                if len(raw_payload) < 12:
                    raise PluginParseError("HEDR payload is shorter than 12 bytes")
                version, record_count, next_object_id = struct.unpack("<fII", raw_payload[:12])
                hedr = HEDRInfo(version, record_count, next_object_id)
        return subrecords, masters, hedr
