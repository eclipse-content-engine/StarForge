# StarForge

StarForge is a desktop and command-line toolkit for safely creating and editing
Starfield star systems, planets, moons, and orbital data.

The project is currently in pre-alpha development. Its existing PySide6 window
is a functional prototype; a new guided desktop experience is planned in
[`docs/IMPLEMENTATION_PHASES.md`](docs/IMPLEMENTATION_PHASES.md).

## Current capabilities

- inspect source and destination plugins
- clone stars, planets, and moons
- allocate and update system IDs
- edit orbital data and apply presets
- preview and stage changes before writing an output plugin
- preserve unsupported record data where possible

## Development status

Phase 1 is in progress. Packaging, dependency isolation, redistributable test
fixtures, and clean-machine reproducibility must be completed before a public
release.

The public test suite builds compact synthetic plugins and archives at runtime.
Optional private compatibility tests remain excluded from version control. See
[`docs/PUBLICATION_SAFETY.md`](docs/PUBLICATION_SAFETY.md).

## Local development

StarForge requires Python 3.11 or newer and contains its required plugin-format
primitives in the `starforge.formats` package.

```powershell
python -m pip install -e .
python -m pytest
python -m starforge
```

### Windows path length

PySide6 contains deeply nested QML files. On Windows systems without long-path
support, creating a development environment under a deeply nested directory can
fail during installation. Use a short path such as `C:\dev\StarForge` or enable
Windows long-path support. Packaged StarForge releases will use controlled,
short installation paths.

## License

StarForge is available under the [MIT License](LICENSE).
