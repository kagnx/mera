#!/usr/bin/env python3
"""
MERA-BİS PRO — Tek komutla sürüm derleme ve dağıtım paketi üretimi.

Kullanım:
    python tools/build_release.py                 # derle + updates klasörü oluştur
    python tools/build_release.py --skip-tests    # testleri atla
    python tools/build_release.py --part minor    # minor sürüm artırarak derle

Adımlar:
  1. Test paketi çalıştırılır (başarısızsa derleme durur).
  2. PyInstaller ile tek dosya exe üretilir (sürüm otomatik artar).
  3. Authenticode imzalama: yapılandırma varsa exe + zip + setup imzalanır
     (--require-sign ile imzasız derleme engellenir; varsayılan uyarıyla geçer).
  4. dist/ çıktısı dist/release/MERA_BIS_PRO_v<surum>.exe olarak kopyalanır.
  5. updates/ klasörüne manifest.json + paket zip'i üretilir (SHA-256 ile).
  6. --installer verilirse Inno Setup kurulum sihirbazı derlenir ve imzalanır.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import versioning  # noqa: E402
sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
import codesign  # noqa: E402
import clean_dist  # noqa: E402
import gen_changelog  # noqa: E402


def run(cmd, **kw):
    print(f"[build] $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=PROJECT_ROOT, **kw)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 512), b""):
            h.update(chunk)
    return h.hexdigest()


def run_tests():
    tests = [
        "tests/test_validation.py",
        "tests/test_db_manager.py",
        "tests/test_backup.py",
        "tests/test_versioning.py",
        "tests/test_rotation_planner.py",
        "tests/test_measurements.py",
        "tests/test_installer_script.py",
        "tests/test_i18n.py",
        "tests/test_turkey_data.py",
        "tests/test_update_checker.py",
        "tests/test_update_e2e.py",
        "tests/test_update_artifacts_e2e.py",
        "tests/test_setup_artifacts_e2e.py",
        "tests/test_codesign.py",
        "tests/test_clean_dist.py",
        "tests/test_signature_check.py",
        "tests/test_ci_workflow.py",
        "tests/test_publish_release_script.py",
        "tests/test_gen_changelog.py",
        "tests/test_migration_wizard.py",
    ]
    for t in tests:
        r = run([sys.executable, t])
        if r.returncode != 0:
            print(f"[build] TEST BAŞARISIZ: {t}")
            return False
    return True


def build_exe():
    spec = os.path.join(PROJECT_ROOT, "MERA_BIS_PRO.spec")
    r = run([sys.executable, "-m", "PyInstaller", spec, "--noconfirm", "--clean"])
    return r.returncode == 0


def make_update_package(version, notes="", sign_cfg=None):
    """dist exe'sini zip'leyip updates/manifest.json üretir.
    sign_cfg verilirse zip paketi de imzalanır (manifest SHA imzalı zip'e göre)."""
    exe = os.path.join(PROJECT_ROOT, "dist", "MERA_BIS_PRO.exe")
    if not os.path.isfile(exe):
        print("[build] dist/MERA_BIS_PRO.exe bulunamadı")
        return False

    updates_dir = os.path.join(PROJECT_ROOT, "updates")
    os.makedirs(updates_dir, exist_ok=True)
    zip_name = f"MERA_BIS_PRO_{version}.zip"
    zip_path = os.path.join(updates_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe, "MERA_BIS_PRO.exe")

    # Zip paketi de imzalanabilir (SHA, imzalı zip'in özeti olmalı).
    # NOT: Authenticode yalnızca PE dosyaları kapsar; signtool zip için
    # "file format cannot be signed" hatası verir. Bütünlük zaten manifest
    # SHA-256 + zip içindeki imzalı exe ile sağlanır — nazikçe geç.
    if sign_cfg is not None:
        try:
            codesign.maybe_sign([zip_path], cfg=sign_cfg)
        except RuntimeError as exc:
            print("[build] UYARI: zip Authenticode alamaz (PE olmayan biçim) — "
                  f"bütünlük manifest SHA-256 ile sağlanır: {exc}")

    manifest = {
        "version": version,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "file": zip_name,
        "sha256": sha256_of(zip_path),
        "size": os.path.getsize(zip_path),
        "notes": notes or f"MERA-BİS PRO v{version} sürümü.",
    }
    with open(os.path.join(updates_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Sürüm damgalı dağıtım kopyası
    release_dir = os.path.join(PROJECT_ROOT, "dist", "release")
    os.makedirs(release_dir, exist_ok=True)
    stamped = os.path.join(release_dir, f"MERA_BIS_PRO_v{version}.exe")
    shutil.copy2(exe, stamped)

    print(f"[build] Güncelleme paketi: {zip_path}")
    print(f"[build] Dağıtım kopyası : {stamped}")
    print(f"[build] Manifest        : {os.path.join(updates_dir, 'manifest.json')}")
    return True


def update_changelog(version):
    """Yeni sürüm için CHANGELOG.md bölümünü üretir (git deposunda).

    Son v* etiketinden bu yana commit'leri kategorize edip bölüm ekler.
    Git deposu/etiket yoksa (ör. bu yerel klasör) uyarıyla atlanır —
    derleme etkilenmez. CI'da fetch-depth: 0 ile tam geçmiş okunur.
    """
    try:
        section, written = gen_changelog.generate(version=version, apply=True)
        if written:
            first = next((l for l in section.splitlines() if l.startswith("### ")), "")
            print(f"[build] CHANGELOG.md güncellendi: v{version} ({first.strip('# ') or 'boş'})")
        else:
            print(f"[build] CHANGELOG.md: v{version} bölümü zaten mevcut — atlandı")
        return True
    except gen_changelog.GitUnavailable as exc:
        print(f"[build] UYARI: changelog atlandı ({exc})")
        return True
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"[build] UYARI: changelog üretilemedi (derleme etkilenmedi): {exc}")
        return True


def archive_old_outputs(clean_build=False):
    """Derleme başarılıysa eski sürüm çıktılarını archive/v<sürüm>/ altına taşır.

    Güncel sürüm (build_data/version.json, spec tarafından artırılmış) dışındaki
    tüm sürümlü dosyalar arşivlenir; build/ ara dosyaları isteğe bağlı silinir.
    Arşivlenen her sürüm için SHA256SUMS.txt yazılır. Hata derlemeyi
    başarısız saymaz (uyarıyla geçer).
    """
    try:
        planned = clean_dist.plan(purge_archive=())
        # build/ silme aksiyonunu isteğe bağlı ekle
        if clean_build and clean_dist._dir_nonempty(clean_dist.BUILD_DIR):
            planned["actions"].append(("delete_dir", clean_dist.BUILD_DIR, None))
            planned["stats"]["delete_bytes"] += clean_dist._dir_size(clean_dist.BUILD_DIR)
        if not planned["actions"]:
            print("[build] Arşivlenecek eski sürüm çıktısı yok.")
            return True
        total = (planned["stats"]["archive_bytes"]
                 + planned["stats"]["delete_bytes"]) / 1048576
        print(f"[build] Eski sürüm çıktıları arşivleniyor (~{total:.1f} MB yer açılacak)...")
        clean_dist.apply(planned)
        print("[build] Arşiv tamamlandı: archive/v<sürüm>/ (SHA256SUMS.txt ile)")
        return True
    except (OSError, shutil.Error) as exc:
        print(f"[build] UYARI: arşivleme başarısız (derleme etkilenmedi): {exc}")
        return True


def main():
    ap = argparse.ArgumentParser(description="MERA-BİS PRO sürüm derleme aracı")
    ap.add_argument("--skip-tests", action="store_true", help="Test paketini atla")
    ap.add_argument("--skip-package", action="store_true", help="updates paketi üretme")
    ap.add_argument("--installer", action="store_true",
                    help="Inno Setup kurulum sihirbazını da derle (setup.exe)")
    ap.add_argument("--no-sign", action="store_true",
                    help="Authenticode imzalamayı atla (yapılandırma olsa bile)")
    ap.add_argument("--require-sign", action="store_true",
                    help="İmza yapılandırması yoksa/imzalama başarısızsa derlemeyi durdur (CI)")
    ap.add_argument("--pfx", default=None, help="PFX sertifika dosyası (imzalama)")
    ap.add_argument("--sha1", default=None, help="Sertifika SHA1 parmak izi (imzalama)")
    ap.add_argument("--part", choices=["patch", "minor", "major"], default=None,
                    help="Sürüm artırma birimi (varsayılan: spec patch artırır)")
    ap.add_argument("--notes", default="", help="Manifest notları (sürüm açıklaması)")
    ap.add_argument("--no-changelog", action="store_true",
                    help="CHANGELOG.md otomatik bölüm üretimini atla")
    ap.add_argument("--archive-old", action="store_true",
                    help="Derleme sonrası eski sürüm çıktılarını archive/ altına taşı")
    ap.add_argument("--clean-build", action="store_true",
                    help="--archive-old ile birlikte build/ ara dosyalarını da sil")
    args = ap.parse_args()

    if args.part:
        v = versioning.bump_version(args.part)
        print(f"[build] Sürüm {args.part} olarak artırıldı: {v}")

    if not args.skip_tests:
        print("[build] Test paketi çalıştırılıyor...")
        if not run_tests():
            print("[build] Derleme iptal edildi (testler başarısız).")
            return 1

    if not args.no_changelog:
        update_changelog(versioning.read_version())

    print("[build] PyInstaller derlemesi başlıyor (bu birkaç dakika sürebilir)...")
    if not build_exe():
        print("[build] Derleme başarısız.")
        return 1

    # ---- Authenticode imzalama ----
    sign_cfg = None
    if not args.no_sign:
        explicit = {"pfx": args.pfx, "sha1": args.sha1}
        sign_cfg = codesign.load_config(explicit)
        if sign_cfg.get("enabled"):
            try:
                codesign.maybe_sign(
                    [os.path.join(PROJECT_ROOT, "dist", "MERA_BIS_PRO.exe")],
                    cfg=sign_cfg, require=args.require_sign,
                )
            except (RuntimeError, FileNotFoundError, ValueError) as exc:
                print(f"[build] İmzalama hatası: {exc}")
                if args.require_sign:
                    return 1
                print("[build] İmzasız devam ediliyor...")
                sign_cfg = None
        else:
            msg = "İmza yapılandırması yok; imzasız derleme."
            if args.require_sign:
                print("[build] HATA (--require-sign): " + msg)
                print("       MERA_SIGN_PFX + MERA_SIGN_PFX_PASSWORD veya MERA_SIGN_SHA1 ayarlayın.")
                return 1
            print(f"[build] UYARI: {msg}")
            sign_cfg = None
    else:
        sign_cfg = None

    if not args.skip_package:
        if not make_update_package(versioning.read_version(), notes=args.notes,
                                   sign_cfg=sign_cfg):
            return 1

    if args.installer:
        r = run([sys.executable, os.path.join("tools", "build_installer.py")])
        if r.returncode != 0:
            print("[build] Kurulum sihirbazı derlemesi başarısız.")
            return 1
        if sign_cfg is not None:
            setup_exe = os.path.join(
                PROJECT_ROOT, "installer", "Output",
                f"MERA_BIS_PRO_Setup_v{versioning.read_version()}.exe")
            if os.path.isfile(setup_exe):
                try:
                    codesign.maybe_sign([setup_exe], cfg=sign_cfg,
                                        require=args.require_sign)
                except (RuntimeError, FileNotFoundError, ValueError) as exc:
                    print(f"[build] Setup imzalama hatası: {exc}")
                    if args.require_sign:
                        return 1

    if args.archive_old:
        archive_old_outputs(clean_build=args.clean_build)

    print(f"[build] Tamamlandı — sürüm {versioning.read_version()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
