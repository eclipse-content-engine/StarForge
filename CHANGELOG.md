# Changelog

All notable changes to StarForge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

## 0.3.0a2 - 2026-08-09

### Fixed

- Made combo-box popup text, hover, and selected states readable on Windows by
  explicitly applying the StarForge dark-theme palette.

## 0.3.0a1 - 2026-08-09

### Added

- Polished Project, Explore, Create, Orbits, and Review desktop workflows.
- Matching source-template constraints for star, planet, and moon creation.
- Background project loading and validated export with progress and cancellation.
- Persistent change review, dependency explanations, and saved window settings.
- Bounded undo/redo, transactional rollback, autosave, and guided crash recovery.
- Filesystem, render, malformed-input, interrupted-write, and accessibility tests.
- Windows installer and portable GUI/CLI bundle with SHA-256 checksums.
- Tag-driven release automation and optional Authenticode signing.
- Five-minute tutorial, troubleshooting, alpha-testing, release, and security docs.

### Changed

- Completed the private xEdit, Creation Kit, and in-game validation matrix.
- Defined and documented the supported-operation boundary and known limitations.

## 0.2.0 - 2026-08-08

### Added

- Typed, GUI-independent application service.
- Non-mutating clone previews and atomic validated output writes.
- CLI inspect, validate, project, clone, orbit, system-ID, and GUI commands.
- Stable JSON responses, documented exit codes, and cancellation support.

## 0.1.0 - 2026-08-08

### Added

- Self-contained plugin-format reader and writer primitives.
- Generated, redistributable plugin and BA2 test fixtures.
- Repository safety checks, development tooling, and continuous integration.
- Phase-based implementation and publication documentation.

### Changed

- Renamed the Python package from `starforge_v1` to `starforge`.
