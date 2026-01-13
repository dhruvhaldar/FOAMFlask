# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Include the entire static directory
# 'static' source folder -> 'static' destination folder in _MEIPASS
datas = [
    ('static', 'static'),
    ('backend', 'backend'),
    ('case_config.json', '.') # Include config if exists (or create empty?)
    # Note: case_config.json should be external to the exe usually, but if we want it to
    # work out of the box we might include a default one.
    # However, app.py expects to write to it. Writing to _MEIPASS is temporary.
    # Better to NOT include it, and let app.py create it in CWD.
    # But app.py checks for existence.
]

# Exclude case_config.json from bundle so it uses CWD version
datas = [('static', 'static'), ('backend', 'backend')]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'engineio.async_drivers.threading',
        'vtk',
        'vtkmodules',
        'vtkmodules.all',
        'pyvista',
        'trame',
        'trame.app',
        'trame.ui.vuetify',
        'trame.widgets.vtk',
        'trame.widgets.vuetify',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='FOAMFlask',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # Keep console for logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico'
)
