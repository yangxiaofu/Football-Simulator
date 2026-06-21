# PyInstaller spec for Football Simulator — Steam packaging spike (Milestone 5.12)
# Build: pyinstaller football_sim.spec
# Output: dist/FootballSimulator/FootballSimulator(.exe)
#
# Notes:
#   console=False  — suppress terminal in release builds (set True for debugging)
#   Saves live in dist/FootballSimulator/saves/ (dev) or %APPDATA%/FootballSimulator/saves/ (TBD)

block_cipher = None

a = Analysis(
    ['src/ui/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src/ui/static', 'src/ui/static'),
        ('src/db/schema.sql', 'src/db'),
    ],
    hiddenimports=['webview', 'sqlite3'],
    hookspath=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FootballSimulator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FootballSimulator',
)
