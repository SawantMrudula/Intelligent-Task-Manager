# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None
flet_datas, flet_binaries, flet_hiddenimports = collect_all('flet')
a = Analysis(
    ['integrated.py'],  # Your main entry point
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),  # Include assets folder
        *flet_datas,
    ],
    hiddenimports=[
        'flet',
        'flet_webview',
        'plotly',
        'plotly.graph_objects',
        'pandas',
        'psutil',
        'pycaw',
        'pycaw.pycaw',
        'comtypes',
        'ctypes',
        're',
        'subprocess',
        'threading',
        'time',
        'datetime',
        'os',
        'sys',
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

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DeviceManagerApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to False for no console window
    icon='assets/logo.png',  # Use an icon if available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DeviceManagerApp',
)