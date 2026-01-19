# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for GUI version (Streamlit)

block_cipher = None

a = Analysis(
    ['run_streamlit.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pdfplumber',
        'pandas',
        'openpyxl',
        'streamlit',
        'fastapi',
        'uvicorn',
        'pydantic',
        'PIL',
        'numpy',
        'chardet',
        'cryptography',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exkludera testfiler och analysfiler
        'test_fixes',
        'test_unit_fix',
        'analyze_unit_problems',
        'analyze_quantity_patterns',
        'analyze_remaining_problems',
        'pytest',
        'unittest',
        'tests',
        # Exkludera onödiga moduler för att minska storlek
        'matplotlib',  # Används inte
        'scipy',  # Används inte
        'IPython',  # Används inte
        'jupyter',  # Används inte
        'notebook',  # Används inte
        'pandas.tests',  # Testfiler
        'numpy.tests',  # Testfiler
        'pandas.testing',  # Testverktyg
        'numpy.testing',  # Testverktyg
        'pandas._testing',  # Interna testverktyg
        'pandas.plotting',  # Plotting (används inte)
        'pandas.io.formats.style',  # Styling (används inte)
        'tkinter',  # GUI (används inte, vi använder Streamlit)
        'PyQt5',  # GUI (används inte)
        'PyQt6',  # GUI (används inte)
        'PySide2',  # GUI (används inte)
        'PySide6',  # GUI (används inte)
        'pydoc',  # Dokumentation (används inte)
        'doctest',  # Testverktyg
        'distutils',  # Deprecated
        'setuptools',  # Build tools (behövs inte i runtime)
        'wheel',  # Build tools
        'email',  # Email (används inte)
        'http.server',  # HTTP server (används inte, vi använder uvicorn)
        'xmlrpc',  # XML-RPC (används inte)
        'sqlite3',  # SQLite (används inte)
        'dbm',  # Database (används inte)
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
    name='EPG_PDF_Extraherare_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
