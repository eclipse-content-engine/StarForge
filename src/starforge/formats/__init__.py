"""Self-contained binary primitives used by StarForge."""

from .binary import (
    RECORD_FLAG_COMPRESSED,
    RECORD_HEADER_SIZE,
    BinaryWriter,
    compress_record_payload,
    read_bytes,
)
from .models import MutableHeader, MutableSubrecord, SubrecordEntry
from .plugin_reader import PluginReader

__all__ = [
    "BinaryWriter",
    "MutableHeader",
    "MutableSubrecord",
    "PluginReader",
    "RECORD_FLAG_COMPRESSED",
    "RECORD_HEADER_SIZE",
    "SubrecordEntry",
    "compress_record_payload",
    "read_bytes",
]
