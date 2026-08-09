from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.models import ClonePreview, OrbitalElements
from ..core.orbits import PRESETS, degrees_to_radians, radians_to_degrees
from ..core.session import StarForgeSession
from .components import InspectorRow, NavButton, NoticeBanner, PageHeader, Surface
from .theme import application_stylesheet

PROJECT_PAGE = 0
EXPLORE_PAGE = 1
CREATE_PAGE = 2
ORBITS_PAGE = 3
REVIEW_PAGE = 4


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.session: StarForgeSession | None = None
        self.current_preview: ClonePreview | None = None
        self.design_preview_mode = False
        self.setWindowTitle("StarForge")
        self.setMinimumSize(1080, 720)
        self.resize(1440, 900)
        self.setStyleSheet(application_stylesheet())
        self._build_ui()
        self._install_shortcuts()
        self._set_enabled(False)
        self.navigate(PROJECT_PAGE)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_topbar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_project_page())
        self.pages.addWidget(self._build_explore_page())
        self.pages.addWidget(self._build_create_page())
        self.pages.addWidget(self._build_orbits_page())
        self.pages.addWidget(self._build_review_page())
        content_layout.addWidget(self.pages, 1)
        content_layout.addWidget(self._build_change_tray())
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(224)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 22, 16, 18)
        layout.setSpacing(8)

        brand = QLabel("STARFORGE")
        brand.setProperty("role", "pageTitle")
        subtitle = QLabel("ORBITAL WORKSHOP")
        subtitle.setProperty("role", "eyebrow")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[NavButton] = []
        for index, (label, hint) in enumerate(
            (
                ("Project", "Ctrl+1"),
                ("Explore", "Ctrl+2"),
                ("Create", "Ctrl+3"),
                ("Orbits", "Ctrl+4"),
                ("Review", "Ctrl+5"),
            )
        ):
            button = NavButton(label, hint)
            button.clicked.connect(lambda _checked=False, page=index: self.navigate(page))
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch(1)
        version = QLabel("PRE-ALPHA  ·  0.2")
        version.setProperty("role", "muted")
        layout.addWidget(version)
        return sidebar

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(72)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)
        project_copy = QVBoxLayout()
        project_copy.setSpacing(2)
        self.project_name_label = QLabel("No project open")
        self.project_name_label.setProperty("role", "sectionTitle")
        self.project_path_label = QLabel("Your source and destination files stay protected")
        self.project_path_label.setProperty("role", "muted")
        project_copy.addWidget(self.project_name_label)
        project_copy.addWidget(self.project_path_label)
        layout.addLayout(project_copy)
        layout.addStretch(1)
        self.validation_label = QLabel("●  Waiting for project")
        self.validation_label.setProperty("status", "warning")
        self.open_button = QPushButton("Open project")
        self.open_button.setProperty("variant", "primary")
        self.open_button.clicked.connect(self.open_session)
        layout.addWidget(self.validation_label)
        layout.addWidget(self.open_button)
        return bar

    def _page_scaffold(self, header: PageHeader) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(header)
        return page, layout

    def _build_project_page(self) -> QWidget:
        page, layout = self._page_scaffold(
            PageHeader(
                "Project setup",
                "Start with protected inputs",
                "Choose a source master and the plugin you want to extend. StarForge writes a new output by default.",
            )
        )
        columns = QHBoxLayout()
        columns.setSpacing(18)

        welcome = Surface("Open a StarForge project", "A short preflight runs before any editing tools are enabled.")
        welcome.content_layout.addWidget(
            NoticeBanner(
                "success",
                "Non-destructive by design",
                "Preview never writes. Export validates a temporary file before publishing the result.",
            )
        )
        open_project = QPushButton("Choose source and destination")
        open_project.setProperty("variant", "primary")
        open_project.clicked.connect(self.open_session)
        design_preview = QPushButton("Explore the interface")
        design_preview.setProperty("variant", "ghost")
        design_preview.setToolTip("Loads representative labels only; no files are opened or changed.")
        design_preview.clicked.connect(self.enter_design_preview)
        welcome.content_layout.addStretch(1)
        welcome.content_layout.addWidget(open_project)
        welcome.content_layout.addWidget(design_preview)

        inputs = Surface(
            "Protected inputs", "These files are read into memory and remain unchanged unless explicitly replaced."
        )
        self.source_label = QLabel("Source master\nNot selected")
        self.source_label.setProperty("role", "technical")
        self.dest_label = QLabel("Destination plugin\nNot selected")
        self.dest_label.setProperty("role", "technical")
        inputs.content_layout.addWidget(self.source_label)
        inputs.content_layout.addWidget(self.dest_label)
        inputs.content_layout.addStretch(1)
        columns.addWidget(welcome, 3)
        columns.addWidget(inputs, 2)
        layout.addLayout(columns, 1)
        return page

    def _build_explore_page(self) -> QWidget:
        page, layout = self._page_scaffold(
            PageHeader(
                "Destination plugin",
                "Explore the system hierarchy",
                "Browse human-readable objects first. Technical IDs remain visible "
                "in the inspector when you need them.",
            )
        )
        splitter = QSplitter(Qt.Orientation.Horizontal)
        hierarchy = Surface("System hierarchy", "Search and select an object to inspect.")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search stars, planets, and moons")
        self.search_input.setAccessibleName("Search system hierarchy")
        self.search_input.textChanged.connect(self._filter_hierarchy)
        self.star_list = QListWidget()
        self.star_list.setAccessibleName("Destination stars")
        self.star_list.currentRowChanged.connect(self._on_star_changed)
        self.hierarchy_planet_list = QListWidget()
        self.hierarchy_planet_list.setAccessibleName("Destination planets and moons")
        self.hierarchy_planet_list.currentRowChanged.connect(self._on_hierarchy_planet_changed)
        hierarchy.content_layout.addWidget(self.search_input)
        hierarchy.content_layout.addWidget(QLabel("Stars"))
        hierarchy.content_layout.addWidget(self.star_list, 1)
        hierarchy.content_layout.addWidget(QLabel("Planets and moons"))
        hierarchy.content_layout.addWidget(self.hierarchy_planet_list, 2)

        inspector = Surface("Inspector", "Selected-object details and safe quick actions.")
        self.inspector_name = QLabel("Nothing selected")
        self.inspector_name.setProperty("role", "pageTitle")
        self.inspector_kind = QLabel("Select a star, planet, or moon")
        self.inspector_kind.setProperty("role", "muted")
        self.inspector_details = QVBoxLayout()
        self.inspector_details.addWidget(InspectorRow("Form ID", "—", technical=True))
        self.inspector_details.addWidget(InspectorRow("System ID", "—", technical=True))
        self.inspector_details.addWidget(InspectorRow("Editor ID", "—", technical=True))
        inspector.content_layout.addWidget(self.inspector_name)
        inspector.content_layout.addWidget(self.inspector_kind)
        inspector.content_layout.addLayout(self.inspector_details)
        inspector.content_layout.addSpacing(8)
        inspector.content_layout.addWidget(QLabel("System ID"))
        self.system_id_input = QLineEdit()
        self.system_id_input.setAccessibleName("New system ID")
        self.randomize_button = QPushButton("Allocate safe ID")
        self.randomize_button.clicked.connect(self.randomize_system_id)
        self.apply_system_id_button = QPushButton("Stage system ID change")
        self.apply_system_id_button.setProperty("variant", "primary")
        self.apply_system_id_button.clicked.connect(self.apply_system_id)
        inspector.content_layout.addWidget(self.system_id_input)
        inspector.content_layout.addWidget(self.randomize_button)
        inspector.content_layout.addWidget(self.apply_system_id_button)
        inspector.content_layout.addStretch(1)
        splitter.addWidget(hierarchy)
        splitter.addWidget(inspector)
        splitter.setSizes([560, 420])
        layout.addWidget(splitter, 1)
        return page

    def _build_create_page(self) -> QWidget:
        page, layout = self._page_scaffold(
            PageHeader(
                "Guided creation",
                "Clone a star, planet, or moon",
                "Choose a known-good template, name the new body, then review every planned record before staging it.",
            )
        )
        columns = QSplitter(Qt.Orientation.Horizontal)
        form_surface = Surface(
            "1. Describe the new body", "Only fields relevant to the selected body type remain active."
        )
        form = QFormLayout()
        form.setSpacing(12)
        self.create_form = form
        self.clone_mode_combo = QComboBox()
        self.clone_mode_combo.addItems(["Star", "Planet", "Moon"])
        self.clone_mode_combo.currentIndexChanged.connect(self._refresh_clone_mode)
        self.source_star_combo = QComboBox()
        self.source_planet_combo = QComboBox()
        self.destination_star_combo = QComboBox()
        self.destination_parent_combo = QComboBox()
        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("Shown in game")
        self.new_editor_id_input = QLineEdit()
        self.new_editor_id_input.setPlaceholderText("Generated when left blank")
        self.extract_biom_checkbox = QCheckBox("Extract biome data when available")
        self.extract_biom_checkbox.setChecked(True)
        self.position_x_input = QLineEdit()
        self.position_y_input = QLineEdit()
        self.position_z_input = QLineEdit()
        form.addRow("Body type", self.clone_mode_combo)
        form.addRow("Source star", self.source_star_combo)
        form.addRow("Source planet or moon", self.source_planet_combo)
        form.addRow("Destination star", self.destination_star_combo)
        form.addRow("Parent planet", self.destination_parent_combo)
        form.addRow("Display name", self.new_name_input)
        form.addRow("Editor ID", self.new_editor_id_input)
        form.addRow("Position X", self.position_x_input)
        form.addRow("Position Y", self.position_y_input)
        form.addRow("Position Z", self.position_z_input)
        form.addRow("", self.extract_biom_checkbox)
        form_surface.content_layout.addLayout(form)
        form_surface.content_layout.addStretch(1)
        self.preview_button = QPushButton("Generate preview")
        self.preview_button.setProperty("variant", "primary")
        self.preview_button.clicked.connect(self.preview_clone)
        form_surface.content_layout.addWidget(self.preview_button)

        preview_surface = Surface("2. Review the plan", "Nothing is changed until this preview is staged and applied.")
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Your change summary will appear here.")
        preview_surface.content_layout.addWidget(self.preview_text, 1)
        preview_actions = QHBoxLayout()
        self.stage_button = QPushButton("Stage change")
        self.stage_button.setProperty("variant", "primary")
        self.stage_button.clicked.connect(self.stage_preview)
        self.apply_preview_button = QPushButton("Apply now")
        self.apply_preview_button.clicked.connect(self.apply_current_preview)
        preview_actions.addWidget(self.stage_button)
        preview_actions.addWidget(self.apply_preview_button)
        preview_surface.content_layout.addLayout(preview_actions)
        columns.addWidget(form_surface)
        columns.addWidget(preview_surface)
        columns.setSizes([520, 520])
        layout.addWidget(columns, 1)
        return page

    def _build_orbits_page(self) -> QWidget:
        page, layout = self._page_scaffold(
            PageHeader(
                "Orbital editor",
                "Shape an orbit with guardrails",
                "Start from a descriptive preset or open the advanced values. "
                "Dependent values are validated before staging.",
            )
        )
        splitter = QSplitter(Qt.Orientation.Horizontal)
        body_surface = Surface("Choose a body", "Planet and moon orbits are edited in destination context.")
        self.planet_list = QListWidget()
        self.planet_list.setAccessibleName("Bodies with orbital data")
        self.planet_list.currentRowChanged.connect(self._on_planet_changed)
        body_surface.content_layout.addWidget(self.planet_list, 1)

        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setFrameShape(QFrame.Shape.NoFrame)
        editor_surface = Surface(
            "Orbit controls", "Presets update the advanced values so the result stays inspectable."
        )
        preset_grid = QGridLayout()
        preset_grid.setSpacing(8)
        self.preset_buttons: list[QPushButton] = []
        for index, preset in enumerate(PRESETS):
            button = QPushButton(preset.label)
            button.setToolTip(preset.description)
            button.clicked.connect(lambda _checked=False, key=preset.key: self.apply_preset(key))
            preset_grid.addWidget(button, index // 3, index % 3)
            self.preset_buttons.append(button)
        editor_surface.content_layout.addLayout(preset_grid)
        self.advanced_orbit_button = QPushButton("Show advanced values")
        self.advanced_orbit_button.setCheckable(True)
        self.advanced_orbit_button.setProperty("variant", "ghost")
        self.advanced_orbit_button.toggled.connect(self._toggle_advanced_orbit)
        editor_surface.content_layout.addWidget(self.advanced_orbit_button)
        self.orbit_advanced_widget = QWidget()
        form = QFormLayout()
        self.orbit_advanced_widget.setLayout(form)
        form.setSpacing(10)
        self.orbit_fields: dict[str, QLineEdit] = {}
        labels = {
            "major_axis": "Major axis",
            "minor_axis": "Minor axis",
            "aphelion": "Aphelion",
            "eccentricity": "Eccentricity",
            "incline_degrees": "Inclination (degrees)",
            "mean_orbit": "Mean orbit",
            "axial_tilt_degrees": "Axial tilt (degrees)",
            "rotational_velocity": "Rotational velocity",
            "start_angle": "Start angle",
            "perihelion_angle": "Perihelion angle",
        }
        for field, label in labels.items():
            widget = QLineEdit()
            widget.setAccessibleName(label)
            self.orbit_fields[field] = widget
            form.addRow(label, widget)
        self.orbit_advanced_widget.setVisible(False)
        editor_surface.content_layout.addWidget(self.orbit_advanced_widget)
        self.apply_orbit_button = QPushButton("Stage orbital change")
        self.apply_orbit_button.setProperty("variant", "primary")
        self.apply_orbit_button.clicked.connect(self.apply_orbit)
        editor_surface.content_layout.addWidget(self.apply_orbit_button)
        editor_scroll.setWidget(editor_surface)
        splitter.addWidget(body_surface)
        splitter.addWidget(editor_scroll)
        splitter.setSizes([360, 700])
        layout.addWidget(splitter, 1)
        return page

    def _build_review_page(self) -> QWidget:
        page, layout = self._page_scaffold(
            PageHeader(
                "Change review",
                "Know exactly what will be written",
                "Resolve warnings, inspect technical details when needed, and export to a new validated plugin.",
            )
        )
        self.review_notice = NoticeBanner(
            "success", "Ready when you are", "No blocking validation issues are present in the current change set."
        )
        layout.addWidget(self.review_notice)
        columns = QSplitter(Qt.Orientation.Horizontal)
        changes = Surface("Pending changes", "Changes remain in memory until you export.")
        self.draft_list = QListWidget()
        self.draft_list.setAccessibleName("Staged changes")
        changes.content_layout.addWidget(self.draft_list, 1)
        draft_actions = QHBoxLayout()
        self.apply_draft_button = QPushButton("Apply selected")
        self.apply_draft_button.clicked.connect(self.apply_selected_draft)
        self.apply_all_button = QPushButton("Apply all")
        self.apply_all_button.setProperty("variant", "primary")
        self.apply_all_button.clicked.connect(self.apply_all_drafts)
        self.discard_draft_button = QPushButton("Discard")
        self.discard_draft_button.setProperty("variant", "ghost")
        self.discard_draft_button.clicked.connect(self.discard_selected_draft)
        draft_actions.addWidget(self.apply_draft_button)
        draft_actions.addWidget(self.apply_all_button)
        draft_actions.addWidget(self.discard_draft_button)
        changes.content_layout.addLayout(draft_actions)

        export = Surface("Export", "StarForge preserves both inputs unless you explicitly choose otherwise.")
        export.content_layout.addWidget(InspectorRow("Source master", "Protected"))
        export.content_layout.addWidget(InspectorRow("Destination plugin", "Protected"))
        export.content_layout.addWidget(InspectorRow("Output strategy", "Create new plugin"))
        export.content_layout.addStretch(1)
        self.save_button = QPushButton("Choose output and export")
        self.save_button.setProperty("variant", "primary")
        self.save_button.clicked.connect(self.save_as)
        export.content_layout.addWidget(self.save_button)
        columns.addWidget(changes)
        columns.addWidget(export)
        columns.setSizes([620, 420])
        layout.addWidget(columns, 1)
        return page

    def _build_change_tray(self) -> QWidget:
        tray = QWidget()
        tray.setObjectName("ChangeTray")
        tray.setFixedHeight(68)
        layout = QHBoxLayout(tray)
        layout.setContentsMargins(24, 0, 24, 0)
        self.change_count_label = QLabel("0 pending changes")
        self.change_count_label.setProperty("role", "sectionTitle")
        self.status_label = QLabel("Open a source and destination plugin to begin.")
        self.status_label.setProperty("role", "muted")
        review_button = QPushButton("Review changes")
        review_button.clicked.connect(lambda: self.navigate(REVIEW_PAGE))
        layout.addWidget(self.change_count_label)
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        layout.addWidget(review_button)
        return tray

    def _install_shortcuts(self) -> None:
        for index in range(5):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda page=index: self.navigate(page))
        QShortcut(QKeySequence.StandardKey.Open, self).activated.connect(self.open_session)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.save_as)

    def navigate(self, page: int) -> None:
        self.pages.setCurrentIndex(page)
        self.nav_buttons[page].setChecked(True)

    def _set_enabled(self, enabled: bool) -> None:
        for widget in (
            self.star_list,
            self.hierarchy_planet_list,
            self.planet_list,
            self.system_id_input,
            self.randomize_button,
            self.apply_system_id_button,
            self.clone_mode_combo,
            self.source_star_combo,
            self.source_planet_combo,
            self.destination_star_combo,
            self.destination_parent_combo,
            self.new_name_input,
            self.new_editor_id_input,
            self.position_x_input,
            self.position_y_input,
            self.position_z_input,
            self.extract_biom_checkbox,
            self.preview_button,
            self.stage_button,
            self.apply_preview_button,
            self.draft_list,
            self.apply_draft_button,
            self.apply_all_button,
            self.discard_draft_button,
            self.apply_orbit_button,
            self.save_button,
        ):
            widget.setEnabled(enabled)
        for widget in self.orbit_fields.values():
            widget.setEnabled(enabled)
        for button in self.preset_buttons:
            button.setEnabled(enabled)

    def open_session(self) -> None:
        source_path_str, _ = QFileDialog.getOpenFileName(self, "Select source master", "", "Plugins (*.esm *.esp)")
        if not source_path_str:
            return
        dest_path_str, _ = QFileDialog.getOpenFileName(self, "Select destination plugin", "", "Plugins (*.esm *.esp)")
        if not dest_path_str:
            return
        try:
            self.session = StarForgeSession(Path(source_path_str), Path(dest_path_str))
        except Exception as exc:
            QMessageBox.critical(self, "Project could not be opened", str(exc))
            return
        self.design_preview_mode = False
        self.current_preview = None
        self.source_label.setText(f"Source master\n{source_path_str}")
        self.dest_label.setText(f"Destination plugin\n{dest_path_str}")
        self.project_name_label.setText(Path(dest_path_str).stem)
        self.project_path_label.setText(dest_path_str)
        self.validation_label.setText("●  Inputs validated")
        self.validation_label.setProperty("status", "success")
        self.validation_label.style().unpolish(self.validation_label)
        self.validation_label.style().polish(self.validation_label)
        self._populate_lists()
        self._set_enabled(True)
        self._refresh_clone_mode()
        self._update_change_tray()
        self.navigate(EXPLORE_PAGE)

    def enter_design_preview(self) -> None:
        self.session = None
        self.design_preview_mode = True
        self.current_preview = None
        self.source_label.setText("Source master\nStarfield.esm  ·  protected")
        self.dest_label.setText("Destination plugin\nAsterVale.esp  ·  protected")
        self.project_name_label.setText("Aster Vale")
        self.project_path_label.setText("Design preview — no files are open or changed")
        self.validation_label.setText("●  Preview data")
        self.validation_label.setProperty("status", "success")
        self._populate_demo()
        self._set_enabled(True)
        self.save_button.setEnabled(False)
        self._refresh_clone_mode()
        self.status_label.setText("Exploring representative Phase 3 interface data.")
        self.navigate(EXPLORE_PAGE)

    def _populate_demo(self) -> None:
        for widget in (
            self.star_list,
            self.hierarchy_planet_list,
            self.planet_list,
            self.source_star_combo,
            self.source_planet_combo,
            self.destination_star_combo,
            self.destination_parent_combo,
            self.draft_list,
        ):
            widget.clear()
        self.star_list.addItems(["Aster Vale  ·  6 bodies", "Pytheas  ·  3 bodies"])
        bodies = ["Planet  Aster I", "Planet  Verdantia", "Moon    Verdantia Minor", "Planet  Cinder"]
        self.hierarchy_planet_list.addItems(bodies)
        self.planet_list.addItems(bodies)
        self.source_star_combo.addItems(["Sol", "Narion", "Cheyenne"])
        self.destination_star_combo.addItems(["Aster Vale", "Pytheas"])
        self.destination_parent_combo.addItems(["Aster I", "Verdantia", "Cinder"])
        self.draft_list.addItems(["CREATE  Verdantia Minor", "ORBIT  Cinder — Wide Stable"])
        self.change_count_label.setText("2 pending changes")
        self.star_list.setCurrentRow(0)
        self.planet_list.setCurrentRow(1)

    def save_as(self) -> None:
        if self.session is None:
            return
        output_path_str, _ = QFileDialog.getSaveFileName(self, "Export edited plugin", "", "Plugins (*.esm *.esp)")
        if not output_path_str:
            return
        try:
            self.session.save_as(Path(output_path_str))
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self._update_change_tray()

    def _populate_lists(self) -> None:
        assert self.session is not None
        for widget in (
            self.star_list,
            self.hierarchy_planet_list,
            self.planet_list,
            self.source_star_combo,
            self.source_planet_combo,
            self.destination_star_combo,
            self.destination_parent_combo,
            self.draft_list,
        ):
            widget.clear()
        for star in self.session.view.stars:
            label = f"{star.display_name or star.editor_id or hex(star.form_id)}  ·  0x{star.system_id:08X}"
            self.star_list.addItem(label)
            self.destination_star_combo.addItem(label, star.form_id)
        for star in self.session.view.source_stars:
            label = f"{star.display_name or star.editor_id or hex(star.form_id)}  ·  0x{star.system_id:08X}"
            self.source_star_combo.addItem(label, star.form_id)
        for planet in self.session.view.planets:
            prefix = "Moon" if planet.is_moon else "Planet"
            body_name = planet.display_name or planet.editor_id or hex(planet.form_id)
            label = f"{prefix}  {body_name}  ·  local {planet.local_id}"
            self.hierarchy_planet_list.addItem(label)
            self.planet_list.addItem(label)
            if not planet.is_moon:
                self.destination_parent_combo.addItem(label, planet.form_id)
        for draft in self.session.state.draft_previews:
            self.draft_list.addItem(f"{draft.draft_id}  {draft.kind.upper()}  {draft.new_display_name}")
        self.preview_text.setPlainText(
            "\n".join(self.current_preview.draft.preview_lines) if self.current_preview else ""
        )
        if self.star_list.count():
            self.star_list.setCurrentRow(0)
        if self.planet_list.count():
            self.planet_list.setCurrentRow(0)
        self._update_change_tray()

    def _refresh_clone_mode(self) -> None:
        mode = self.clone_mode_combo.currentText()
        is_star = mode == "Star"
        is_moon = mode == "Moon"
        self.source_star_combo.setEnabled(is_star)
        self._populate_source_body_templates(mode)
        self.destination_star_combo.setEnabled(mode == "Planet")
        self.destination_parent_combo.setEnabled(is_moon)
        for widget in (self.position_x_input, self.position_y_input, self.position_z_input):
            widget.setEnabled(is_star)
        self.extract_biom_checkbox.setEnabled(not is_star)
        self.create_form.setRowVisible(self.source_star_combo, is_star)
        self.create_form.setRowVisible(self.source_planet_combo, not is_star)
        self.create_form.setRowVisible(self.destination_star_combo, mode == "Planet")
        self.create_form.setRowVisible(self.destination_parent_combo, is_moon)
        for widget in (self.position_x_input, self.position_y_input, self.position_z_input):
            self.create_form.setRowVisible(widget, is_star)
        self.create_form.setRowVisible(self.extract_biom_checkbox, not is_star)

    def _populate_source_body_templates(self, mode: str) -> None:
        self.source_planet_combo.clear()
        if mode == "Star":
            return
        want_moon = mode == "Moon"
        field_label = self.create_form.labelForField(self.source_planet_combo)
        if isinstance(field_label, QLabel):
            field_label.setText("Source moon" if want_moon else "Source planet")

        if self.design_preview_mode:
            demo_templates = (
                (("Luna", 0x10), ("Phobos", 0x11))
                if want_moon
                else (("Jemison", 0x20), ("Akila", 0x21), ("Kreet", 0x22))
            )
            for label, form_id in demo_templates:
                self.source_planet_combo.addItem(label, form_id)
        elif self.session is not None:
            for planet in self.session.view.source_planets:
                if planet.is_moon != want_moon:
                    continue
                label = planet.display_name or planet.editor_id or hex(planet.form_id)
                self.source_planet_combo.addItem(label, planet.form_id)

        has_templates = self.source_planet_combo.count() > 0
        if not has_templates:
            body_type = "moon" if want_moon else "planet"
            self.source_planet_combo.addItem(f"No {body_type} templates available", None)
        self.source_planet_combo.setEnabled(has_templates)

    def _filter_hierarchy(self, query: str) -> None:
        normalized = query.strip().casefold()
        for widget in (self.star_list, self.hierarchy_planet_list):
            for row in range(widget.count()):
                item = widget.item(row)
                item.setHidden(bool(normalized) and normalized not in item.text().casefold())

    def _toggle_advanced_orbit(self, visible: bool) -> None:
        self.orbit_advanced_widget.setVisible(visible)
        self.advanced_orbit_button.setText("Hide advanced values" if visible else "Show advanced values")

    def _on_star_changed(self, row: int) -> None:
        if self.design_preview_mode and row >= 0:
            self.system_id_input.setText("4096")
            self.inspector_name.setText(self.star_list.item(row).text().split("  ·")[0])
            self.inspector_kind.setText("Star system")
            return
        if self.session is None or row < 0 or row >= len(self.session.view.stars):
            self.system_id_input.clear()
            return
        star = self.session.view.stars[row]
        self.system_id_input.setText(str(star.system_id))
        self.inspector_name.setText(star.display_name or star.editor_id or hex(star.form_id))
        self.inspector_kind.setText("Star system")

    def _on_hierarchy_planet_changed(self, row: int) -> None:
        if row < 0:
            return
        if self.design_preview_mode:
            self.inspector_name.setText(self.hierarchy_planet_list.item(row).text().strip())
            self.inspector_kind.setText("Moon" if "Moon" in self.hierarchy_planet_list.item(row).text() else "Planet")
            return
        if self.session is None or row >= len(self.session.view.planets):
            return
        planet = self.session.view.planets[row]
        self.inspector_name.setText(planet.display_name or planet.editor_id or hex(planet.form_id))
        self.inspector_kind.setText("Moon" if planet.is_moon else "Planet")

    def _on_planet_changed(self, row: int) -> None:
        if self.design_preview_mode and row >= 0:
            self._load_orbit_fields(
                OrbitalElements(95_000.0, 94_998.0, 95_650.0, 0.0069, 0.1, 0.5, 0.2, 1.0, 0.0, 0.0, True, False)
            )
            return
        if self.session is None or row < 0 or row >= len(self.session.view.planets):
            for widget in self.orbit_fields.values():
                widget.clear()
            return
        self._load_orbit_fields(self.session.view.planets[row].orbit)

    def _load_orbit_fields(self, orbit: OrbitalElements | None) -> None:
        if orbit is None:
            for widget in self.orbit_fields.values():
                widget.clear()
            return
        values = {
            "major_axis": orbit.major_axis,
            "minor_axis": orbit.minor_axis,
            "aphelion": orbit.aphelion,
            "eccentricity": orbit.eccentricity,
            "incline_degrees": radians_to_degrees(orbit.incline_radians),
            "mean_orbit": orbit.mean_orbit,
            "axial_tilt_degrees": radians_to_degrees(orbit.axial_tilt_radians),
            "rotational_velocity": orbit.rotational_velocity,
            "start_angle": orbit.start_angle,
            "perihelion_angle": orbit.perihelion_angle,
        }
        for key, value in values.items():
            self.orbit_fields[key].setText(f"{value:.6f}")

    def randomize_system_id(self) -> None:
        if self.design_preview_mode:
            self.system_id_input.setText("4097")
        elif self.session is not None:
            self.system_id_input.setText(str(self.session.allocate_system_id()))

    def apply_system_id(self) -> None:
        if self.session is None:
            return
        row = self.star_list.currentRow()
        if row < 0:
            return
        try:
            self.session.set_star_system_id(self.session.view.stars[row].form_id, int(self.system_id_input.text()))
        except Exception as exc:
            QMessageBox.critical(self, "System ID update failed", str(exc))
            return
        self._populate_lists()

    def preview_clone(self) -> None:
        if self.design_preview_mode:
            self.preview_text.setPlainText(
                "Create planet ‘Pelagos’\n\n"
                "Template\n  Jemison\n\n"
                "Destination\n  Aster Vale\n\n"
                "Planned records\n  Planet data\n  Main, orbit, and surface locations\n\n"
                "Safety\n  No files changed · ready to stage"
            )
            self.status_label.setText("Preview generated. No files were changed.")
            return
        if self.session is None:
            return
        try:
            self.current_preview = self._build_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Preview failed", str(exc))
            return
        self.preview_text.setPlainText(
            "\n".join(self.current_preview.hard_errors or self.current_preview.draft.preview_lines)
        )
        self.status_label.setText(f"Previewed {self.current_preview.draft.kind} draft. No files changed.")

    def stage_preview(self) -> None:
        if self.session is None or self.current_preview is None:
            return
        try:
            self.session.stage_draft(self.current_preview)
        except Exception as exc:
            QMessageBox.critical(self, "Stage failed", str(exc))
            return
        self._populate_lists()
        self.navigate(REVIEW_PAGE)

    def apply_current_preview(self) -> None:
        if self.session is None or self.current_preview is None:
            return
        try:
            draft = self.session.stage_draft(self.current_preview)
            self.session.apply_draft(draft.draft_id)
        except Exception as exc:
            QMessageBox.critical(self, "Apply failed", str(exc))
            return
        self.current_preview = None
        self._populate_lists()

    def apply_selected_draft(self) -> None:
        if self.session is None or self.draft_list.currentRow() < 0:
            return
        draft_id = self.draft_list.currentItem().text().split()[0]
        try:
            self.session.apply_draft(draft_id)
        except Exception as exc:
            QMessageBox.critical(self, "Apply draft failed", str(exc))
            return
        self._populate_lists()

    def apply_all_drafts(self) -> None:
        if self.session is None:
            return
        try:
            self.session.apply_all_drafts()
        except Exception as exc:
            QMessageBox.critical(self, "Apply all failed", str(exc))
            return
        self.current_preview = None
        self._populate_lists()

    def discard_selected_draft(self) -> None:
        if self.session is None or self.draft_list.currentRow() < 0:
            return
        draft_id = self.draft_list.currentItem().text().split()[0]
        self.session.discard_draft(draft_id)
        self._populate_lists()

    def _build_preview(self) -> ClonePreview:
        assert self.session is not None
        mode = self.clone_mode_combo.currentText()
        new_name = self.new_name_input.text().strip()
        new_editor_id = self.new_editor_id_input.text().strip()
        orbit_override = self._collect_orbit_override()
        if mode == "Star":
            form_id = int(self.source_star_combo.currentData())
            source_star = next(item for item in self.session.view.source_stars if item.form_id == form_id)
            system_id = (
                int(self.system_id_input.text())
                if self.system_id_input.text().strip()
                else self.session.allocate_system_id()
            )
            return self.session.preview_star_clone(
                source_star_form_id=form_id,
                new_editor_id=new_editor_id or f"{source_star.editor_id or 'NewStar'}Clone",
                new_display_name=new_name or f"{source_star.display_name or 'NewStar'} Clone",
                system_id=system_id,
                position=(
                    float(self.position_x_input.text() or 0.0),
                    float(self.position_y_input.text() or 0.0),
                    float(self.position_z_input.text() or 0.0),
                ),
            )
        selected_source_form_id = self.source_planet_combo.currentData()
        if selected_source_form_id is None:
            body_type = "moon" if mode == "Moon" else "planet"
            raise ValueError(f"No {body_type} templates are available in the source plugin.")
        source_form_id = int(selected_source_form_id)
        source_planet = next(item for item in self.session.view.source_planets if item.form_id == source_form_id)
        new_name = new_name or f"{source_planet.display_name or ('NewMoon' if mode == 'Moon' else 'NewPlanet')} Clone"
        new_editor_id = (
            new_editor_id or f"{source_planet.editor_id or ('NewMoon' if mode == 'Moon' else 'NewPlanet')}Clone"
        )
        if mode == "Planet":
            return self.session.preview_planet_clone(
                source_planet_form_id=source_form_id,
                destination_star_form_id=int(self.destination_star_combo.currentData()),
                new_editor_id=new_editor_id,
                new_display_name=new_name,
                extract_biom=self.extract_biom_checkbox.isChecked(),
                orbit_override=orbit_override,
            )
        return self.session.preview_moon_clone(
            source_moon_form_id=source_form_id,
            destination_parent_planet_form_id=int(self.destination_parent_combo.currentData()),
            new_editor_id=new_editor_id,
            new_display_name=new_name,
            extract_biom=self.extract_biom_checkbox.isChecked(),
            orbit_override=orbit_override,
        )

    def _collect_orbit_override(self) -> OrbitalElements | None:
        if any(not widget.text().strip() for widget in self.orbit_fields.values()):
            return None
        return OrbitalElements(
            major_axis=float(self.orbit_fields["major_axis"].text()),
            minor_axis=float(self.orbit_fields["minor_axis"].text()),
            aphelion=float(self.orbit_fields["aphelion"].text()),
            eccentricity=float(self.orbit_fields["eccentricity"].text()),
            incline_radians=degrees_to_radians(float(self.orbit_fields["incline_degrees"].text())),
            mean_orbit=float(self.orbit_fields["mean_orbit"].text()),
            axial_tilt_radians=degrees_to_radians(float(self.orbit_fields["axial_tilt_degrees"].text())),
            rotational_velocity=float(self.orbit_fields["rotational_velocity"].text()),
            start_angle=float(self.orbit_fields["start_angle"].text()),
            perihelion_angle=float(self.orbit_fields["perihelion_angle"].text()),
            apply_orbital_motion=True,
            geostationary=False,
        )

    def apply_preset(self, preset_key: str) -> None:
        if self.design_preview_mode:
            self.status_label.setText(f"Previewed {preset_key.replace('_', ' ')} preset. No files changed.")
            return
        if self.session is None or self.planet_list.currentRow() < 0:
            return
        try:
            orbit = self.session.apply_preset(
                self.session.view.planets[self.planet_list.currentRow()].form_id, preset_key
            )
        except Exception as exc:
            QMessageBox.critical(self, "Preset failed", str(exc))
            return
        self._load_orbit_fields(orbit)
        self._update_change_tray()

    def apply_orbit(self) -> None:
        if self.session is None or self.planet_list.currentRow() < 0:
            return
        try:
            orbit = self._collect_orbit_override()
            if orbit is None:
                raise ValueError("Fill all orbit fields before staging the change.")
            self.session.set_planet_orbit(self.session.view.planets[self.planet_list.currentRow()].form_id, orbit)
        except Exception as exc:
            QMessageBox.critical(self, "Orbit update failed", str(exc))
            return
        self._populate_lists()

    def _update_change_tray(self) -> None:
        if self.session is None:
            return
        pending = self.session.state.pending
        count = pending.applied_change_count + len(pending.staged_draft_ids)
        self.change_count_label.setText(f"{count} pending {'change' if count == 1 else 'changes'}")
        self.status_label.setText(self.session.state.status_text)
