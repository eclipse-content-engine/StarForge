# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


root = Path(SPECPATH).parent
source_path = str(root / "src")
gui_analysis = Analysis(
    [str(root / "packaging" / "starforge_gui.py")],
    pathex=[source_path],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
cli_analysis = Analysis(
    [str(root / "packaging" / "starforge_cli.py")],
    pathex=[source_path],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

MERGE(
    (gui_analysis, "starforge_gui", "StarForge"),
    (cli_analysis, "starforge_cli", "starforge-cli"),
)

gui_pyz = PYZ(gui_analysis.pure)
gui_exe = EXE(
    gui_pyz,
    gui_analysis.dependencies,
    gui_analysis.scripts,
    [],
    exclude_binaries=True,
    name="StarForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

cli_pyz = PYZ(cli_analysis.pure)
cli_exe = EXE(
    cli_pyz,
    cli_analysis.dependencies,
    cli_analysis.scripts,
    [],
    exclude_binaries=True,
    name="starforge-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)

bundle = COLLECT(
    gui_exe,
    cli_exe,
    gui_analysis.binaries,
    gui_analysis.datas,
    cli_analysis.binaries,
    cli_analysis.datas,
    strip=False,
    upx=True,
    name="StarForge",
)
