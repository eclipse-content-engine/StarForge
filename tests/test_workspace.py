from __future__ import annotations

from pathlib import Path

import pytest
from conftest import PluginFixtures

from starforge.application import (
    CancellationToken,
    ExitCode,
    OperationCancelledError,
    ProgressUpdate,
    RecoveryStore,
    Workspace,
)


def test_workspace_open_reports_progress_and_exposes_project(plugin_fixtures: PluginFixtures) -> None:
    updates: list[ProgressUpdate] = []

    workspace = Workspace.open(
        plugin_fixtures.source,
        plugin_fixtures.destination,
        progress=updates.append,
    )

    assert workspace.source_path == plugin_fixtures.source
    assert workspace.destination_path == plugin_fixtures.destination
    assert workspace.view.source_stars
    assert workspace.view.stars
    assert updates[0].fraction == 0.05
    assert updates[-1].fraction == 1.0
    assert updates[-1].message == "Project ready"


def test_workspace_open_honors_cancellation(plugin_fixtures: PluginFixtures) -> None:
    cancellation = CancellationToken()
    cancellation.cancel()

    with pytest.raises(OperationCancelledError) as error:
        Workspace.open(
            plugin_fixtures.source,
            plugin_fixtures.destination,
            cancellation=cancellation,
        )

    assert error.value.exit_code == ExitCode.CANCELLED


def test_workspace_preview_apply_and_export_are_safe(
    tmp_path: Path,
    plugin_fixtures: PluginFixtures,
) -> None:
    source_before = plugin_fixtures.source.read_bytes()
    destination_before = plugin_fixtures.destination.read_bytes()
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    source_star = workspace.view.source_stars[0]
    preview = workspace.preview_star_clone(
        source_star_form_id=source_star.form_id,
        new_editor_id="WorkspaceTestStar",
        new_display_name="Workspace Test",
        system_id=workspace.allocate_system_id(),
    )

    draft = workspace.stage_draft(preview)
    assert workspace.pending_change_count == 1
    workspace.apply_draft(draft.draft_id)
    assert workspace.pending_change_count == 1
    assert workspace.applied_change_summaries == (f"CREATE STAR  {draft.new_display_name}  ·  Draft {draft.draft_id}",)

    updates: list[ProgressUpdate] = []
    output = tmp_path / "workspace-output.esp"
    result = workspace.export(output, progress=updates.append)

    assert result.output_path == output
    assert output.exists()
    assert updates[-1].fraction == 1.0
    assert plugin_fixtures.source.read_bytes() == source_before
    assert plugin_fixtures.destination.read_bytes() == destination_before


def test_workspace_review_summarizes_applied_edits(plugin_fixtures: PluginFixtures) -> None:
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    star = workspace.view.stars[0]

    workspace.set_star_system_id(star.form_id, workspace.allocate_system_id())

    assert workspace.pending_change_count == 1
    assert workspace.applied_change_summaries == (f"SYSTEM ID  {star.display_name}  ·  Form 0x{star.form_id:08X}",)


def test_workspace_undo_and_redo_restore_the_complete_session(plugin_fixtures: PluginFixtures) -> None:
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    original = workspace.view.stars[0]
    replacement = workspace.allocate_system_id()

    workspace.set_star_system_id(original.form_id, replacement)
    assert workspace.view.stars[0].system_id == replacement
    assert workspace.can_undo
    assert not workspace.can_redo

    assert workspace.undo().changed
    assert workspace.view.stars[0].system_id == original.system_id
    assert workspace.pending_change_count == 0
    assert workspace.can_redo

    assert workspace.redo().changed
    assert workspace.view.stars[0].system_id == replacement
    assert workspace.pending_change_count == 1


def test_failed_edit_does_not_pollute_undo_history(plugin_fixtures: PluginFixtures) -> None:
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    star = workspace.view.stars[0]

    with pytest.raises(ValueError, match="already in use"):
        workspace.set_star_system_id(star.form_id, 0x01002000)

    assert not workspace.can_undo


def test_recovery_snapshot_restores_applied_changes_and_protects_inputs(
    tmp_path: Path,
    plugin_fixtures: PluginFixtures,
) -> None:
    source_before = plugin_fixtures.source.read_bytes()
    destination_before = plugin_fixtures.destination.read_bytes()
    store = RecoveryStore(tmp_path / "recovery")
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    workspace.enable_recovery(store)
    star = workspace.view.stars[0]
    replacement = workspace.allocate_system_id()
    workspace.set_star_system_id(star.form_id, replacement)

    record = workspace.save_recovery()

    assert record is not None
    assert record.recovery_path.is_file()
    assert store.latest() == record
    assert plugin_fixtures.source.read_bytes() == source_before
    assert plugin_fixtures.destination.read_bytes() == destination_before

    recovered = Workspace.recover(record)
    assert recovered.destination_path == plugin_fixtures.destination
    assert recovered.view.stars[0].system_id == replacement
    assert recovered.pending_change_count == 1


def test_recovery_manifest_reports_unapplied_drafts(tmp_path: Path, plugin_fixtures: PluginFixtures) -> None:
    store = RecoveryStore(tmp_path / "recovery")
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    workspace.enable_recovery(store)
    source_star = workspace.view.source_stars[0]
    preview = workspace.preview_star_clone(
        source_star_form_id=source_star.form_id,
        new_editor_id="RecoveryDraftStar",
        new_display_name="Recovery Draft",
        system_id=workspace.allocate_system_id(),
    )
    draft = workspace.stage_draft(preview)

    record = workspace.save_recovery()

    assert record is not None
    assert record.omitted_staged_drafts == (draft.draft_id,)
    assert Workspace.recover(record).view.stars == workspace.view.stars
