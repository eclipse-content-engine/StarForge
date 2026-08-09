from __future__ import annotations

from starforge.ui.theme import TOKENS, application_stylesheet


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_core_theme_colors_meet_wcag_aa_contrast() -> None:
    assert _contrast_ratio(TOKENS.text, TOKENS.canvas) >= 4.5
    assert _contrast_ratio(TOKENS.muted, TOKENS.surface) >= 4.5
    assert _contrast_ratio(TOKENS.accent, TOKENS.canvas) >= 4.5
    assert _contrast_ratio(TOKENS.error, TOKENS.surface) >= 4.5


def test_combo_popup_text_meets_contrast_and_has_explicit_states() -> None:
    stylesheet = application_stylesheet()

    assert _contrast_ratio(TOKENS.text, TOKENS.field) >= 4.5
    assert _contrast_ratio(TOKENS.text, TOKENS.selection) >= 4.5
    assert "QComboBox QAbstractItemView" in stylesheet
    assert f"selection-color: {TOKENS.text}" in stylesheet
    assert f"selection-background-color: {TOKENS.selection}" in stylesheet
