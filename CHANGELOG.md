# Changelog

## Unreleased

- Added the Phase 3 Project, Explore, Create, Orbits, and Review prototype.
- Added reusable navigation, surface, notice, empty-state, header, and inspector
  components with a centralized dark workshop theme.
- Added the UX specification, design-system reference, keyboard navigation,
  progressive disclosure, hierarchy search, and representative design-preview
  mode.
- Constrained planet and moon creation to source templates of the matching body
  type, including a clear empty-template state.
- Added the Phase 4 stateful application workspace used by the desktop client.
- Added background project loading and validated export with progress,
  cancellation, and actionable recovery messages.
- Added live object identifiers, dependency explanations, applied-change
  summaries, persistent window geometry, and remembered project directories.
- Added workspace, background-task, safe-export, and WCAG AA contrast tests.
- Added Phase 5 bounded undo/redo and transactional rollback for desktop edits.
- Added atomic crash-recovery plugins with non-executable JSON metadata and a
  guided recovery offer in the desktop UI.
- Added Unicode, deep-path, read-only input, malformed plugin, missing archive,
  interrupted publish, recovery, and UI render hardening tests.
- Documented the supported-operation boundary, known limitations, and external
  xEdit/Creation Kit/in-game validation matrix.

## 0.2.0 - 2026-08-08

- Added a typed, GUI-independent application service.
- Added non-mutating clone previews and atomic validated output writes.
- Added the `starforge` CLI with inspect, validate, project, clone, orbit,
  system-ID, and GUI commands.
- Added stable JSON responses, documented exit codes, cancellation support, and
  CLI/application contract tests.

All notable changes to StarForge will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases will use semantic versioning once the public alpha begins.

## [Unreleased]

### Added

- Self-contained plugin-format reader and writer primitives.
- Generated, redistributable plugin and BA2 test fixtures.
- Repository safety checks, development tooling, and continuous integration.
- Phase-based implementation and publication documentation.

### Changed

- Renamed the Python package from `starforge_v1` to `starforge`.
