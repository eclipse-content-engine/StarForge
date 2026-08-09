from __future__ import annotations

from pathlib import Path

from conftest import PluginFixtures
from pytestqt.qtbot import QtBot

from starforge.application import RecoveryStore, Workspace
from starforge.ui.main_window import REVIEW_PAGE, MainWindow


def test_primary_pages_render_to_non_blank_images(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1280, 800)
    window.show()
    window.enter_design_preview()

    for page in (0, REVIEW_PAGE):
        window.navigate(page)
        image = window.grab().toImage()
        assert image.width() / image.devicePixelRatio() == 1280
        assert image.height() / image.devicePixelRatio() == 800
        sampled_colors = {
            image.pixelColor(x, y).name() for x in range(0, image.width(), 80) for y in range(0, image.height(), 80)
        }
        assert len(sampled_colors) >= 4


def test_undo_controls_follow_workspace_history(qtbot: QtBot, plugin_fixtures: PluginFixtures) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    original = workspace.view.stars[0]
    workspace.set_star_system_id(original.form_id, workspace.allocate_system_id())
    window.session = workspace
    window._populate_lists()

    assert window.undo_button.isEnabled()
    assert not window.redo_button.isEnabled()

    window.undo_button.click()

    assert workspace.view.stars[0].system_id == original.system_id
    assert window.redo_button.isEnabled()


def test_recovery_offer_is_visible_and_specific(
    qtbot: QtBot,
    tmp_path: Path,
    plugin_fixtures: PluginFixtures,
) -> None:
    store = RecoveryStore(tmp_path / "recovery")
    workspace = Workspace.open(plugin_fixtures.source, plugin_fixtures.destination)
    workspace.enable_recovery(store)
    workspace.set_star_system_id(workspace.view.stars[0].form_id, workspace.allocate_system_id())
    record = workspace.save_recovery()
    assert record is not None

    window = MainWindow()
    qtbot.addWidget(window)
    window.recovery_store = store
    window._refresh_recovery_offer()

    assert not window.recovery_panel.isHidden()
    assert str(plugin_fixtures.destination) in window.recovery_summary.text()
