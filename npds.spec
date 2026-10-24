# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

# Collect dynamic libraries from onnxruntime
onnx_binaries = collect_dynamic_libs('onnxruntime')
all_binaries = onnx_binaries

# Collect data files
easyocr_datas = collect_data_files('easyocr')
qfluentwidgets_datas = collect_data_files('qfluentwidgets')

# Application data files
app_datas = [
    ('models', 'models'),
    ('assets', 'assets'),
    ('npds_data.db', '.'),
] + easyocr_datas + qfluentwidgets_datas

# Explicit hidden imports for reliable runtime discovery
hidden_imports = list(set([
    'onnxruntime',
    'onnxruntime.capi._pybind_state',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.lib.format',
    'qfluentwidgets',
    'torch',
    'torchvision',
    'easyocr',
    'PIL',
    'cv2',
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
] + collect_submodules('qfluentwidgets')))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=all_binaries,
    datas=app_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib.tests', 'tkinter'],
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
    name='NumberPlateDetectionSystem',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NumberPlateDetectionSystem',
)
