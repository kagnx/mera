"""Sürüm yönetimi: otomatik artırma, derleme bilgisi ve Windows sürüm kaynağı.

- `bump_version()`  : derleme sırasında sürümü otomatik artırır (varsayılan: patch).
- `write_build_info()`: sürüm + derleme tarihini `build_data/version_info.json`
  olarak yazar; bu dosya exe içine paketlenir ve Hakkında diyaloğu çalışma
  zamanında okur (kaynak modda da aynı dosya kullanılır).
- `write_windows_version_info()`: PyInstaller `EXE(version=...)` için Windows
  dosya özellikleri (FileVersion, ProductName vb.) kaynağını üretir.

Komut satırı:
    python versioning.py          -> mevcut sürümü yazdırır
    python versioning.py bump     -> patch sürümünü artırır ve yazdırır
    python versioning.py bump minor -> minor sürümünü artırır
"""
import json
import os
import re
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DATA_DIR = os.path.join(PROJECT_ROOT, "build_data")
VERSION_JSON = os.path.join(BUILD_DATA_DIR, "version.json")          # {version}
BUILD_INFO_JSON = os.path.join(BUILD_DATA_DIR, "version_info.json")   # {version, build_date}

DEFAULT_VERSION = "1.0.0"

# PE sürüm kaynağına ve ISS yayıncı alanına gömülen metadata — TEK DOĞRULUK
# KAYNAĞI. write_windows_version_info() PE şablonunu, build_installer.py
# stamp_version() ise ISS MyAppPublisher satırını bu sabitlerden damgalar.
COMPANY_NAME = "kagnx"
PRODUCT_NAME = "MERABIS PRO"
FILE_DESCRIPTION = "MERABIS PRO - Turkiye Mera ve Otlatma Alanlari Bilgi Sistemi"
LEGAL_COPYRIGHT = "Copyright (c) 2026 kagnx - Her Hakki Saklidir  D :D :D"


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_version(version):
    """'1.2.3' -> (1, 2, 3); eksik parçaları 0'la tamamlar."""
    parts = []
    for p in str(version).split("."):
        if p.isdigit():
            parts.append(int(p))
        else:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def read_version():
    """Kaynak of truth: build_data/version.json'daki sürüm."""
    return _load_json(VERSION_JSON).get("version") or DEFAULT_VERSION


def bump_version(part="patch"):
    """Sürümü artırır ve build_data/version.json'a yazar.

    part: 'major' | 'minor' | 'patch' (varsayılan 'patch').
    Her derleme otomatik artırır (PyInstaller spec'i bunu çağırır).
    """
    major, minor, patch = parse_version(read_version())
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new_version = f"{major}.{minor}.{patch}"
    _save_json(VERSION_JSON, {"version": new_version})
    return new_version


def build_timestamp():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def write_build_info():
    """Derleme sırasında çağrılır: güncel sürüm + derleme tarihini yazar."""
    info = {"version": read_version(), "build_date": build_timestamp()}
    _save_json(BUILD_INFO_JSON, info)
    return info


def get_build_info():
    """Çalışma zamanı: paketli (frozen) veya kaynak dizinden derleme bilgisini okur."""
    if hasattr(sys, "_MEIPASS"):
        path = os.path.join(sys._MEIPASS, "build_data", "version_info.json")
    else:
        path = BUILD_INFO_JSON
    info = _load_json(path)
    if not info.get("version"):
        info["version"] = read_version()
    info.setdefault("build_date", None)
    return info


def write_windows_version_info(path, version):
    """PyInstaller EXE(version=...) için Windows sürüm kaynağı dosyasını üretir."""
    major, minor, patch, build = parse_version(version) + (0,)
    text = (
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        f"    filevers=({major}, {minor}, {patch}, {build}),\n"
        f"    prodvers=({major}, {minor}, {patch}, {build}),\n"
        "    mask=0x3f,\n"
        "    flags=0x0,\n"
        "    OS=0x40004,\n"
        "    fileType=0x1,\n"
        "    subtype=0x0,\n"
        "    date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable('040904b0', [\n"
        "        StringStruct('CompanyName', '" + COMPANY_NAME + "'),\n"
        "        StringStruct('FileDescription', '" + FILE_DESCRIPTION + "'),\n"
        f"        StringStruct('FileVersion', '{version}'),\n"
        "        StringStruct('ProductName', '" + PRODUCT_NAME + "'),\n"
        f"        StringStruct('ProductVersion', '{version}'),\n"
        "        StringStruct('LegalCopyright', '" + LEGAL_COPYRIGHT + "')\n"
        "      ])\n"
        "    ]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n"
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def get_legal_copyright():
    """LegalCopyright PE sürüm kaynağını okur.

    Katmanlar:
      1. Paketli mod (sys.frozen): Windows API (ctypes) ile çalıştıran exe'nin
         PE sürüm kaynağından LegalCopyright okunur.
      2. Kaynak mod: build_data/version_info.txt şablonu ayrıştırılır (derleme
         dışı ortamda PE yoktur; şablon aynı metni taşır).
      3. Her iki katman başarısızsa LEGAL_COPYRIGHT sabitine geri döner.

    Hata asla yükseltmez — boş/bilinmiyorsa boş string yerine sabit döner.
    """
    try:
        if getattr(sys, "frozen", False) and os.name == "nt":
            import ctypes
            import ctypes.wintypes

            size = ctypes.windll.version.GetFileVersionInfoSizeW(sys.executable, None)
            if size:
                data = ctypes.create_string_buffer(size)
                if ctypes.windll.version.GetFileVersionInfoW(sys.executable, 0, size, data):
                    val = ctypes.c_void_p()
                    val_len = ctypes.wintypes.UINT()
                    if ctypes.windll.version.VerQueryValueW(
                            data, "\\StringFileInfo\\040904b0\\LegalCopyright",
                            ctypes.byref(val), ctypes.byref(val_len)) and val_len.value:
                        text = ctypes.wstring_at(val, val_len.value)
                        if text.strip():
                            return text

        # Kaynak mod: şablon dosyasından ayrıştır
        template = os.path.join(BUILD_DATA_DIR, "version_info.txt")
        if os.path.isfile(template):
            m = re.search(
                r"StringStruct\('LegalCopyright',\s*'([^']*)'",
                open(template, encoding="utf-8").read())
            if m and m.group(1).strip():
                return m.group(1)
    except Exception:
        pass
    return LEGAL_COPYRIGHT


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "bump":
        part = args[1] if len(args) > 1 and args[1] in ("major", "minor", "patch") else "patch"
        print(bump_version(part))
    else:
        print(read_version())
