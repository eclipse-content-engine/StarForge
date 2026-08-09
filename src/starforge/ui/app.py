from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("StarForge")
    QApplication.setApplicationDisplayName("StarForge")
    app.setOrganizationName("Eclipse Content Engine")
    window = MainWindow()
    window.show()
    return app.exec()
