from __future__ import annotations

from pytestqt.qtbot import QtBot

from starforge.ui.main_window import CREATE_PAGE, EXPLORE_PAGE, ORBITS_PAGE, PROJECT_PAGE, REVIEW_PAGE, MainWindow


def test_main_window_opens_in_empty_state(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "StarForge"
    assert window.session is None
    assert window.status_label.text() == "Open a source and destination plugin to begin."
    assert window.pages.currentIndex() == PROJECT_PAGE
    assert window.minimumWidth() >= 1080
    assert window.minimumHeight() >= 720


def test_primary_navigation_and_keyboard_contract(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    for page in (EXPLORE_PAGE, CREATE_PAGE, ORBITS_PAGE, REVIEW_PAGE, PROJECT_PAGE):
        window.navigate(page)
        assert window.pages.currentIndex() == page
        assert window.nav_buttons[page].isChecked()


def test_design_preview_exposes_representative_workflow_without_a_session(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.enter_design_preview()

    assert window.session is None
    assert window.design_preview_mode
    assert window.pages.currentIndex() == EXPLORE_PAGE
    assert window.star_list.count() == 2
    assert window.planet_list.count() == 4
    assert window.draft_list.count() == 2
    assert not window.save_button.isEnabled()


def test_core_controls_have_accessible_names(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.search_input.accessibleName() == "Search system hierarchy"
    assert window.star_list.accessibleName() == "Destination stars"
    assert window.planet_list.accessibleName() == "Bodies with orbital data"
    assert all(field.accessibleName() for field in window.orbit_fields.values())


def test_hierarchy_search_and_advanced_orbit_disclosure(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.enter_design_preview()

    window.search_input.setText("pytheas")
    assert window.star_list.item(0).isHidden()
    assert not window.star_list.item(1).isHidden()

    assert window.orbit_advanced_widget.isHidden()
    window.navigate(ORBITS_PAGE)
    window.advanced_orbit_button.setChecked(True)
    assert not window.orbit_advanced_widget.isHidden()
