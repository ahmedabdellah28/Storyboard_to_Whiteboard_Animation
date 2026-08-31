# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Kivy and KivyMD hook paths
try:
    from kivymd import hooks_path as kivymd_hooks_path
    kivymd_hooks = kivymd_hooks_path()
except Exception:
    kivymd_hooks = []

try:
    from kivy.tools.packaging.pyinstaller_hooks import hookspath as kivy_hookspath
    kivy_hooks = kivy_hookspath()
except Exception:
    kivy_hooks = []

# Collect KivyMD asset files (fonts, icons, themes)
kivymd_datas = []
try:
    kivymd_datas = collect_data_files('kivymd')
except Exception:
    pass

datas = [
    ('data', 'data'),
    ('engine', 'engine'),
    ('ui', 'ui'),
    ('licensing', 'licensing'),
    ('main_layout.kv', '.'),
]
if os.path.exists('screens'):
    datas.append(('screens', 'screens'))
datas.extend(kivymd_datas)

# Exclude unnecessary heavy packages to keep the EXE lightweight
excludes = [
    'tkinter',
    'unittest',
    'pydoc',
    'email',
    'http',
    'xmlrpc',
    'test',
    'distutils',
    'setuptools',
    'matplotlib',
    'scipy',
    'pandas',
    'IPython',
    'notebook',
    'lib2to3',
]

hiddenimports = [
    'kivymd.uix.gridlayout',
    'kivymd.uix.textfield',
    'kivymd.uix.button',
    'kivymd.uix.dialog',
    'kivymd.uix.card',
    'kivymd.uix.label',
    'kivymd.uix.boxlayout',
    'kivymd.uix.selectioncontrol',
    'kivymd.uix.slider',
    'kivymd.toast',
    'plyer.platforms',
    'plyer.platforms.win',
    'plyer.platforms.win.filechooser',
    'ffpyplayer',
    'av',
    'licensing',
    'licensing.fingerprint',
    'licensing.crypto',
    'licensing.local_cache',
    'licensing.license_guard',
    'licensing.activation_dialog',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[*([kivymd_hooks] if isinstance(kivymd_hooks, str) else kivymd_hooks), *kivy_hooks],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Img2Sketch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='data/images/favicon.ico' if os.path.exists('data/images/favicon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Img2Sketch'
)