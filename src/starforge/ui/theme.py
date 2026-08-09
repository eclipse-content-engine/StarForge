from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignTokens:
    canvas: str = "#0B0F17"
    sidebar: str = "#0E1420"
    surface: str = "#121A27"
    raised: str = "#172233"
    field: str = "#0F1622"
    selection: str = "#20354A"
    border: str = "#263449"
    text: str = "#F3F7FC"
    muted: str = "#9DABBE"
    accent: str = "#66D9EF"
    accent_strong: str = "#2CBBD8"
    warning: str = "#F4C66A"
    error: str = "#FF7A90"
    success: str = "#72D6A0"


TOKENS = DesignTokens()


def application_stylesheet(tokens: DesignTokens = TOKENS) -> str:
    return f"""
    QMainWindow, QWidget#AppRoot {{
        background: {tokens.canvas};
        color: {tokens.text};
        font-family: "Segoe UI";
        font-size: 14px;
    }}
    QWidget#Sidebar {{
        background: {tokens.sidebar};
        border-right: 1px solid {tokens.border};
    }}
    QWidget#TopBar, QWidget#ChangeTray {{
        background: {tokens.sidebar};
        border-bottom: 1px solid {tokens.border};
    }}
    QWidget#ChangeTray {{
        border-top: 1px solid {tokens.border};
        border-bottom: none;
    }}
    QFrame#Surface {{
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: 10px;
    }}
    QLabel {{ color: {tokens.text}; background: transparent; }}
    QLabel[role="muted"] {{ color: {tokens.muted}; }}
    QLabel[role="eyebrow"] {{ color: {tokens.accent}; font-size: 12px; font-weight: 600; }}
    QLabel[role="pageTitle"] {{ color: {tokens.text}; font-size: 26px; font-weight: 600; }}
    QLabel[role="sectionTitle"] {{ color: {tokens.text}; font-size: 16px; font-weight: 600; }}
    QLabel[role="technical"] {{ font-family: "Cascadia Mono"; color: {tokens.muted}; }}
    QLabel[status="success"] {{ color: {tokens.success}; }}
    QLabel[status="warning"] {{ color: {tokens.warning}; }}
    QLabel[status="error"] {{ color: {tokens.error}; }}
    QPushButton {{
        min-height: 38px;
        padding: 0 14px;
        color: {tokens.text};
        background: {tokens.raised};
        border: 1px solid {tokens.border};
        border-radius: 7px;
        font-weight: 600;
    }}
    QPushButton:hover {{ border-color: {tokens.muted}; background: #1C2A3E; }}
    QPushButton:pressed {{ background: {tokens.surface}; }}
    QPushButton:focus {{ border: 2px solid {tokens.accent}; }}
    QPushButton:disabled {{ color: #657287; background: #111823; border-color: #202B3C; }}
    QPushButton[variant="primary"] {{
        color: #061218;
        background: {tokens.accent};
        border-color: {tokens.accent};
    }}
    QPushButton[variant="primary"]:hover {{ background: {tokens.accent_strong}; }}
    QPushButton[variant="ghost"] {{ background: transparent; border-color: transparent; color: {tokens.muted}; }}
    QPushButton[variant="ghost"]:hover {{ background: {tokens.raised}; color: {tokens.text}; }}
    QPushButton[nav="true"] {{
        min-height: 44px;
        text-align: left;
        padding-left: 16px;
        background: transparent;
        border: 1px solid transparent;
        color: {tokens.muted};
    }}
    QPushButton[nav="true"]:checked {{
        color: {tokens.text};
        background: {tokens.raised};
        border-color: {tokens.border};
        border-left: 3px solid {tokens.accent};
    }}
    QLineEdit, QComboBox, QTextEdit, QListWidget {{
        color: {tokens.text};
        background: {tokens.field};
        border: 1px solid {tokens.border};
        border-radius: 7px;
        padding: 8px 10px;
        selection-background-color: {tokens.accent_strong};
    }}
    QLineEdit, QComboBox {{ min-height: 22px; }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus {{
        border: 2px solid {tokens.accent};
    }}
    QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QListWidget:disabled {{
        color: #657287; background: #111823;
    }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QComboBox QAbstractItemView {{
        color: {tokens.text};
        background: {tokens.field};
        border: 1px solid {tokens.border};
        selection-color: {tokens.text};
        selection-background-color: {tokens.selection};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{ min-height: 34px; padding: 4px 10px; }}
    QComboBox QAbstractItemView::item:hover {{ background: {tokens.raised}; color: {tokens.text}; }}
    QComboBox QAbstractItemView::item:selected {{ background: {tokens.selection}; color: {tokens.text}; }}
    QListWidget::item {{ padding: 10px; border-radius: 6px; }}
    QListWidget::item:hover {{ background: #172233; }}
    QListWidget::item:selected {{ background: {tokens.selection}; color: {tokens.text}; }}
    QCheckBox {{ color: {tokens.text}; spacing: 8px; }}
    QCheckBox::indicator {{ width: 17px; height: 17px; }}
    QCheckBox::indicator:unchecked {{
        background: {tokens.field}; border: 1px solid {tokens.border}; border-radius: 4px;
    }}
    QCheckBox::indicator:checked {{
        background: {tokens.accent}; border: 1px solid {tokens.accent}; border-radius: 4px;
    }}
    QScrollArea {{ background: transparent; border: none; }}
    QSplitter::handle {{ background: {tokens.border}; width: 1px; }}
    QScrollBar:vertical {{ background: {tokens.sidebar}; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {tokens.border}; min-height: 28px; border-radius: 5px; }}
    QScrollBar::handle:vertical:hover {{ background: {tokens.muted}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QProgressBar {{
        min-height: 8px;
        max-height: 8px;
        color: transparent;
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: 4px;
    }}
    QProgressBar::chunk {{ background: {tokens.accent}; border-radius: 3px; }}
    QToolTip {{ color: {tokens.text}; background: {tokens.raised}; border: 1px solid {tokens.border}; padding: 6px; }}
    """
