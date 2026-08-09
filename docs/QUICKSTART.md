# StarForge five-minute quick start

StarForge is a Windows desktop tool for guided Starfield star-system editing. It
also includes a scriptable CLI for coding agents and advanced users.

## 1. Install or unpack

- Installer: run `StarForge-0.3.0-alpha.1-Windows-Setup.exe`.
- Portable: unpack the entire `StarForge-0.3.0-alpha.1-Windows-Portable.zip`
  archive, then run `StarForge.exe` from the extracted folder.

Compare the downloaded file against `SHA256SUMS.txt`. Alpha artifacts may be
unsigned; the release includes `SIGNING_STATUS.txt` whenever no certificate was
available during the build.

## 2. Open a project

Select the source plugin you want to copy from and the destination plugin you
want to extend. StarForge treats both inputs as protected and writes changes to
a separate output plugin.

## 3. Explore and create

Use **Explore** to search the loaded hierarchy. In **Create**, choose a star,
planet, or moon and then select a matching source template. Planet creation only
offers planets; moon creation only offers moons. Review any dependency or
archive notices before staging the change.

## 4. Review and export

Open **Review** to inspect every staged operation. Choose an output location,
run validation, and export. If a write is interrupted, StarForge keeps the input
files untouched and can offer a protected recovery snapshot on the next launch.

## CLI equivalent

Open PowerShell in the portable folder and start with:

```powershell
.\starforge-cli.exe --help
.\starforge-cli.exe inspect --plugin "C:\path\Source.esm" --json
```

See [CLI.md](CLI.md) for every command and exit code.
