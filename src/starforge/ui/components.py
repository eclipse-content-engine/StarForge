from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class NavButton(QPushButton):
    def __init__(self, label: str, shortcut_hint: str, parent: QWidget | None = None) -> None:
        super().__init__(f"{label}\n{shortcut_hint}", parent)
        self.setCheckable(True)
        self.setProperty("nav", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(label)


class Surface(QFrame):
    def __init__(self, title: str | None = None, description: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(20, 18, 20, 20)
        self.content_layout.setSpacing(12)
        if title:
            title_label = QLabel(title)
            title_label.setProperty("role", "sectionTitle")
            self.content_layout.addWidget(title_label)
        if description:
            description_label = QLabel(description)
            description_label.setProperty("role", "muted")
            description_label.setWordWrap(True)
            self.content_layout.addWidget(description_label)


class PageHeader(QWidget):
    def __init__(self, eyebrow: str, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(5)
        eyebrow_label = QLabel(eyebrow.upper())
        eyebrow_label.setProperty("role", "eyebrow")
        title_label = QLabel(title)
        title_label.setProperty("role", "pageTitle")
        description_label = QLabel(description)
        description_label.setProperty("role", "muted")
        description_label.setWordWrap(True)
        layout.addWidget(eyebrow_label)
        layout.addWidget(title_label)
        layout.addWidget(description_label)


class NoticeBanner(QFrame):
    def __init__(self, status: str, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        label = QLabel(status.upper())
        label.setProperty("status", status)
        label.setProperty("role", "eyebrow")
        label.setMinimumWidth(72)
        copy = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setProperty("role", "sectionTitle")
        message_label = QLabel(message)
        message_label.setProperty("role", "muted")
        message_label.setWordWrap(True)
        copy.addWidget(title_label)
        copy.addWidget(message_label)
        layout.addWidget(label)
        layout.addLayout(copy, 1)


class EmptyState(Surface):
    action_requested = Signal()

    def __init__(self, title: str, message: str, action: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.content_layout.addStretch(1)
        title_label = QLabel(title)
        title_label.setProperty("role", "pageTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label = QLabel(message)
        message_label.setProperty("role", "muted")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button = QPushButton(action)
        button.setProperty("variant", "primary")
        button.clicked.connect(self.action_requested)
        button_row.addWidget(button)
        button_row.addStretch(1)
        self.content_layout.addWidget(title_label)
        self.content_layout.addWidget(message_label)
        self.content_layout.addSpacing(8)
        self.content_layout.addLayout(button_row)
        self.content_layout.addStretch(1)


class InspectorRow(QWidget):
    def __init__(self, label: str, value: str, *, technical: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        key = QLabel(label)
        key.setProperty("role", "muted")
        self.value_label = QLabel(value)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if technical:
            self.value_label.setProperty("role", "technical")
        layout.addWidget(key)
        layout.addStretch(1)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
