# StarForge implementation phases

## Product objective

Ship StarForge as a polished Windows desktop application for mod authors while
retaining a stable, automation-friendly CLI for coding agents and advanced
users.

The existing PySide6 UI is a disposable functional prototype. The verified
domain behavior should be preserved, while the presentation layer and its
information architecture are replaced.

## Architectural target

StarForge will expose one deterministic engine through two first-class clients:

1. `starforge.core` owns parsing, validation, mutation, and serialization.
2. `starforge.application` owns user-facing operations, typed results, progress,
   and structured errors.
3. `starforge.cli` exposes application operations as human-readable and JSON
   commands.
4. `starforge.ui` exposes the same operations through a guided PySide6 desktop
   application.

The UI must not shell out to the CLI. Neither interface may implement domain
rules independently.

## Phase 1: repository and safety foundation

**Goal:** create a clean, legally publishable, reproducible base before product
development begins.

**Current status:** complete as of 2026-08-08. The public repository is live,
and the full CI matrix passes on Windows and Linux with Python 3.11, 3.12, and
3.13.

### Work

- [x] Document the implementation phases and release gates.
- [x] Add repository ignores for Python outputs, build products, generated
  reports, Bethesda plugins, and BA2 archives.
- [x] Document the proprietary-data boundary and fixture replacement plan.
- [x] Align stale writer tests with the current TES4/group contract.
- [x] Establish the GitHub repository as the canonical source and connect the
  local checkout without publishing unfinished work.
- [x] Select and add the MIT source license.
- [x] Replace `starforge_v1` with the final `starforge` package name.
- [x] Remove workspace-relative `sys.path` injection.
- [x] Extract the required binary reader/writer primitives into `starforge.formats`.
- [x] Replace private game-file tests with generated redistributable fixtures.
- [x] Add linting, formatting, typing, and clean-environment test configuration.
- [x] Make all local public tests pass without private files.
- [x] Confirm the same suite from the first clean GitHub checkout and CI run.

### Exit criteria

- A fresh clone can install in an isolated environment.
- Unit tests do not require Bethesda-owned content.
- Optional private integration tests are clearly separated and ignored by Git.
- No code depends on the developer's workspace layout.
- The repository contains a chosen license and contribution policy.
- CI passes on the supported Python and Windows versions.

## Phase 2: shared application layer and CLI

**Goal:** make every supported edit available through a stable headless API and
CLI before attaching the replacement UI.

**Current status:** complete as of 2026-08-08. The typed application layer and
CLI share the existing domain engine, previews are non-mutating, and writes are
validated and atomically replaced.

### Work

- [x] Decompose `StarForgeSession` into explicit application operations.
- [x] Define typed request, preview, result, warning, and error models.
- [x] Add progress and cancellation support for long plugin operations.
- [x] Implement CLI commands for inspect, project creation, clone, orbit editing,
  validation, preview, apply, and GUI launch.
- [x] Support stable JSON output, documented exit codes, and non-interactive mode.
- [x] Write outputs through temporary files followed by atomic replacement.
- [x] Add application, CLI contract, and failure-path tests.

### Exit criteria

- GUI-independent workflows cover the current feature set.
- Preview operations cannot mutate input or destination files.
- CLI JSON output is documented and tested.
- Input plugins are never overwritten by default.

## Phase 3: UX specification and design system

**Goal:** approve the new interaction model and visual language before wiring
every backend feature into widgets.

**Current status:** complete as of 2026-08-08. The UX specification, design
tokens, reusable components, and navigable PySide6 prototype received visual
approval. Qt 6 scaling, keyboard navigation, visible focus states, and automated
WCAG AA contrast checks complete the validation gate.

### Work

- [x] Design the project-opening, clone, orbit, review, and export workflows.
- [x] Create wireframes for welcome, workspace, inspector, change tray, empty,
  loading, warning, and error states.
- [x] Define typography, color, spacing, elevation, iconography, and component states.
- [x] Build reusable PySide6 navigation, surface, field, notice, inspector, and
  command components.
- [x] Validate high-DPI behavior, keyboard navigation, focus visibility, and color
  contrast.
- [x] Receive design approval before Phase 4 feature integration.

### Exit criteria

- The full workflow is navigable as a visual prototype.
- Shared components cover the common states without one-off styling.
- The design is approved before full feature integration.

## Phase 4: desktop MVP

**Goal:** replace the prototype window with a polished, guided application.

**Current status:** implementation complete as of 2026-08-08 and ready for
review. The desktop client now uses the shared application layer, keeps plugin
parsing and export off the UI thread, and preserves the Phase 2 write-safety
contract.

### Work

- [x] Build project setup and preflight validation.
- [x] Build a searchable star-system hierarchy.
- [x] Implement guided star, planet, and moon cloning.
- [x] Implement a friendly orbit editor with presets and advanced numeric controls.
- [x] Implement system-ID allocation and dependency explanations.
- [x] Add the persistent change tray, human summary, technical details, and export.
- [x] Move parsing and writing off the UI thread and expose progress/cancellation.
- [x] Persist window state and non-sensitive user preferences.

### Exit criteria

- All MVP operations have GUI/CLI parity.
- Normal plugin operations do not freeze the UI.
- Errors are actionable and never require reading a traceback.
- Every write is preceded by a reviewable change set.

## Phase 5: hardening and validation

**Goal:** prove that StarForge is safe and dependable on real projects.

### Work

- Add undo/redo or command-level rollback.
- Add crash recovery and project autosave.
- Add UI smoke tests and selected visual snapshots.
- Test clean installation, upgrades, Unicode paths, long paths, read-only inputs,
  missing archives, interrupted writes, and malformed plugins.
- Validate representative outputs with xEdit, Creation Kit, and in-game checks.
- Document the supported-operation matrix and known limitations.

### Exit criteria

- Automated tests and the manual validation matrix pass.
- Failed or interrupted writes cannot corrupt the user's source.
- Unsupported edits are blocked with plain-language explanations.

## Phase 6: public release

**Goal:** distribute a trustworthy alpha and establish a sustainable release
process.

### Work

- Add GitHub Actions for linting, tests, packaging, and release artifacts.
- Produce a Windows installer and portable archive.
- Sign binaries when a code-signing certificate is available.
- Publish screenshots, a five-minute tutorial, CLI reference, troubleshooting,
  changelog, and security reporting instructions.
- Run a limited external alpha before declaring the release stable.

### Exit criteria

- StarForge installs and launches on a clean supported Windows system.
- Release artifacts are generated from a tagged commit.
- Documentation covers both guided UI and agent-driven CLI workflows.
- No proprietary fixtures or credentials exist anywhere in Git history.

## MVP scope

Version 0.1 includes plugin opening, hierarchy browsing, star/planet/moon cloning,
system-ID management, orbital editing, preview, validation, staging, safe export,
CLI parity, and Windows packaging.

AI chat, graphical orbit manipulation, arbitrary raw-record editing, plugin
merging, asset generation, and mod-platform publishing are deferred until after
the deterministic tool is stable.
