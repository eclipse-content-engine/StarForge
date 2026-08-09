from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..application import CancellationToken, ProgressUpdate

TaskFunction = Callable[[CancellationToken, Callable[[ProgressUpdate], None]], Any]


class TaskSignals(QObject):
    progress = Signal(object)
    result = Signal(object)
    error = Signal(object)
    finished = Signal()


class BackgroundTask(QRunnable):
    def __init__(self, function: TaskFunction) -> None:
        super().__init__()
        self.function = function
        self.token = CancellationToken()
        self.signals = TaskSignals()
        self.setAutoDelete(True)

    def cancel(self) -> None:
        self.token.cancel()

    @Slot()
    def run(self) -> None:
        try:
            result = self.function(self.token, self.signals.progress.emit)
        except Exception as exc:  # exception crosses the Qt signal boundary as data
            self.signals.error.emit(exc)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
