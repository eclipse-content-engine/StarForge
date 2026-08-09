from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BiomExtractResult:
    source_name: str
    destination_name: str
    output_path: Path
    size: int


class PlanetaryDataArchive:
    def __init__(self, archive_path: Path) -> None:
        self.archive_path = archive_path
        self._entries: dict[str, tuple[int, int, int]] | None = None
        self._data: bytes | None = None

    def load(self) -> None:
        data = self.archive_path.read_bytes()
        if len(data) < 36:
            raise ValueError("BA2 archive is too small.")
        tag, version, group_tag, file_count, name_offset, _unused = struct.unpack_from("<4sI4sIQQ", data, 0)
        if tag != b"BTDX" or group_tag != b"GNRL":
            raise ValueError("Unsupported BA2 archive format.")
        cursor = 36
        entries: list[tuple[int, int, int]] = []
        for _ in range(file_count):
            _ext, _hash1, _hash2, offset, compressed_size, decompressed_size, _unused2 = struct.unpack_from(
                "<4sIIQIIQ", data, cursor
            )
            entries.append((offset, compressed_size, decompressed_size))
            cursor += 36
        name_cursor = name_offset
        entry_map: dict[str, tuple[int, int, int]] = {}
        for offset, compressed_size, decompressed_size in entries:
            name_len = struct.unpack_from("<H", data, name_cursor)[0]
            name_cursor += 2
            raw_name = data[name_cursor : name_cursor + name_len]
            name_cursor += name_len
            entry_map[raw_name.decode("utf-8", errors="replace").lower()] = (offset, compressed_size, decompressed_size)
        self._data = data
        self._entries = entry_map

    def extract_biom(self, source_planet_name: str, destination_name: str, output_root: Path) -> BiomExtractResult:
        if self._entries is None or self._data is None:
            self.load()
        assert self._entries is not None and self._data is not None
        nested_name = f"planetdata/biomemaps/{source_planet_name}.biom".lower()
        if nested_name not in self._entries:
            raise FileNotFoundError(f"Biome '{nested_name}' was not found in {self.archive_path.name}.")
        offset, compressed_size, decompressed_size = self._entries[nested_name]
        if compressed_size > 0:
            raw = zlib.decompress(self._data[offset : offset + compressed_size])
        else:
            raw = self._data[offset : offset + decompressed_size]
        output_path = output_root / "planetdata" / "biomemaps" / f"{destination_name}.biom"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(raw)
        return BiomExtractResult(
            source_name=source_planet_name,
            destination_name=destination_name,
            output_path=output_path,
            size=len(raw),
        )
