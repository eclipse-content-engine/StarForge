from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from ..formats import (
    RECORD_FLAG_COMPRESSED,
    RECORD_HEADER_SIZE,
    BinaryWriter,
    MutableHeader,
    MutableSubrecord,
    PluginReader,
    compress_record_payload,
    read_bytes,
)

MANAGED_GROUPS = ("STDT", "PNDT", "LCTN", "NPC_")


@dataclass
class MutableRecord:
    signature: str
    form_id: int
    flags: int
    revision: int
    internal_version: int
    unknown: int
    was_compressed: bool
    subrecords: list[MutableSubrecord]


@dataclass
class MutablePluginModel:
    source_path: Path
    original_bytes: bytes
    header: MutableHeader
    records_by_form_id: dict[int, MutableRecord]
    mutable_record_form_ids: set[int] = field(default_factory=set)
    new_records_by_group: dict[str, list[MutableRecord]] = field(default_factory=dict)
    existing_group_headers: dict[str, bytes] = field(default_factory=dict)
    masters: tuple[str, ...] = ()


class StarForgePluginModelIO:
    def __init__(self) -> None:
        self.reader = PluginReader()

    def load_model(self, path: Path) -> MutablePluginModel:
        header = self.reader.read_header(path)
        data = read_bytes(path)
        mutable_header = MutableHeader(
            source_header=header,
            subrecords=[MutableSubrecord(code=item.code, raw_payload=item.raw_payload) for item in header.subrecords],
            version=header.hedr.version if header.hedr is not None else 1.0,
            record_count=header.hedr.record_count if header.hedr is not None else 0,
            next_object_id=header.hedr.next_object_id if header.hedr is not None else 1,
        )
        records_by_form_id: dict[int, MutableRecord] = {}
        existing_group_headers: dict[str, bytes] = {}
        for entry_start, signature, size_value in self.reader._iter_top_level_entries(data, header):
            if signature != b"GRUP":
                continue
            entry_size = size_value
            group_bytes = data[entry_start : entry_start + entry_size]
            label = group_bytes[8:12].decode("ascii", errors="replace")
            if label not in MANAGED_GROUPS:
                continue
            existing_group_headers[label] = group_bytes[:24]
        for signature in MANAGED_GROUPS:
            for record in self.reader._read_direct_records_with_payload(path, signature):
                header_values = self._record_header_values(data, record.offset)
                subrecords = [
                    MutableSubrecord(code=item.code, raw_payload=item.data)
                    for item in self.reader._scan_subrecord_entries(record.payload, record.offset)
                ]
                records_by_form_id[record.form_id] = MutableRecord(
                    signature=signature,
                    form_id=record.form_id,
                    flags=header_values["flags"],
                    revision=header_values["revision"],
                    internal_version=header_values["internal_version"],
                    unknown=header_values["unknown"],
                    was_compressed=(header_values["flags"] & RECORD_FLAG_COMPRESSED) != 0,
                    subrecords=subrecords,
                )
        return MutablePluginModel(
            source_path=path,
            original_bytes=data,
            header=mutable_header,
            records_by_form_id=records_by_form_id,
            existing_group_headers=existing_group_headers,
            masters=tuple(header.masters),
        )

    def replace_subrecord(
        self, model: MutablePluginModel, *, form_id: int, code: str, payload: bytes, ordinal: int = 0
    ) -> None:
        record = model.records_by_form_id[form_id]
        found = 0
        for subrecord in record.subrecords:
            if subrecord.code != code:
                continue
            if found == ordinal:
                subrecord.raw_payload = payload
                model.mutable_record_form_ids.add(form_id)
                return
            found += 1
        raise ValueError(f"Subrecord {code}[{ordinal}] not found for 0x{form_id:08X}")

    def add_record(self, model: MutablePluginModel, record: MutableRecord) -> None:
        model.records_by_form_id[record.form_id] = record
        model.new_records_by_group.setdefault(record.signature, []).append(record)
        model.header.record_count += 1

    def write_model(self, output_path: Path, model: MutablePluginModel) -> None:
        if output_path.resolve() == model.source_path.resolve():
            raise ValueError("Output path must differ from source path.")
        header = self.reader.read_header(model.source_path)
        rebuilt_header = self._build_tes4_record_bytes(model)
        managed_group_bytes = self._build_managed_groups(model)
        writer = BinaryWriter()
        writer.write(rebuilt_header)
        written_managed_groups: set[str] = set()
        for entry_start, signature, size_value in self.reader._iter_top_level_entries(model.original_bytes, header):
            entry_size = size_value if signature == b"GRUP" else RECORD_HEADER_SIZE + size_value
            entry_end = entry_start + entry_size
            entry_bytes = model.original_bytes[entry_start:entry_end]
            if signature != b"GRUP":
                if signature != b"TES4":
                    writer.write(entry_bytes)
                continue
            label = model.original_bytes[entry_start + 8 : entry_start + 12].decode("ascii", errors="replace")
            if label in managed_group_bytes:
                writer.write(managed_group_bytes[label])
                written_managed_groups.add(label)
            else:
                writer.write(entry_bytes)
        for label in MANAGED_GROUPS:
            if label in managed_group_bytes and label not in written_managed_groups:
                writer.write(managed_group_bytes[label])
        output_path.write_bytes(writer.to_bytes())

    def validate_written_model(
        self, path: Path, *, expected_groups: tuple[str, ...] = MANAGED_GROUPS, expected_record_count: int | None = None
    ) -> dict[str, object]:
        header = self.reader.read_header(path)
        data = path.read_bytes()
        group_labels: list[str] = []
        for entry_start, signature, _size_value in self.reader._iter_top_level_entries(data, header):
            if signature == b"GRUP":
                group_labels.append(data[entry_start + 8 : entry_start + 12].decode("ascii", errors="replace"))
        managed_present = tuple(label for label in expected_groups if label in group_labels)
        return {
            "masters": tuple(header.masters),
            "group_labels": tuple(group_labels),
            "managed_groups_present": managed_present,
            "record_count": header.hedr.record_count if header.hedr is not None else None,
            "is_valid": all(
                label in group_labels for label in expected_groups if expected_record_count or label in group_labels
            )
            and (
                expected_record_count is None
                or (header.hedr is not None and header.hedr.record_count == expected_record_count)
            ),
        }

    def _build_managed_groups(self, model: MutablePluginModel) -> dict[str, bytes]:
        groups: dict[str, bytes] = {}
        for label in MANAGED_GROUPS:
            content = BinaryWriter()
            existing = [record for record in model.records_by_form_id.values() if record.signature == label]
            if not existing:
                continue
            for record in sorted(existing, key=lambda item: item.form_id):
                if (
                    record.form_id in model.mutable_record_form_ids
                    or any(item.form_id == record.form_id for item in model.new_records_by_group.get(label, []))
                    or record.form_id in model.records_by_form_id
                ):
                    content.write(self._build_record_bytes(record))
            groups[label] = self._encode_group(self._group_header_for_label(model, label), content.to_bytes())
        return groups

    def _group_header_for_label(self, model: MutablePluginModel, label: str) -> bytes:
        existing = model.existing_group_headers.get(label)
        if existing is not None:
            return existing
        return (
            b"GRUP"
            + (24).to_bytes(4, "little")
            + label.encode("ascii")
            + (0).to_bytes(4, "little")
            + (0).to_bytes(4, "little")
            + (0).to_bytes(4, "little")
        )

    def _build_record_bytes(self, record: MutableRecord) -> bytes:
        payload_writer = BinaryWriter()
        for subrecord in record.subrecords:
            payload_writer.write(self._encode_subrecord(subrecord.code, subrecord.raw_payload))
        payload = payload_writer.to_bytes()
        flags = record.flags & ~RECORD_FLAG_COMPRESSED
        if record.was_compressed:
            payload = struct.pack("<I", len(payload)) + compress_record_payload(payload)
            flags = record.flags | RECORD_FLAG_COMPRESSED
        return self._encode_record(
            signature=record.signature,
            flags=flags,
            form_id=record.form_id,
            revision=record.revision,
            internal_version=record.internal_version,
            unknown=record.unknown,
            payload=payload,
        )

    def _build_tes4_record_bytes(self, model: MutablePluginModel) -> bytes:
        masters = self._normalized_masters(model)
        payload = BinaryWriter()
        masters_inserted = False
        # Starfield plugins use MAST entries without TES4 DATA companions.
        # Keep the master table ahead of late header fields such as BNAM/INCC,
        # but do not synthesize DATA subrecords that xEdit flags as invalid.
        late_header_codes = {"BNAM", "INCC", "INTV", "ONAM", "SCRN"}
        for subrecord in model.header.subrecords:
            if subrecord.code == "HEDR":
                payload.write(
                    self._encode_subrecord(
                        "HEDR",
                        struct.pack(
                            "<fII", model.header.version, model.header.record_count, model.header.next_object_id
                        ),
                    )
                )
                continue
            if not masters_inserted and masters and subrecord.code in late_header_codes:
                for master in masters:
                    payload.write(self._encode_subrecord("MAST", master.encode("utf-8") + b"\x00"))
                masters_inserted = True
            if subrecord.code in {"MAST", "DATA"}:
                if not masters_inserted and masters:
                    for master in masters:
                        payload.write(self._encode_subrecord("MAST", master.encode("utf-8") + b"\x00"))
                    masters_inserted = True
                continue
            payload.write(self._encode_subrecord(subrecord.code, subrecord.raw_payload))
        if not masters_inserted:
            for master in masters:
                payload.write(self._encode_subrecord("MAST", master.encode("utf-8") + b"\x00"))
        source_header = model.header.source_header
        return self._encode_record(
            signature="TES4",
            flags=source_header.flags,
            form_id=source_header.form_id,
            revision=source_header.revision,
            internal_version=source_header.internal_version,
            unknown=source_header.unknown,
            payload=payload.to_bytes(),
        )

    def _normalized_masters(self, model: MutablePluginModel) -> tuple[str, ...]:
        masters: list[str] = []
        for master in model.masters:
            if master not in masters:
                masters.append(master)
        if "Starfield.esm" not in masters:
            masters.insert(0, "Starfield.esm")
        return tuple(masters)

    def _encode_group(self, original_header: bytes, content: bytes) -> bytes:
        header = bytearray(original_header)
        header[4:8] = (24 + len(content)).to_bytes(4, "little")
        return bytes(header) + content

    def _encode_record(
        self,
        *,
        signature: str,
        flags: int,
        form_id: int,
        revision: int,
        internal_version: int,
        unknown: int,
        payload: bytes,
    ) -> bytes:
        return (
            signature.encode("ascii")
            + len(payload).to_bytes(4, "little")
            + flags.to_bytes(4, "little")
            + form_id.to_bytes(4, "little")
            + revision.to_bytes(4, "little")
            + internal_version.to_bytes(2, "little")
            + unknown.to_bytes(2, "little")
            + payload
        )

    def _encode_subrecord(self, code: str, payload: bytes) -> bytes:
        if len(payload) <= 0xFFFF:
            return code.encode("ascii") + len(payload).to_bytes(2, "little") + payload
        return (
            b"XXXX"
            + (4).to_bytes(2, "little")
            + len(payload).to_bytes(4, "little")
            + code.encode("ascii")
            + (0).to_bytes(2, "little")
            + payload
        )

    def _record_header_values(self, data: bytes, offset: int) -> dict[str, int]:
        return {
            "flags": int.from_bytes(data[offset + 8 : offset + 12], "little"),
            "revision": int.from_bytes(data[offset + 16 : offset + 20], "little"),
            "internal_version": int.from_bytes(data[offset + 20 : offset + 22], "little"),
            "unknown": int.from_bytes(data[offset + 22 : offset + 24], "little"),
        }
