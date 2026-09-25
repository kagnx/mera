#!/usr/bin/env python3
"""
MERA-BİS PRO — Inno Setup kurulum sihirbazı derleyici.

Kullanım:
    python tools/build_installer.py                 # derle
    python tools/build_installer.py --skip-version  # sürüm damgasını güncelleme

Adımlar:
  1. ISCC.exe'yi bulur (PATH, %ProgramFiles(x86)% vb. klasik konumlar).
  2. installer/MERA_BIS_PRO.iss içindeki MyAppVersion satırını
     build_data/version.json'daki sürümle eşitler (tek doğruluk kaynağı).
  3. ISCC ile derler; çıktı: installer/Output/MERA_BIS_PRO_Setup_v<sürüm>.exe
  4. Çıktının varlığını, sürüm damgasını ve boyutunu doğrular.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
import codesign  # noqa: E402
import versioning  # noqa: E402  — publisher metadata tek doğruluk kaynağı

ISS_PATH = os.path.join(PROJECT_ROOT, "installer", "MERA_BIS_PRO.iss")

# Yaygın Inno Setup kurulum konumları (en yeniden eskiye)
ISCC_CANDIDATES = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    r"C:\Program Files\Inno Setup 5\ISCC.exe",
]


def find_iscc():
    """ISCC.exe'yi PATH ve klasik konumlarda arar; bulursa yolunu döndürür."""
    found = shutil.which("ISCC.exe")
    if found:
        return found
    for cand in ISCC_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    # Chocolatey / scoop konumları
    choco = os.path.join(os.environ.get("ProgramData", ""), "chocolatey", "bin", "ISCC.exe")
    if os.path.isfile(choco):
        return choco
    scoop = os.path.join(os.environ.get("USERPROFILE", ""), "scoop", "shims", "ISCC.exe")
    if os.path.isfile(scoop):
        return scoop
    return None


def stamp_version(iss_path, version):
    """ISS dosyasındaki MyAppVersion + MyAppPublisher satırlarını damgalar.

    - MyAppVersion  : build_data/version.json'dan gelen sürüm
    - MyAppPublisher: versioning.COMPANY_NAME (tek doğruluk kaynağı — PE
      şablonundaki CompanyName ile aynı)
    """
    with open(iss_path, "r", encoding="utf-8") as f:
        text = f.read()
    new_text, n = re.subn(
        r"(#define MyAppVersion\s+\")[^\"]+(\")",
        rf"\g<1>{version}\g<2>",
        text,
        count=1,
    )
    if n != 1:
        raise RuntimeError("ISS dosyasında MyAppVersion satırı bulunamadı.")
    new_text, n_pub = re.subn(
        r"(#define MyAppPublisher\s+\")[^\"]+(\")",
        rf"\g<1>{versioning.COMPANY_NAME}\g<2>",
        new_text,
        count=1,
    )
    if n_pub != 1:
        raise RuntimeError("ISS dosyasında MyAppPublisher satırı bulunamadı.")
    new_text, n_cop = re.subn(
        r"(#define MyAppCopyright\s+\")[^\"]+(\")",
        rf"\g<1>{versioning.LEGAL_COPYRIGHT}\g<2>",
        new_text,
        count=1,
    )
    if n_cop != 1:
        raise RuntimeError("ISS dosyasında MyAppCopyright satırı bulunamadı.")
    if new_text != text:
        with open(iss_path, "w", encoding="utf-8") as f:
            f.write(new_text)
    return version


def compile_installer(iscc_path, iss_path, version=None):
    """ISCC ile kurulum paketini derler; başarı durumunda çıktı yolunu döndürür."""
    r = subprocess.run(
        [iscc_path, "/Q", iss_path],
        cwd=PROJECT_ROOT, capture_output=True, text=True, errors="replace",
    )
    if r.returncode != 0:
        print("[installer] ISCC hatası:")
        print(r.stdout)
        print(r.stderr)
        return None
    return _expected_output_path(iss_path, version=version)


def _expected_output_path(iss_path, version=None):
    """ISS'ten OutputDir ve OutputBaseFilename okuyup beklenen çıktı yolunu üretir.

    OutputBaseFilename içindeki {#MyAppVersion} yer tutucusu gerçek sürümle
    değiştirilir (ör. 'Setup_v{#MyAppVersion}' -> 'Setup_v1.2.3'); sürüm öncelikle
    `version` parametresinden, o yoksa ISS'in kendi #define MyAppVersion
    satırından okunur.
    """
    out_dir, base, iss_version = "Output", None, None
    with open(iss_path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*OutputDir=(.+)", line)
            if m:
                out_dir = m.group(1).strip()
            m = re.match(r"\s*OutputBaseFilename=(.+)", line)
            if m:
                base = m.group(1).strip()
            m = re.match(r'\s*#define\s+MyAppVersion\s+"([^"]+)"', line)
            if m:
                iss_version = m.group(1)
    if base is None:
        return None
    resolved = version or iss_version
    if resolved:
        base = base.replace("{#MyAppVersion}", resolved)
    out_dir_abs = out_dir if os.path.isabs(out_dir) else os.path.join(
        os.path.dirname(iss_path), out_dir)
    return os.path.join(out_dir_abs, f"{base}.exe")


def main():
    ap = argparse.ArgumentParser(description="MERA-BİS PRO kurulum sihirbazı derleyici")
    ap.add_argument("--skip-version", action="store_true",
                    help="Sürüm damgasını güncelleme (elle yönetilen sürüm)")
    ap.add_argument("--sign", action="store_true",
                    help="Setup.exe'yi Authenticode ile imzala (yapılandırma gerekir)")
    args = ap.parse_args()

    if not os.path.isfile(ISS_PATH):
        print(f"Hata: ISS betiği bulunamadı: {ISS_PATH}")
        return 1
    if not os.path.isfile(os.path.join(PROJECT_ROOT, "dist", "MERA_BIS_PRO.exe")):
        print("Hata: dist/MERA_BIS_PRO.exe yok. Önce derleyin:")
        print("    python tools/build_release.py --skip-package")
        return 1

    iscc = find_iscc()
    if not iscc:
        print("Hata: Inno Setup (ISCC.exe) bulunamadı.")
        print("Kurulum: https://jrsoftware.org/isdl.php  veya  choco install innosetup")
        return 1
    print(f"[installer] ISCC: {iscc}")

    version = "1.0.0"
    if not args.skip_version:
        with open(os.path.join(PROJECT_ROOT, "build_data", "version.json"),
                  encoding="utf-8") as f:
            version = json.load(f).get("version", "1.0.0")
        stamp_version(ISS_PATH, version)
        print(f"[installer] Sürüm damgalandı: {version}")

    print("[installer] Derleniyor...")
    out = compile_installer(iscc, ISS_PATH)
    if not out or not os.path.isfile(out):
        print("[installer] Derleme çıktısı doğrulanamadı.")
        return 1

    size_mb = os.path.getsize(out) / 1024 / 1024
    print(f"[installer] Tamamlandı: {out} ({size_mb:.1f} MB)")

    if args.sign:
        cfg = codesign.load_config()
        result = codesign.maybe_sign([out], cfg=cfg, require=True,
                                     log=lambda m: print(f"[installer] {m}"))
        print(f"[installer] İmzalanan dosya sayısı: {len(result['signed'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
