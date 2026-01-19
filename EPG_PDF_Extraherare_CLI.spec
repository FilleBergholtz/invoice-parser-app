# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for CLI version

block_cipher = None

a = Analysis(
    ['src/cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pdfplumber',
        'pandas',
        'openpyxl',
        # 'streamlit',  # CLI behöver inte Streamlit
        # 'fastapi',  # CLI behöver inte FastAPI
        # 'uvicorn',  # CLI behöver inte Uvicorn
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
        'test_fixes',
        'test_unit_fix',
        'analyze_unit_problems',
        'analyze_quantity_patterns',
        'analyze_remaining_problems',
        'pytest',
        'unittest',
        'tests',
        # Exkludera onödiga moduler för att minska storlek
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pandas.tests',
        'numpy.tests',
        'pandas.testing',
        'numpy.testing',
        'pandas._testing',
        'pandas.plotting',
        'pandas.io.formats.style',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'pydoc',
        'doctest',
        'distutils',
        'setuptools',
        'wheel',
        'email',
        'http.server',
        'xmlrpc',
        'sqlite3',
        'dbm',
        # CLI behöver inte Streamlit
        'streamlit',
        'streamlit.web',
        'streamlit.runtime',
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
    name='EPG_PDF_Extraherare',
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
