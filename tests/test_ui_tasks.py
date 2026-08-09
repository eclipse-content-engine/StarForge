from __future__ import annotations

from pytestqt.qtbot import QtBot

from starforge.application import ProgressUpdate
from starforge.ui.tasks import BackgroundTask


def test_background_task_delivers_progress_and_result(qtbot: QtBot) -> None:
    updates: list[ProgressUpdate] = []
    results: list[object] = []

    def operation(_token, progress):
        progress(ProgressUpdate("test", 0.5, "Halfway"))
        return {"ready": True}

    task = BackgroundTask(operation)
    task.signals.progress.connect(updates.append)
    task.signals.result.connect(results.append)
    task.run()
    qtbot.wait(1)

    assert updates == [ProgressUpdate("test", 0.5, "Halfway")]
    assert results == [{"ready": True}]


def test_background_task_exposes_errors_as_data(qtbot: QtBot) -> None:
    errors: list[Exception] = []

    def operation(_token, _progress):
        raise ValueError("synthetic failure")

    task = BackgroundTask(operation)
    task.signals.error.connect(errors.append)
    task.run()
    qtbot.wait(1)

    assert len(errors) == 1
    assert str(errors[0]) == "synthetic failure"
