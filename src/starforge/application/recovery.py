from __future__ import annotations

import json
import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RecoveryRecord:
    source_path: Path
    destination_path: Path
    recovery_path: Path
    created_at: datetime
    omitted_staged_drafts: tuple[str, ...] = ()


class RecoveryStore:
    """Atomic, non-executable recovery metadata stored beside recovery plugins."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def project_key(self, source_path: Path, destination_path: Path) -> str:
        identity = f"{source_path.resolve()}\0{destination_path.resolve()}".encode()
        return sha256(identity).hexdigest()[:16]

    def plugin_path(self, source_path: Path, destination_path: Path, generation: str) -> Path:
        key = self.project_key(source_path, destination_path)
        suffix = destination_path.suffix if destination_path.suffix.casefold() in {".esm", ".esp"} else ".esp"
        return self.root / f"recovery-{key}-{generation}{suffix}"

    def next_plugin_path(self, source_path: Path, destination_path: Path) -> Path:
        current = self._read_manifest(self._manifest_path(source_path, destination_path))
        generation = "b" if current is not None and f"-{current.recovery_path.stem[-1]}" == "-a" else "a"
        return self.plugin_path(source_path, destination_path, generation)

    def save_manifest(self, record: RecoveryRecord) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        manifest = self._manifest_path(record.source_path, record.destination_path)
        previous = self._read_manifest(manifest)
        temporary = manifest.with_name(f".{manifest.name}.{uuid4().hex}.tmp")
        payload = {
            "schema_version": 1,
            "source_path": str(record.source_path),
            "destination_path": str(record.destination_path),
            "recovery_path": str(record.recovery_path),
            "created_at": record.created_at.isoformat(),
            "omitted_staged_drafts": list(record.omitted_staged_drafts),
        }
        try:
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(temporary, manifest)
        finally:
            temporary.unlink(missing_ok=True)
        if previous is not None and previous.recovery_path != record.recovery_path:
            with suppress(OSError):
                previous.recovery_path.unlink(missing_ok=True)

    def latest(self) -> RecoveryRecord | None:
        records = [record for path in self.root.glob("recovery-*.json") if (record := self._read_manifest(path))]
        return max(records, key=lambda record: record.created_at) if records else None

    def clear(self, source_path: Path, destination_path: Path) -> None:
        manifest = self._manifest_path(source_path, destination_path)
        record = self._read_manifest(manifest)
        with suppress(OSError):
            manifest.unlink(missing_ok=True)
        if record is not None:
            with suppress(OSError):
                record.recovery_path.unlink(missing_ok=True)

    def _manifest_path(self, source_path: Path, destination_path: Path) -> Path:
        return self.root / f"recovery-{self.project_key(source_path, destination_path)}.json"

    def _read_manifest(self, path: Path) -> RecoveryRecord | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != 1:
                return None
            record = RecoveryRecord(
                source_path=Path(payload["source_path"]),
                destination_path=Path(payload["destination_path"]),
                recovery_path=Path(payload["recovery_path"]),
                created_at=datetime.fromisoformat(payload["created_at"]),
                omitted_staged_drafts=tuple(payload.get("omitted_staged_drafts", ())),
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None
        try:
            recovery_is_owned = record.recovery_path.resolve().is_relative_to(self.root.resolve())
        except OSError:
            recovery_is_owned = False
        if not recovery_is_owned or not record.source_path.is_file() or not record.recovery_path.is_file():
            return None
        return record


def recovery_timestamp() -> datetime:
    return datetime.now(UTC)
