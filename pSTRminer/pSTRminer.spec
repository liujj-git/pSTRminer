# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for pSTRminer
# Build:  pyinstaller pSTRminer.spec
#
# Produces a single-directory bundle in dist/pSTRminer/
# Run:    dist/pSTRminer/pSTRminer          (GUI)
#         dist/pSTRminer/pSTRminer poly ...  (CLI)

import sys
from pathlib import Path

block_cipher = None

# ── collect the bundled scripts ───────────────────────────────
scripts_src = str(Path('scripts').resolve())

a = Analysis(
    ['__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # (source_path, destination_in_bundle)
        (scripts_src, 'scripts'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'pandas', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pSTRminer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,          # keep console for log output on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pSTRminer',
)
