"""Small binary I/O and compression primitives for StarForge."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from .exceptions import PluginParseError, TruncatedDataError

SUPPORTED_EXTENSIONS = (".esm", ".esp", ".esl")
RECORD_SIGNATURE_TES4 = b"TES4"
RECORD_HEADER_SIZE = 24
SUBRECORD_HEADER_SIZE = 6
RECORD_FLAG_COMPRESSED = 0x00040000


@dataclass
class BinaryReader:
    data: bytes
    offset: int = 0

    def tell(self) -> int:
        return self.offset

    def seek(self, offset: int) -> None:
        if offset < 0 or offset > len(self.data):
            raise TruncatedDataError(f"Seek offset {offset} is outside buffer length {len(self.data)}")
        self.offset = offset

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read(self, size: int) -> bytes:
        if size < 0 or self.offset + size > len(self.data):
            raise TruncatedDataError(f"Need {size} bytes at offset {self.offset}, only {self.remaining()} remain")
        chunk = self.data[self.offset : self.offset + size]
        self.offset += size
        return chunk

    def read_uint16(self) -> int:
        return struct.unpack("<H", self.read(2))[0]

    def read_uint32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def read_float32(self) -> float:
        return struct.unpack("<f", self.read(4))[0]

    def read_fourcc(self) -> str:
        return self.read(4).decode("ascii", errors="replace")


@dataclass
class BinaryWriter:
    chunks: list[bytes] = field(default_factory=list)

    def write(self, chunk: bytes) -> None:
        self.chunks.append(chunk)

    def to_bytes(self) -> bytes:
        return b"".join(self.chunks)


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def compress_record_payload(payload: bytes) -> bytes:
    return zlib.compress(payload)


def normalize_record_payload(payload: bytes, flags: int, record_offset: int) -> bytes:
    if not flags & RECORD_FLAG_COMPRESSED:
        return payload
    if len(payload) < 4:
        raise TruncatedDataError(f"Compressed payload is too short at record offset {record_offset}")
    expected_size = struct.unpack("<I", payload[:4])[0]
    try:
        result = zlib.decompress(payload[4:])
    except zlib.error as exc:
        raise PluginParseError(f"Invalid compressed payload at record offset {record_offset}: {exc}") from exc
    if len(result) != expected_size:
        raise PluginParseError(
            f"Decompressed payload size mismatch at record offset {record_offset}: "
            f"expected {expected_size}, got {len(result)}"
        )
    return result
