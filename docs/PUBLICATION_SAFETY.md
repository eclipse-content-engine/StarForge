# Publication safety and fixture policy

## Current private data

The local `Test ESM/` directory contains Bethesda game data and project-specific
plugins used during development. At the start of Phase 1 it includes, among
other files:

- `Starfield.esm` (approximately 1.39 GB)
- `Starfield - PlanetData.ba2` (approximately 21 MB)
- local Pytheas ESM/ESP fixtures
- extracted BIOM assets

These files must not be committed, uploaded as release artifacts, copied into
generated fixtures, or included in bug-report bundles. `.gitignore` excludes the
directory and all BA2 archives as a defensive measure.

## Testing policy

Tests are divided into two classes:

1. Public unit and integration tests use compact fixtures generated entirely by
   this project. They run in CI and from a fresh clone.
2. Private compatibility tests use locally installed game data. They are opt-in,
   skipped when the required environment configuration is absent, and never run
   in public CI.

Generated public fixtures must contain invented editor IDs, names, FormIDs, and
payload values. They may model the binary structure needed by StarForge but must
not copy record payloads or assets from the game.

## Dependency boundary

StarForge contains a deliberately narrow `starforge.formats` package with the
TES4 header, managed-group, record, subrecord, and compression primitives it
uses. It does not modify `sys.path` or import a sibling workspace project.

## Pre-publication audit

Before the first push containing project history:

- inspect `git status --ignored` for protected files;
- inspect tracked files for ESM, ESP, ESL, BA2, BIOM, archive, output, and cache
  artifacts;
- scan text for credentials, absolute developer paths, and personal data;
- verify the selected license covers every distributed source dependency;
- build release artifacts from a clean checkout and inspect their contents.
