#!/usr/bin/env python3
"""
MERA-BİS PRO — Mevcut derlemeden offline güncelleme paketi üretir.

Kullanım:
    python tools/make_update_package.py --notes "Hata düzeltmeleri ve güncelleme servisi"

updates/ klasörüne şunları yazar:
    MERA_BIS_PRO_<sürüm>.zip   (exe içerir)
    manifest.json              (sürüm, tarih, SHA-256, boyut, notlar)

Kullanıcı, updates/ klasörünü ağ paylaşımına veya USB belleğe kopyalayıp
uygulamada "Araçlar → Güncellemeleri Denetle" ile kaynağı göstererek
güncelleme yapabilir.
"""
import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import versioning  # noqa: E402


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 512), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Offline güncelleme paketi üretici")
    ap.add_argument("--exe", default=os.path.join(PROJECT_ROOT, "dist", "MERA_BIS_PRO.exe"),
                    help="Kaynak exe (varsayılan: dist/MERA_BIS_PRO.exe)")
    ap.add_argument("--notes", default="", help="Sürüm notları")
    args = ap.parse_args()

    if not os.path.isfile(args.exe):
        print(f"Hata: exe bulunamadı: {args.exe}")
        print("Önce derleyin:  python -m PyInstaller MERA_BIS_PRO.spec --noconfirm")
        return 1

    version = versioning.read_version()
    updates_dir = os.path.join(PROJECT_ROOT, "updates")
    os.makedirs(updates_dir, exist_ok=True)
    zip_name = f"MERA_BIS_PRO_{version}.zip"
    zip_path = os.path.join(updates_dir, zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(args.exe, "MERA_BIS_PRO.exe")

    manifest = {
        "version": version,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "file": zip_name,
        "sha256": sha256_of(zip_path),
        "size": os.path.getsize(zip_path),
        "notes": args.notes or f"MERA-BİS PRO v{version} sürümü.",
    }
    mpath = os.path.join(updates_dir, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Paket   : {zip_path}")
    print(f"Manifest: {mpath}")
    print(f"Sürüm   : {version}  |  Boyut: {manifest['size']:,} B")
    print(f"SHA-256 : {manifest['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
