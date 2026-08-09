from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.models import ClonePreview, OrbitalElements
from ..core.orbits import PRESETS, degrees_to_radians, radians_to_degrees
from ..core.session import StarForgeSession


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.session: StarForgeSession | None = None
        self.current_preview: ClonePreview | None = None
        self.setWindowTitle("StarForge")
        self.resize(1500, 960)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        session_row = QHBoxLayout()
        self.source_label = QLabel("Source: none")
        self.dest_label = QLabel("Destination: none")
        self.status_label = QLabel("Open a source and destination plugin to begin.")
        open_button = QPushButton("Open Session")
        open_button.clicked.connect(self.open_session)
        save_button = QPushButton("Save As")
        save_button.clicked.connect(self.save_as)
        session_row.addWidget(open_button)
        session_row.addWidget(save_button)
        session_row.addWidget(self.source_label, 1)
        session_row.addWidget(self.dest_label, 1)
        layout.addLayout(session_row)
        layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        source_group = QGroupBox("Source Records")
        source_layout = QVBoxLayout(source_group)
        self.source_star_list = QListWidget()
        self.source_planet_list = QListWidget()
        source_layout.addWidget(QLabel("Source Stars"))
        source_layout.addWidget(self.source_star_list)
        source_layout.addWidget(QLabel("Source Planets / Moons"))
        source_layout.addWidget(self.source_planet_list)
        left_layout.addWidget(source_group)

        star_group = QGroupBox("Destination Stars")
        star_layout = QVBoxLayout(star_group)
        self.star_list = QListWidget()
        self.star_list.currentRowChanged.connect(self._on_star_changed)
        self.system_id_input = QLineEdit()
        self.randomize_button = QPushButton("Randomize System ID")
        self.randomize_button.clicked.connect(self.randomize_system_id)
        self.apply_system_id_button = QPushButton("Apply System ID")
        self.apply_system_id_button.clicked.connect(self.apply_system_id)
        star_layout.addWidget(self.star_list)
        star_layout.addWidget(QLabel("New system ID"))
        star_layout.addWidget(self.system_id_input)
        star_layout.addWidget(self.randomize_button)
        star_layout.addWidget(self.apply_system_id_button)
        left_layout.addWidget(star_group)

        planet_group = QGroupBox("Destination Planets / Moons")
        planet_layout = QVBoxLayout(planet_group)
        self.planet_list = QListWidget()
        self.planet_list.currentRowChanged.connect(self._on_planet_changed)
        planet_layout.addWidget(self.planet_list)
        left_layout.addWidget(planet_group)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        create_group = QGroupBox("Create Workspace")
        create_layout = QGridLayout(create_group)
        self.clone_mode_combo = QComboBox()
        self.clone_mode_combo.addItems(["Star", "Planet", "Moon"])
        self.clone_mode_combo.currentIndexChanged.connect(self._refresh_clone_mode)
        self.source_star_combo = QComboBox()
        self.source_planet_combo = QComboBox()
        self.destination_star_combo = QComboBox()
        self.destination_parent_combo = QComboBox()
        self.new_name_input = QLineEdit()
        self.new_editor_id_input = QLineEdit()
        self.extract_biom_checkbox = QCheckBox("Extract biome on apply")
        self.extract_biom_checkbox.setChecked(True)
        self.position_x_input = QLineEdit()
        self.position_y_input = QLineEdit()
        self.position_z_input = QLineEdit()
        create_layout.addWidget(QLabel("Mode"), 0, 0)
        create_layout.addWidget(self.clone_mode_combo, 0, 1)
        create_layout.addWidget(QLabel("Source star"), 1, 0)
        create_layout.addWidget(self.source_star_combo, 1, 1)
        create_layout.addWidget(QLabel("Source planet / moon"), 2, 0)
        create_layout.addWidget(self.source_planet_combo, 2, 1)
        create_layout.addWidget(QLabel("Destination star"), 3, 0)
        create_layout.addWidget(self.destination_star_combo, 3, 1)
        create_layout.addWidget(QLabel("Destination parent planet"), 4, 0)
        create_layout.addWidget(self.destination_parent_combo, 4, 1)
        create_layout.addWidget(QLabel("New display name"), 5, 0)
        create_layout.addWidget(self.new_name_input, 5, 1)
        create_layout.addWidget(QLabel("New editor ID"), 6, 0)
        create_layout.addWidget(self.new_editor_id_input, 6, 1)
        create_layout.addWidget(QLabel("Star X"), 7, 0)
        create_layout.addWidget(self.position_x_input, 7, 1)
        create_layout.addWidget(QLabel("Star Y"), 8, 0)
        create_layout.addWidget(self.position_y_input, 8, 1)
        create_layout.addWidget(QLabel("Star Z"), 9, 0)
        create_layout.addWidget(self.position_z_input, 9, 1)
        create_layout.addWidget(self.extract_biom_checkbox, 10, 0, 1, 2)
        preview_row = QHBoxLayout()
        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self.preview_clone)
        self.stage_button = QPushButton("Stage Draft")
        self.stage_button.clicked.connect(self.stage_preview)
        self.apply_preview_button = QPushButton("Apply Preview")
        self.apply_preview_button.clicked.connect(self.apply_current_preview)
        preview_row.addWidget(self.preview_button)
        preview_row.addWidget(self.stage_button)
        preview_row.addWidget(self.apply_preview_button)
        create_layout.addLayout(preview_row, 11, 0, 1, 2)
        right_layout.addWidget(create_group)

        draft_group = QGroupBox("Preview / Staged Drafts")
        draft_layout = QVBoxLayout(draft_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.draft_list = QListWidget()
        draft_buttons = QHBoxLayout()
        self.apply_draft_button = QPushButton("Apply Selected Draft")
        self.apply_draft_button.clicked.connect(self.apply_selected_draft)
        self.apply_all_button = QPushButton("Apply All Drafts")
        self.apply_all_button.clicked.connect(self.apply_all_drafts)
        self.discard_draft_button = QPushButton("Discard Selected Draft")
        self.discard_draft_button.clicked.connect(self.discard_selected_draft)
        draft_buttons.addWidget(self.apply_draft_button)
        draft_buttons.addWidget(self.apply_all_button)
        draft_buttons.addWidget(self.discard_draft_button)
        draft_layout.addWidget(self.preview_text, 2)
        draft_layout.addWidget(QLabel("Staged drafts"))
        draft_layout.addWidget(self.draft_list, 1)
        draft_layout.addLayout(draft_buttons)
        right_layout.addWidget(draft_group, 1)

        orbit_group = QGroupBox("Orbital Editor")
        orbit_grid = QGridLayout(orbit_group)
        self.preset_buttons: list[QPushButton] = []
        for idx, preset in enumerate(PRESETS):
            button = QPushButton(preset.label)
            button.clicked.connect(lambda _checked=False, key=preset.key: self.apply_preset(key))
            orbit_grid.addWidget(button, idx // 3, idx % 3)
            self.preset_buttons.append(button)

        self.orbit_fields: dict[str, QLineEdit] = {}
        form = QFormLayout()
        for field in (
            "major_axis",
            "minor_axis",
            "aphelion",
            "eccentricity",
            "incline_degrees",
            "mean_orbit",
            "axial_tilt_degrees",
            "rotational_velocity",
            "start_angle",
            "perihelion_angle",
        ):
            widget = QLineEdit()
            self.orbit_fields[field] = widget
            form.addRow(field.replace("_", " ").title(), widget)
        orbit_grid.addLayout(form, 2, 0, 1, 3)
        self.apply_orbit_button = QPushButton("Apply Orbit To Selected Destination Body")
        self.apply_orbit_button.clicked.connect(self.apply_orbit)
        orbit_grid.addWidget(self.apply_orbit_button, 3, 0, 1, 3)
        right_layout.addWidget(orbit_group)
        splitter.addWidget(right)

        self.setCentralWidget(root)
        self._set_enabled(False)

    def _set_enabled(self, enabled: bool) -> None:
        for widget in (
            self.star_list,
            self.source_star_list,
            self.source_planet_list,
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
        self.session = StarForgeSession(Path(source_path_str), Path(dest_path_str))
        self.current_preview = None
        self.source_label.setText(f"Source: {source_path_str}")
        self.dest_label.setText(f"Destination: {dest_path_str}")
        self._populate_lists()
        self._set_enabled(True)
        self._refresh_clone_mode()
        self.status_label.setText(self.session.state.status_text)

    def save_as(self) -> None:
        if self.session is None:
            return
        output_path_str, _ = QFileDialog.getSaveFileName(self, "Save edited plugin", "", "Plugins (*.esm *.esp)")
        if not output_path_str:
            return
        try:
            self.session.save_as(Path(output_path_str))
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self.status_label.setText(self.session.state.status_text)

    def _populate_lists(self) -> None:
        assert self.session is not None
        self.star_list.clear()
        self.planet_list.clear()
        self.source_star_list.clear()
        self.source_planet_list.clear()
        self.source_star_combo.clear()
        self.source_planet_combo.clear()
        self.destination_star_combo.clear()
        self.destination_parent_combo.clear()
        self.draft_list.clear()
        for star in self.session.view.stars:
            label = f"{star.display_name or star.editor_id or hex(star.form_id)} [0x{star.system_id:08X}]"
            self.star_list.addItem(label)
            self.destination_star_combo.addItem(label, star.form_id)
        for star in self.session.view.source_stars:
            label = f"{star.display_name or star.editor_id or hex(star.form_id)} [0x{star.system_id:08X}]"
            self.source_star_list.addItem(label)
            self.source_star_combo.addItem(label, star.form_id)
        for planet in self.session.view.planets:
            prefix = "Moon" if planet.is_moon else "Planet"
            label = (
                f"{prefix}: {planet.display_name or planet.editor_id or hex(planet.form_id)} (local {planet.local_id})"
            )
            self.planet_list.addItem(label)
            if not planet.is_moon:
                self.destination_parent_combo.addItem(label, planet.form_id)
        for planet in self.session.view.source_planets:
            prefix = "Moon" if planet.is_moon else "Planet"
            biome = " biome" if planet.has_biome else ""
            label = f"{prefix}: {planet.display_name or planet.editor_id or hex(planet.form_id)}{biome}"
            self.source_planet_list.addItem(label)
            self.source_planet_combo.addItem(label, planet.form_id)
        for draft in self.session.state.draft_previews:
            self.draft_list.addItem(f"{draft.draft_id} {draft.kind} {draft.new_display_name}")
        self.preview_text.setPlainText(
            "\n".join(self.current_preview.draft.preview_lines) if self.current_preview else ""
        )

    def _refresh_clone_mode(self) -> None:
        mode = self.clone_mode_combo.currentText()
        is_star = mode == "Star"
        is_moon = mode == "Moon"
        self.source_star_combo.setEnabled(is_star)
        self.source_planet_combo.setEnabled(not is_star)
        self.destination_star_combo.setEnabled(mode == "Planet")
        self.destination_parent_combo.setEnabled(is_moon)
        for widget in (self.position_x_input, self.position_y_input, self.position_z_input):
            widget.setEnabled(is_star)
        self.extract_biom_checkbox.setEnabled(not is_star)

    def _on_star_changed(self, row: int) -> None:
        if self.session is None or row < 0 or row >= len(self.session.view.stars):
            self.system_id_input.clear()
            return
        self.system_id_input.setText(str(self.session.view.stars[row].system_id))

    def _on_planet_changed(self, row: int) -> None:
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
        if self.session is None:
            return
        self.system_id_input.setText(str(self.session.allocate_system_id()))

    def apply_system_id(self) -> None:
        if self.session is None:
            return
        row = self.star_list.currentRow()
        if row < 0:
            return
        try:
            value = int(self.system_id_input.text())
            self.session.set_star_system_id(self.session.view.stars[row].form_id, value)
        except Exception as exc:
            QMessageBox.critical(self, "System ID update failed", str(exc))
            return
        self._populate_lists()
        self.status_label.setText(self.session.state.status_text)

    def preview_clone(self) -> None:
        if self.session is None:
            return
        try:
            self.current_preview = self._build_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Preview failed", str(exc))
            return
        if self.current_preview.hard_errors:
            self.preview_text.setPlainText("\n".join(self.current_preview.hard_errors))
        else:
            self.preview_text.setPlainText("\n".join(self.current_preview.draft.preview_lines))
        self.status_label.setText(f"Previewed {self.current_preview.draft.kind} draft.")

    def stage_preview(self) -> None:
        if self.session is None or self.current_preview is None:
            return
        try:
            self.session.stage_draft(self.current_preview)
        except Exception as exc:
            QMessageBox.critical(self, "Stage failed", str(exc))
            return
        self._populate_lists()
        self.status_label.setText(self.session.state.status_text)

    def apply_current_preview(self) -> None:
        if self.session is None or self.current_preview is None:
            return
        try:
            draft = self.current_preview.draft
            self.session._apply_clone_draft(draft)
        except Exception as exc:
            QMessageBox.critical(self, "Apply failed", str(exc))
            return
        self.current_preview = None
        self._populate_lists()
        self.status_label.setText(self.session.state.status_text)

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
        self.status_label.setText(self.session.state.status_text)

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
        self.status_label.setText(self.session.state.status_text)

    def discard_selected_draft(self) -> None:
        if self.session is None or self.draft_list.currentRow() < 0:
            return
        draft_id = self.draft_list.currentItem().text().split()[0]
        self.session.discard_draft(draft_id)
        self._populate_lists()
        self.status_label.setText(self.session.state.status_text)

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
            new_name = new_name or f"{source_star.display_name or 'NewStar'}Clone"
            new_editor_id = new_editor_id or f"{source_star.editor_id or 'NewStar'}Clone"
            position = (
                float(self.position_x_input.text() or 0.0),
                float(self.position_y_input.text() or 0.0),
                float(self.position_z_input.text() or 0.0),
            )
            return self.session.preview_star_clone(
                source_star_form_id=form_id,
                new_editor_id=new_editor_id,
                new_display_name=new_name,
                system_id=system_id,
                position=position,
            )
        source_form_id = int(self.source_planet_combo.currentData())
        source_planet = next(item for item in self.session.view.source_planets if item.form_id == source_form_id)
        new_name = new_name or f"{source_planet.display_name or ('NewMoon' if mode == 'Moon' else 'NewPlanet')}Clone"
        new_editor_id = (
            new_editor_id or f"{source_planet.editor_id or ('NewMoon' if mode == 'Moon' else 'NewPlanet')}Clone"
        )
        if mode == "Planet":
            destination_star_form_id = int(self.destination_star_combo.currentData())
            return self.session.preview_planet_clone(
                source_planet_form_id=source_form_id,
                destination_star_form_id=destination_star_form_id,
                new_editor_id=new_editor_id,
                new_display_name=new_name,
                extract_biom=self.extract_biom_checkbox.isChecked(),
                orbit_override=orbit_override,
            )
        destination_parent_form_id = int(self.destination_parent_combo.currentData())
        return self.session.preview_moon_clone(
            source_moon_form_id=source_form_id,
            destination_parent_planet_form_id=destination_parent_form_id,
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
        if self.session is None:
            return
        row = self.planet_list.currentRow()
        if row < 0:
            return
        try:
            orbit = self.session.apply_preset(self.session.view.planets[row].form_id, preset_key)
        except Exception as exc:
            QMessageBox.critical(self, "Preset failed", str(exc))
            return
        self._load_orbit_fields(orbit)
        self.status_label.setText(self.session.state.status_text)

    def apply_orbit(self) -> None:
        if self.session is None:
            return
        row = self.planet_list.currentRow()
        if row < 0:
            return
        try:
            orbit = self._collect_orbit_override()
            if orbit is None:
                raise ValueError("Fill all orbit fields before applying.")
            self.session.set_planet_orbit(self.session.view.planets[row].form_id, orbit)
        except Exception as exc:
            QMessageBox.critical(self, "Orbit update failed", str(exc))
            return
        self._populate_lists()
        self.status_label.setText(self.session.state.status_text)
