#!/usr/bin/env python3
"""
MERA-BİS PRO — Derleme çıktı temizliği ve sürüm arşivleme.

Sorun: PyInstaller + Inno Setup her derlemede dist/, updates/ ve
installer/Output/ içinde yüzlerce MB yeni çıktı bırakır; eski sürümler
birikerek birkaç GB yer kaplar.

Strateji:
  1. Sürümler dosya adlarından ve/veya exe VersionInfo'dan tespit edilir.
  2. "Güncel sürüm" dışındaki her sürüm, SHA-256 kaydıyla birlikte
     archive/v<sürüm>/ altına taşınır (dist/release'dan exe'ler,
     updates/ + installer/Output/ zaten yalnızca birer sürüm içerir).
  3. build/ klasörü tamamen silinebilir — yalnızca PyInstaller ara
     dosyalarıdır (obj/toc/collect), exe'ye dönüştürülemez, hep yeniden
     üretilir.
  4. dist/MERA_BIS_PRO.exe (damgasız ana exe) arşivlenmez; bir sonraki
     derlemede üzerine yazılır.

Kullanım:
    python tools/clean_dist.py                  # plan (dry-run)
    python tools/clean_dist.py --apply          # planı uygula
    python tools/clean_dist.py --keep 1.2.1     # yürürlükten çıkacak sürümü koru
    python tools/clean_dist.py --current 1.2.4  # güncel sürümü elle sabitle
    python tools/clean_dist.py --apply --clean-build          # build/ sil
    python tools/clean_dist.py --apply --clean-build --purge-archive 1.2.1
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_DIR = os.path.join(PROJECT_ROOT, "archive")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
RELEASE_DIR = os.path.join(DIST_DIR, "release")
UPDATES_DIR = os.path.join(PROJECT_ROOT, "updates")
INSTALLER_DIR = os.path.join(PROJECT_ROOT, "installer", "Output")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")

# GitHub Release staging klasörleri (gh_release_v<sürüm>): yayın varlıklarının
# doğrulanmış kopyalarıdır; asla arşivlenmez/silinmez. Temizlik aracı bunları
# yalnızca RAPORLAR (koruma kaydı), dokunmaz.
STAGING_PREFIX = "gh_release_"

VERSION_PATTERNS = [
    # MERA_BIS_PRO_v1.2.4.exe / MERA_BIS_PRO_1.2.4.zip / Setup_v1.2.4.exe
    re.compile(r"_v?(\d+\.\d+\.\d+)(?:\.\w+)?$"),
]

FAIL = 0


def _p(msg):
    print(f"[clean] {msg}")


def sha256_of(path, chunk=1024 * 512):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for piece in iter(lambda: f.read(chunk), b""):
            h.update(piece)
    return h.hexdigest()


def version_of(path):
    """Sürüm tespiti: önce dosya adı kalıbı, sonra PE VersionInfo."""
    name = os.path.basename(path)
    for pat in VERSION_PATTERNS:
        m = pat.search(name)
        if m:
            return m.group(1)
    if name.lower().endswith(".exe"):
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-Item '%s').VersionInfo.ProductVersion" % path.replace("'", "''")],
                capture_output=True, text=True, timeout=30,
            )
            v = (r.stdout or "").strip()
            if re.fullmatch(r"\d+\.\d+\.\d+(\.\d+)?", v):
                return ".".join(v.split(".")[:3])
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def detect_current_version():
    """Güncel sürümü build_data/version.json'dan okur (tek doğruluk kaynağı)."""
    try:
        with open(os.path.join(PROJECT_ROOT, "build_data", "version.json"),
                  encoding="utf-8") as f:
            return json.load(f).get("version")
    except (OSError, ValueError):
        return None


def scan():
    """Tüm derleme dizinlerini tarayıp sürümlere göre sınıflandırır.

    Dönüş: {"current": sürüm, "versions": {sürüm: [mutlak dosya yolları]},
            "unversioned": [yollar]}
    """
    current = detect_current_version()
    versions = {}
    unversioned = []

    targets = [os.path.join(RELEASE_DIR, f) for f in _safe_listdir(RELEASE_DIR)]
    targets += [os.path.join(UPDATES_DIR, f) for f in _safe_listdir(UPDATES_DIR)
                if f.lower().endswith((".zip", ".json"))]
    targets += [os.path.join(INSTALLER_DIR, f) for f in _safe_listdir(INSTALLER_DIR)
                if f.lower().endswith(".exe")]

    for path in targets:
        if not os.path.isfile(path):
            continue
        if os.path.basename(path) == "manifest.json":
            continue  # güncel manifest asla arşivlenmez (güncelleyici okur)
        v = version_of(path)
        if v is None:
            unversioned.append(path)
        else:
            versions.setdefault(v, []).append(path)
    # Deterministik plan sırası (dosya sistemi listeleme sırasına güvenme)
    for files in versions.values():
        files.sort()
    return {"current": current, "versions": versions, "unversioned": unversioned}


def _safe_listdir(d):
    try:
        return os.listdir(d)
    except OSError:
        return []


def staging_dirs():
    """dist/release altındaki gh_release_* staging klasörlerini döndürür."""
    out = []
    for name in _safe_listdir(RELEASE_DIR):
        if name.startswith(STAGING_PREFIX) and \
                os.path.isdir(os.path.join(RELEASE_DIR, name)):
            out.append(os.path.join(RELEASE_DIR, name))
    return sorted(out)


def plan(keep=None, current_override=None, purge_archive=()):
    """Arşivleme/silme planını üretir (hiçbir dosyaya dokunmaz)."""
    info = scan()
    current = current_override or info["current"]
    actions = []
    stats = {"archive_bytes": 0, "delete_bytes": 0, "purge_bytes": 0}

    for ver, files in sorted(info["versions"].items()):
        if ver == current:
            continue  # güncel sürüm dursun
        if keep and ver in keep:
            _p(f"  koru (bayrak): v{ver} ({len(files)} dosya)")
            continue
        for path in files:
            actions.append(("archive", path, ver))
            stats["archive_bytes"] += os.path.getsize(path)

    # manifest eski sürümde kalıyorsa güncelleme paketiyle birlikte taşınır;
    # güncel manifest zaten atlandı (scan).
    for path in info["unversioned"]:
        actions.append(("keep", path, None))
        _p(f"  sürümsüz (dokunulmaz): {os.path.relpath(path, PROJECT_ROOT)}")

    # GitHub Release staging klasörleri: hiçbir aksiyon üretilmez, yalnızca
    # koruma kaydı düşer (yanlışlıkla arşivleme/silme savunması).
    for sdir in staging_dirs():
        _p(f"  staging (korunur): {os.path.relpath(sdir, PROJECT_ROOT)}/ "
           f"({_dir_size(sdir) / 1048576:.0f} MB)")

    if _dir_nonempty(BUILD_DIR):
        actions.append(("delete_dir", BUILD_DIR, None))
        stats["delete_bytes"] += _dir_size(BUILD_DIR)

    for ver in purge_archive:
        adir = os.path.join(ARCHIVE_DIR, f"v{ver}")
        if os.path.isdir(adir):
            actions.append(("purge", adir, ver))
            stats["purge_bytes"] += _dir_size(adir)
        else:
            _p(f"  uyarı: arşivde v{ver} yok, purge atlandı")
    return {"current": current, "actions": actions, "stats": stats}


def _dir_size(d):
    total = 0
    for root, _dirs, files in os.walk(d):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _dir_nonempty(d):
    return os.path.isdir(d) and bool(os.listdir(d))


def apply(planned, write_checksums=True):
    """Planı uygular; archive/v<sürüm>/SHA256SUMS.txt yazar."""
    done = {"archived": 0, "purged": 0, "build_removed": False}
    archives = {}

    for action, target, ver in planned["actions"]:
        if action == "archive":
            dest_dir = os.path.join(ARCHIVE_DIR, f"v{ver}")
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, os.path.basename(target))
            _p(f"  arşivle: {os.path.relpath(target, PROJECT_ROOT)} -> "
               f"{os.path.relpath(dest, PROJECT_ROOT)}")
            shutil.move(target, dest)
            done["archived"] += 1
            archives.setdefault(f"v{ver}", []).append(dest)
        elif action == "delete_dir":
            _p(f"  sil: {os.path.relpath(target, PROJECT_ROOT)}/ (PyInstaller ara dosyaları)")
            shutil.rmtree(target, ignore_errors=True)
            done["build_removed"] = True
        elif action == "purge":
            _p(f"  arşivden sil: {os.path.relpath(target, PROJECT_ROOT)}/")
            shutil.rmtree(target, ignore_errors=True)
            done["purged"] += 1

    if write_checksums:
        for ver_dir, files in archives.items():
            lines = []
            for f in sorted(files):
                rel = os.path.basename(f)
                lines.append(f"{sha256_of(f)}  {rel}")
            sums = os.path.join(ARCHIVE_DIR, ver_dir, "SHA256SUMS.txt")
            # LF satır sonu: Windows metin modu CRLF yazarsa sha256sum -c
            # dosya adlarındaki \r nedeniyle başarısız olur.
            with open(sums, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines) + "\n")
            _p(f"  sağlama yazıldı: {os.path.relpath(sums, PROJECT_ROOT)}")
    return done


def main():
    ap = argparse.ArgumentParser(description="Derleme çıktı temizliği ve arşivleme")
    ap.add_argument("--apply", action="store_true",
                    help="Planı uygula (verilmezse yalnızca göster)")
    ap.add_argument("--keep", action="append", default=[],
                    help="Bu sürümü arşivleme (tekrarlanabilir: --keep 1.2.1)")
    ap.add_argument("--current", help="Güncel sürümü elle sabitle")
    ap.add_argument("--clean-build", action="store_true",
                    help="build/ PyInstaller ara dosyalarını sil")
    ap.add_argument("--purge-archive", action="append", default=[],
                    help="Arşivden bu sürümü tamamen sil (tekrarlanabilir)")
    ap.add_argument("--purge-all-archives", action="store_true",
                    help="Arşivdeki tüm sürümleri sil (ONAY GEREKTİRİR)")
    args = ap.parse_args()

    purge = list(args.purge_archive)
    if args.purge_all_archives:
        if not args.apply:
            _p("--purge-all-archives yalnızca --apply ile çalışır.")
            return 2
        answer = input("TÜM arşiv sürümleri silinecek. Onay için 'EVET' yazın: ")
        if answer.strip() != "EVET":
            _p("Onay verilmedi; işlem iptal.")
            return 2
        for name in _safe_listdir(ARCHIVE_DIR):
            if name.startswith("v"):
                purge.append(name[1:])

    planned = plan(keep=set(args.keep), current_override=args.current,
                   purge_archive=purge)

    print(f"\n[clean] Güncel sürüm: v{planned['current']}")
    a = planned["stats"]["archive_bytes"]
    d = planned["stats"]["delete_bytes"]
    pg = planned["stats"]["purge_bytes"]
    print(f"[clean] Plan: {sum(1 for x in planned['actions'] if x[0] == 'archive')} dosya arşiv "
          f"({a / 1048576:.1f} MB) | build sil {d / 1048576:.1f} MB | "
          f"arşivden sil {pg / 1048576:.1f} MB")
    if not planned["actions"]:
        _p("Yapılacak işlem yok.")
        return 0
    if not args.apply:
        _p("Dry-run modu: hiçbir dosyaya dokunulmadı. Uygulamak için --apply ekleyin.")
        return 0

    done = apply(planned)
    freed = (a + d + pg) / 1048576
    _p(f"Tamamlandı: {done['archived']} dosya arşivlendi, "
       f"{'build/ silindi' if done['build_removed'] else 'build/ korunmuş'}, "
       f"{done['purged']} arşiv sürümü silindi — ~{freed:.1f} MB yer açıldı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
