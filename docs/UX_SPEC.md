# StarForge UX specification

## Product promise

StarForge helps a mod author make deliberate, reviewable Starfield plugin edits
without requiring them to understand record internals. Technical identifiers
remain available, but the default experience speaks in stars, planets, moons,
orbits, changes, and outputs.

## Experience principles

1. **Orient before editing.** Always show which source and destination are open.
2. **One decision per surface.** Reveal only the controls needed for the current
   task and keep advanced numeric values secondary.
3. **Preview is a promise.** A preview never changes a file and states exactly
   what applying it will do.
4. **Inputs are precious.** Source and destination files are visually identified
   as protected; exporting creates a new output by default.
5. **Plain language first.** Names and consequences lead. Form IDs, system IDs,
   and raw values are supporting details.
6. **No silent work.** Loading, validation, cancellation, warnings, and errors
   have visible states with an actionable next step.

## Information architecture

The desktop shell contains five stable destinations:

1. **Project** — open source and destination plugins, view recent projects, and
   run preflight checks.
2. **Explore** — browse the destination hierarchy and inspect one selected
   object.
3. **Create** — clone a star, planet, or moon through a guided form and preview.
4. **Orbits** — select a body, apply a preset or edit advanced orbital values,
   and validate before staging.
5. **Review** — inspect the change set, resolve warnings, and export safely.

The sidebar communicates location. The top bar communicates the active project.
The bottom change tray communicates pending work and provides the single route
to final review.

## Primary workflows

### Open a project

1. Choose a source master.
2. Choose a destination plugin.
3. StarForge checks readability, supported extensions, and whether the paths
   differ.
4. On success, enter Explore with the destination hierarchy selected.
5. On failure, remain on Project and show a plain-language recovery action.

### Clone a body

1. Choose Star, Planet, or Moon.
2. Choose the source template. Planet creation lists only planet templates;
   moon creation lists only moon templates.
3. Choose the destination parent when required.
4. Enter the display name and optional technical editor ID.
5. Review the generated preview, warnings, allocated IDs, and planned files.
6. Stage the change or return to edit the inputs.

### Edit an orbit

1. Select a destination planet or moon.
2. Choose a descriptive preset or open advanced values.
3. StarForge recalculates dependent values and validates sibling overlap.
4. Review the before/after summary.
5. Stage the orbital change.

### Review and export

1. Review changes grouped by created bodies, system IDs, and orbits.
2. Expand technical details only when needed.
3. Resolve blocking errors and acknowledge warnings.
4. Choose a new output path.
5. Write to a temporary file, validate it, and atomically publish the output.

## Screen and component states

### Empty

Explain what the user needs and offer one primary action. Never show disabled
editor grids as the main content.

### Loading

Keep the current context visible, disable conflicting actions, show the named
operation and determinate progress when available, and always expose Cancel for
long operations.

### Warning

Use amber styling, describe the consequence, and provide the safe default
action. Warnings do not impersonate errors.

### Error

State what failed, whether files were changed, and the next recovery action.
Tracebacks belong in expandable technical details, not the primary message.

### Success

Confirm the outcome and output path without blocking the next action.

## Keyboard and accessibility

- Logical tab order follows navigation, page heading, content, then actions.
- `Ctrl+1` through `Ctrl+5` switch primary sections.
- `Ctrl+O` opens a project and `Ctrl+Shift+S` begins export.
- Every field has a visible label; placeholder text is never the only label.
- Focus uses a high-contrast accent outline.
- Status is communicated with text and shape as well as color.
- The default palette targets WCAG AA contrast and remains legible at 200% DPI.

## Phase 3 prototype boundary

The prototype proves navigation, hierarchy, guided forms, preview/review
structure, reusable components, and common states. Phase 4 connects every page
to the typed application service, moves work off the UI thread, and completes
production persistence and export behavior.
