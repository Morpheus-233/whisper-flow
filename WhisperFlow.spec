# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, collect_dynamic_libs

block_cipher = None

datas = [
    ('data', 'data'),
    ('studio', 'studio'),
    ('ui', 'ui'),
]

binaries = []
hiddenimports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'faster_whisper',
    'ctranslate2',
    'sounddevice',
    '_sounddevice_data',
    'numpy',
    'scipy',
    'scipy.io',
    'scipy.io.wavfile',
    'uiautomation',
    'comtypes',
    'comtypes.stream',
    'comtypes.client',
    'pyautogui',
    'pygetwindow',
    'pyperclip',
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._win32',
    'pynput.mouse',
    'pynput.mouse._win32',
    'config',
    'audio_engine',
    'whisper_engine',
    'paster',
    'text_cleaner',
    'focus_detector',
    'voice_profile',
    'style_engine',
    'calibration_engine',
    'studio_server',
]

# Collect packages with dynamic native DLLs or generated assets
for pkg in ['ctranslate2', 'faster_whisper', 'sounddevice', 'pynput', 'uiautomation', 'comtypes', 'pyautogui']:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hidden)
    except Exception as e:
        print(f"Notice collecting {pkg}: {e}")

# Optional NVIDIA CUDA libraries: if nvidia packages are installed in build venv, bundle their bin DLLs
for env_path in [sys.prefix] + getattr(sys, 'path', []):
    site_packages = os.path.join(env_path, 'Lib', 'site-packages')
    nvidia_dir = os.path.join(site_packages, 'nvidia')
    if os.path.exists(nvidia_dir):
        for root, dirs, files in os.walk(nvidia_dir):
            if 'bin' in dirs or root.endswith('bin'):
                b_dir = os.path.join(root, 'bin') if 'bin' in dirs else root
                for f in os.listdir(b_dir):
                    if f.lower().endswith('.dll'):
                        binaries.append((os.path.join(b_dir, f), 'nvidia/bin'))
        break

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'notebook', 'IPython', 'PIL'],
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
    name='WhisperFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='WhisperFlow',
)
