from __future__ import annotations

from pytestqt.qtbot import QtBot

from starforge.ui.main_window import MainWindow


def test_main_window_opens_in_empty_state(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "StarForge"
    assert window.session is None
    assert window.status_label.text() == "Open a source and destination plugin to begin."
