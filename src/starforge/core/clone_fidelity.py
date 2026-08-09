from __future__ import annotations

from .models import CloneFixupReport, ComponentRewriteWarning
from .plugin_model import MutableRecord


def apply_component_fixups(
    record: MutableRecord,
    *,
    source_candidates: tuple[str, ...],
    new_display_name: str,
    new_editor_id: str,
) -> CloneFixupReport:
    warnings: list[ComponentRewriteWarning] = []
    rewritten: list[str] = []
    unchanged: list[str] = []
    index = 0
    while index < len(record.subrecords):
        subrecord = record.subrecords[index]
        if subrecord.code != "BFCB":
            index += 1
            continue
        component_name = _decode_cstring(subrecord.raw_payload)
        end_index = index + 1
        while end_index < len(record.subrecords) and record.subrecords[end_index].code != "BFCE":
            end_index += 1
        component_slice = record.subrecords[index + 1 : end_index]
        if component_name == "TESFullName_Component":
            full_subrecord = next((item for item in component_slice if item.code == "FULL"), None)
            if full_subrecord is None:
                warnings.append(
                    ComponentRewriteWarning(component_name=component_name, message="FULL payload was not found.")
                )
            else:
                full_subrecord.raw_payload = new_display_name.encode("utf-8") + b"\x00"
                rewritten.append(component_name)
        elif component_name == "HoudiniData_Component":
            pccc_subrecord = next((item for item in component_slice if item.code == "PCCC"), None)
            if pccc_subrecord is None:
                warnings.append(
                    ComponentRewriteWarning(component_name=component_name, message="PCCC payload was not found.")
                )
            else:
                updated_payload, result = rewrite_houdini_payload(
                    pccc_subrecord.raw_payload,
                    source_candidates=source_candidates,
                    new_display_name=new_display_name,
                    new_editor_id=new_editor_id,
                )
                pccc_subrecord.raw_payload = updated_payload
                rewritten.extend(result.rewritten_components)
                unchanged.extend(result.unchanged_components)
                warnings.extend(result.warnings)
        index = end_index + 1
    return CloneFixupReport(
        rewritten_components=tuple(dict.fromkeys(rewritten)),
        unchanged_components=tuple(dict.fromkeys(unchanged)),
        warnings=tuple(warnings),
    )


def rewrite_houdini_payload(
    payload: bytes,
    *,
    source_candidates: tuple[str, ...],
    new_display_name: str,
    new_editor_id: str,
) -> tuple[bytes, CloneFixupReport]:
    updated = payload
    rewritten: list[str] = []
    warnings: list[ComponentRewriteWarning] = []
    unchanged: list[str] = []
    for candidate in source_candidates:
        candidate_bytes = candidate.encode("utf-8")
        if candidate_bytes and candidate_bytes in updated:
            updated = updated.replace(candidate_bytes, new_display_name.encode("utf-8"))
            rewritten.append("HoudiniData_Component")
        biom_token = f"{candidate}.biom".encode()
        if biom_token in updated:
            updated = updated.replace(biom_token, f"{new_display_name}.biom".encode())
            rewritten.append("HoudiniData_Component")
        path_token = f"/{candidate}/".encode()
        if path_token in updated:
            updated = updated.replace(path_token, f"/{new_display_name}/".encode())
            rewritten.append("HoudiniData_Component")
    source_editor_id = next(
        (item for item in source_candidates if item.endswith("PlanetData") or item.endswith("Star")), None
    )
    if source_editor_id is not None and source_editor_id.encode("utf-8") in updated:
        updated = updated.replace(source_editor_id.encode("utf-8"), new_editor_id.encode("utf-8"))
        rewritten.append("HoudiniData_Component")
    if not rewritten:
        unchanged.append("HoudiniData_Component")
        warnings.append(
            ComponentRewriteWarning(
                component_name="HoudiniData_Component",
                message="No unambiguous source-name tokens were found in the Houdini payload.",
            )
        )
    return updated, CloneFixupReport(
        rewritten_components=tuple(dict.fromkeys(rewritten)),
        unchanged_components=tuple(dict.fromkeys(unchanged)),
        warnings=tuple(warnings),
    )


def _decode_cstring(payload: bytes) -> str:
    return payload.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
