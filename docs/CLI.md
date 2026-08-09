# StarForge CLI contract

StarForge exposes the same application operations intended for the desktop UI
through the `starforge` command and `python -m starforge`.

## Safety model

- Preview and inspection commands never write files.
- Apply commands write to a temporary file in the output directory, validate
  it, and atomically replace the requested output.
- The source plugin can never be overwritten.
- The destination plugin and existing outputs are preserved unless
  `--overwrite` is passed explicitly.
- Commands never prompt. `--non-interactive` is accepted to make that contract
  explicit in agent scripts.

## JSON contract

Place `--json` before the command to emit schema version 1 JSON. Successful
responses contain:

```json
{
  "schema_version": 1,
  "operation": "inspect",
  "success": true,
  "changed": false,
  "output_path": null,
  "warnings": [],
  "data": {}
}
```

Errors contain:

```json
{
  "schema_version": 1,
  "operation": "inspect",
  "success": false,
  "error": {
    "code": "input_not_found",
    "message": "Plugin does not exist: missing.esp"
  }
}
```

Paths are strings, form and system IDs are JSON integers, and ordered model
collections are arrays. New fields may be added within schema version 1;
existing fields will not change meaning.

## Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 2 | Invalid command arguments |
| 3 | Missing, unsafe, or invalid input/output |
| 4 | Domain validation failed |
| 5 | Operation cancelled |
| 10 | Unexpected internal error |

## Commands

Inspect or validate a plugin:

```powershell
starforge --json inspect .\MyMod.esp
starforge validate .\MyMod.esp
```

Create and inspect a reusable project pointer:

```powershell
starforge project create .\MyMod.starforge.json `
  --source .\Starfield.esm --destination .\MyMod.esp
starforge --json project show .\MyMod.starforge.json
```

Preview a clone without writing anything:

```powershell
starforge --json preview star `
  --source .\Starfield.esm --destination .\MyMod.esp `
  --source-form-id 0x1234 --editor-id MyNewStar `
  --display-name "My New Star" --system-id 0x1000
```

Apply the same operation to a new output:

```powershell
starforge apply star `
  --source .\Starfield.esm --destination .\MyMod.esp `
  --source-form-id 0x1234 --editor-id MyNewStar `
  --display-name "My New Star" --system-id 0x1000 `
  --output .\MyMod-StarForge.esp
```

`preview planet`, `preview moon`, `apply planet`, and `apply moon` use
`--destination-form-id` for the target star or parent planet. BIOM extraction
is opt-in with `--extract-biom`.

Apply an orbit preset or change a system ID:

```powershell
starforge orbit preset --source .\Starfield.esm --destination .\MyMod.esp `
  --planet-form-id 0x4567 --preset wide_stable `
  --output .\MyMod-Orbit.esp

starforge system-id --source .\Starfield.esm --destination .\MyMod.esp `
  --star-form-id 0x2222 --system-id 0x1001 `
  --output .\MyMod-System.esp
```

Arbitrary orbital fields can be reviewed with `preview orbit` and written with
`orbit set`. Supplying `--major-axis` or `--eccentricity` automatically
recalculates minor axis and aphelion unless those values are supplied explicitly.

```powershell
starforge --json preview orbit `
  --source .\Starfield.esm --destination .\MyMod.esp `
  --planet-form-id 0x4567 --major-axis 120000 --eccentricity 0.05

starforge orbit set `
  --source .\Starfield.esm --destination .\MyMod.esp `
  --planet-form-id 0x4567 --major-axis 120000 --eccentricity 0.05 `
  --output .\MyMod-Orbit.esp
```

Launch the polished desktop application explicitly with `starforge gui` or
`starforge-gui`. Windows release archives also provide `StarForge.exe` for the
windowed app and `starforge-cli.exe` for console and agent workflows.
