# Supported operations and limitations

This matrix defines the supported StarForge pre-alpha contract. Operations not
listed here are blocked or intentionally unavailable rather than treated as
best-effort binary edits.

## Operation matrix

| Operation | Desktop UI | CLI | Application API | Safety behavior |
| --- | --- | --- | --- | --- |
| Inspect and validate plugins | Yes | Yes | Yes | Read-only |
| Search destination hierarchy | Yes | Inspect output | Yes | Read-only |
| Allocate and change system IDs | Yes | Yes | Yes | Duplicate IDs blocked |
| Edit or preset orbital data | Yes | Yes | Yes | Invalid and overlapping orbits blocked |
| Preview star, planet, and moon clones | Yes | Yes | Yes | Non-mutating preview |
| Stage and review clone drafts | Yes | Preview/apply split | Yes | Export blocked while drafts remain staged |
| Export an edited plugin | Yes | Yes | Yes | Temporary write, validation, atomic publish |
| Undo and redo commands | Yes | No | Yes | Last 50 successful in-memory commands |
| Crash-recovery snapshot | Yes | No | Yes | Separate validated plugin in application data |

## Supported input and output boundary

- StarForge accepts `.esm` and `.esp` plugins that its TES4 reader can parse.
- Managed edits cover `STDT`, `PNDT`, and `LCTN` records required by the exposed
  workflows. Existing unmanaged groups and record bytes are preserved where the
  writer does not need to rebuild them.
- Outputs are always validated before atomic publication. The source master is
  never a legal output target. Existing outputs require an explicit overwrite.
- Biome extraction expects `Starfield - PlanetData.ba2` beside the source plugin.
  Missing archives fail plainly and the clone command is rolled back.

## Known limitations

- Arbitrary raw-record editing, plugin merging, conflict resolution, load-order
  management, and master cleaning are not supported.
- Undo history is in-memory and ends when the project closes. It does not reverse
  an output that has already been exported.
- Recovery snapshots preserve applied in-memory edits. Unapplied clone drafts are
  reported in recovery metadata but must be recreated after recovery.
- Recovery is best-effort protection against process interruption, not a source
  control or backup system.
- Paths within the platform-supported limit are Unicode-safe. Windows paths over
  the legacy `MAX_PATH` boundary require long-path support to be enabled in the
  operating system.
- Compatibility with xEdit, Creation Kit, and the game remains a required manual
  release gate because synthetic fixtures cannot establish runtime compatibility.

## Unsupported-operation policy

StarForge does not expose a generic binary mutation escape hatch. Unsupported
requests should be stopped with a plain-language explanation and leave source,
destination, and any pre-existing output unchanged.
