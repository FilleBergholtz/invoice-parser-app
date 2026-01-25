# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None

# We assume PyInstaller is run from the project root
# build_engine.py ensures cwd is project_root
project_root = Path(os.getcwd())

print(f"Spec file running from: {project_root}")
print(f"Target script: {project_root / 'run_gui.py'}")

a = Analysis(
    [str(project_root / 'run_gui.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PySide6',
        # Include backend dependencies too if we want a single-file distribution (though we use separate exe approach)
        # But wait, run_gui.py just runs the UI which spawns subprocess.
        # So we just need UI deps here.
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'notebook',
        'ipython',
        'tkinter',
        'matplotlib',
        'scipy',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InvoiceParserGUI',
    icon=str(project_root / 'src' / 'ui' / 'assets' / 'icons' / 'app.ico'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # GUI app - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
