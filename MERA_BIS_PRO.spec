# -*- mode: python ; coding: utf-8 -*-

# ---- Sürüm yönetimi: her derlemede otomatik artırma + derleme bilgisi ----
# Spec, PyInstaller'ın çalıştığı dizinde değilse proje köküne eklenir.
# Not: spec içinde '__file__' tanımlı değildir; PyInstaller 'SPECPATH' globalini verir.
import os
import sys

sys.path.insert(0, SPECPATH)

import versioning

# 1) Sürümü otomatik artır (patch) — her derleme yeni sürüm üretir.
#    İsterseniz: versioning.bump_version('minor') veya ('major')
versioning.bump_version("patch")

# 2) Derleme bilgisini (sürüm + tarih) exe içine paketlenecek JSON'a yaz.
build_info = versioning.write_build_info()
VERSION_STR = build_info["version"]

# 3) Windows dosya özellikleri (FileVersion/ProductName) kaynağını üret.
VERSION_RESOURCE = versioning.write_windows_version_info(
    os.path.join(versioning.BUILD_DATA_DIR, "version_info.txt"), VERSION_STR
)

print(f"[build] Sürüm: {VERSION_STR} | Derleme: {build_info['build_date']}")


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('build_data', 'build_data')],
    hiddenimports=[
        'matplotlib.backends.backend_qtagg',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MERA_BIS_PRO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app_icon.ico'],
    version=VERSION_RESOURCE,
)
