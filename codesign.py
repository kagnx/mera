#!/usr/bin/env python3
"""
MERA-BİS PRO — Authenticode kod imzalama modülü.

Windows SDK `signtool` ile exe/setup dosyalarını Authenticode sertifikasıyla
imzalar ve mevcut imzayı doğrular. Derleme zinciri bu modülü kullanır;
imza yapılandırması yoksa derleme uyarı verip imzasız devam eder (CI'da
`--require-sign` verilerek imzasız derleme engellenebilir).

## Yapılandırma (öncelik sırasıyla)

1. Komut satırı:   --pfx yol --pfx-password-env ENV_ADI --sha1 parmakizi
2. Yapılandırma:   build_data/signing.json (örnek: signing.example.json)
3. Ortam değişkenleri:
     MERA_SIGN_PFX          PFX dosya yolu
     MERA_SIGN_PFX_PASSWORD PFX parolası (PAROLA KAYNAĞI DOSYAYA ASLA YAZILMAZ)
     MERA_SIGN_SHA1         Sertifika parmak izi (SHA1, boşluksuz)
     MERA_SIGN_TIMESTAMP    RFC3161 zaman damgası sunucusu (isteğe bağlı)

## Güvenlik kuralları

- PFX parolası yalnızca ortam değişkeninden okunur; hiçbir dosyaya yazılmaz.
- PFX dosyası derleme çıktılarına (dist/, updates/, installer/Output/)
  kopyalanmaz; _iter_app_files güncelleme yedeklerinde de hariç tutar.
- Zaman damgası verilirse imza, sertifika süresi dolsa da geçerli kalır.
"""
import json
import os
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "build_data", "signing.json")

# Yaygın signtool konumları (Windows SDK sürümleri yeniden eskiye)
_SIGTOOL_CANDIDATES = [
    r"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
    r"C:\Program Files (x86)\Windows Kits\10\bin\x86\signtool.exe",
]
_SDK_KITS_ROOTS = [
    r"C:\Program Files (x86)\Windows Kits\10\bin",
    r"C:\Program Files\Windows Kits\10\bin",
]

DEFAULT_TIMESTAMP_URL = "http://timestamp.digicert.com"

# Ortam değişkeni adları (tek doğruluk kaynağı; testler de bunu kullanır)
ENV_PFX = "MERA_SIGN_PFX"
ENV_PFX_PASSWORD = "MERA_SIGN_PFX_PASSWORD"
ENV_SHA1 = "MERA_SIGN_SHA1"
ENV_TIMESTAMP = "MERA_SIGN_TIMESTAMP"


def find_signtool():
    """signtool.exe'yi PATH ve Windows SDK klasik konumlarında arar (en yeni SDK öncelikli)."""
    found = shutil.which("signtool.exe")
    if found:
        return found
    # SDK bin kökünde sürüm klasörleri (10.0.22621.0 vb.) yeniden eskiye
    for root in _SDK_KITS_ROOTS:
        if os.path.isdir(root):
            versions = sorted(
                (d for d in os.listdir(root) if d.startswith("10.")),
                reverse=True,
            )
            for v in versions:
                for arch in ("x64", "x86"):
                    cand = os.path.join(root, v, arch, "signtool.exe")
                    if os.path.isfile(cand):
                        return cand
    for cand in _SIGTOOL_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return None


def load_config(explicit=None):
    """İmza yapılandırmasını dosya + ortam değişkenlerinden birleştirir.

    explicit: komut satırı değerleri (pfx, pfx_password_env, sha1, timestamp_url).
    Dönen sözlük: {pfx, pfx_password_env, sha1, timestamp_url, enabled}.
    Parola DEĞERİ asla dönmez; yalnızca hangi ortam değişkeninden okunacağı döner.
    """
    cfg = {"pfx": "", "pfx_password_env": ENV_PFX_PASSWORD, "sha1": "",
           "timestamp_url": DEFAULT_TIMESTAMP_URL}
    # 1) dosya
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in ("pfx", "pfx_password_env", "sha1", "timestamp_url"):
                if data.get(k):
                    cfg[k] = str(data[k])
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[sign] UYARI: {CONFIG_PATH} okunamadı: {exc}")
    # 2) ortam değişkenleri (dosyayı ezer)
    if os.environ.get(ENV_PFX):
        cfg["pfx"] = os.environ[ENV_PFX]
    if os.environ.get(ENV_SHA1):
        cfg["sha1"] = os.environ[ENV_SHA1].replace(" ", "").lower()
    if os.environ.get(ENV_TIMESTAMP):
        cfg["timestamp_url"] = os.environ[ENV_TIMESTAMP]
    # 3) komut satırı (her şeyi ezer)
    if explicit:
        if explicit.get("pfx"):
            cfg["pfx"] = explicit["pfx"]
        if explicit.get("pfx_password_env"):
            cfg["pfx_password_env"] = explicit["pfx_password_env"]
        if explicit.get("sha1"):
            cfg["sha1"] = explicit["sha1"].replace(" ", "").lower()
        if explicit.get("timestamp_url"):
            cfg["timestamp_url"] = explicit["timestamp_url"]
    # Etkinlik kuralları:
    # - PFX kipi: gerçek dosya + parola ortam değişkeni gerekir.
    # - SHA1 kipi (donanım token/EV/HSM): parmak izi yeterlidir; özel anahtar
    #   token'da/sertifikada deposunda yaşadığı için PAROLA ENV'İ GEREKMEZ —
    #   PIN'i token CSP/KSP'si imzalama anında sorar (bkz. EV_TOKEN_GUIDE.md).
    password_env_set = bool(os.environ.get(cfg["pfx_password_env"]))
    cfg["enabled"] = bool(
        (cfg["pfx"] and os.path.isfile(cfg["pfx"]) and password_env_set)
        or bool(cfg["sha1"])
    )
    return cfg


def build_sign_command(file_path, cfg):
    """Verilen yapılandırmayla signtool sign komut listesini üretir.

    Parola komut satırına KOYULMAZ (`/fd` + `/tr` + `/td` yeterli); PFX parolası
    signtool'un güvenli istemine bırakılamayacağı için ortam değişkeni üzerinden
    subprocess env'ine aktarılır (bkz. sign_file).
    """
    cmd = ["signtool", "sign", "/fd", "SHA256", "/v"]
    pw_env = cfg.get("pfx_password_env") or ENV_PFX_PASSWORD
    if cfg.get("pfx"):
        cmd += ["/f", cfg["pfx"]]
        cmd += ["/p", f"${{{pw_env}}}"]  # yer tutucu; sign_file'da gerçek parolayla değişir
    elif cfg.get("sha1"):
        cmd += ["/sha1", cfg["sha1"]]
    else:
        raise ValueError("İmza yapılandırması eksik: PFX dosyası veya SHA1 parmak izi gerekli.")
    ts = cfg.get("timestamp_url") or DEFAULT_TIMESTAMP_URL
    cmd += ["/tr", ts, "/td", "SHA256"]
    cmd.append(file_path)
    return cmd


def sign_file(file_path, cfg):
    """Dosyayı Authenticode ile imzalar; başarılıysa True döndürür.

    Parola, ortam değişkeninden okunup yalnızca alt sürecin env'ine konur;
    komut satırı argümanlarına veya loglara asla sızmaz.
    """
    signtool = find_signtool()
    if not signtool:
        raise FileNotFoundError("signtool.exe bulunamadı (Windows SDK kurulu mu?)")
    cmd = build_sign_command(file_path, cfg)
    pw_env = cfg.get("pfx_password_env") or ENV_PFX_PASSWORD
    placeholder = f"${{{pw_env}}}"
    if placeholder in cmd:
        password = os.environ.get(pw_env)
        if not password:
            raise ValueError(
                f"PFX parolası bulunamadı: '{pw_env}' ortam değişkenini ayarlayın.")
        cmd[cmd.index(placeholder)] = password

    env = dict(os.environ)
    env.setdefault(pw_env, os.environ.get(pw_env, ""))
    # /p ile geçen parola argüman listesinde; proc argümanları kısa ömürlüdür
    # ama log temizliği için çıktıyı süzüyoruz.
    r = subprocess.run([signtool] + cmd[1:], capture_output=True, text=True,
                       errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if pw_env in out:  # signtool ayrıntılı modda parolayı yazdırmaz ama garanti
        out = out.replace(os.environ.get(pw_env, ""), "***")
    if r.returncode != 0:
        raise RuntimeError(f"İmzalama başarısız (kod {r.returncode}):\n{out[:2000]}")
    return True


def verify_signature(file_path):
    """Dosyanın Authenticode imzasını doğrular; geçerliyse True döner."""
    signtool = find_signtool()
    if not signtool:
        raise FileNotFoundError("signtool.exe bulunamadı (Windows SDK kurulu mu?)")
    r = subprocess.run([signtool, "verify", "/pa", "/v", file_path],
                       capture_output=True, text=True, errors="replace")
    return r.returncode == 0


def _parse_verify_output(out):
    """signtool verify /v çıktısını ayrıştırır: (imza_gömülü_mü, dosya_sha256).

    Gerçek çıktı örnekleri (signtool 10.x):
      imzasız : "SignTool Error: No signature found."
      gömülü  : "Signature Index: 0 (Primary Signature)" + "Hash of file (sha256): <64 hex>"
    NOT: kelime-bazlı "Signed" araması imzalı dosyada da False verir; çünkü
    gömülü imza çıktıda "Signature Index" biçiminde geçer. Bu kusur gerçek
    imzalama denemesinde yakalandı (v1.2.7).
    """
    signed = (
        "Signature Index:" in out
        or "Successfully verified" in out
        or "imzalı" in out.lower()
    )
    if "No signature found" in out:
        signed = False
    m = re.search(r"Hash of file \(sha256\):\s*([0-9A-Fa-f]{64})", out)
    file_hash = m.group(1).upper() if m else None
    return signed, file_hash


def get_signature_status(file_path):
    """İmza durumunu insan-okur özetle döndürür: {signed, valid, detail}.

    signed: imza gömülü mü (güven zincirinden bağımsız).
    valid : imza güvenilen bir köke uzuyor mu (signtool çıkış kodu).
    """
    signtool = find_signtool()
    if not signtool:
        return {"signed": False, "valid": False, "detail": "signtool yok"}
    r = subprocess.run([signtool, "verify", "/pa", "/v", file_path],
                       capture_output=True, text=True, errors="replace")
    out = ((r.stdout or "") + (r.stderr or ""))
    signed, file_hash = _parse_verify_output(out)
    detail = " ".join(out.split())[:300]
    if file_hash:
        detail = f"sha256={file_hash} | {detail}"[:300]
    return {
        "signed": signed,
        "valid": r.returncode == 0,
        "detail": detail,
    }


def maybe_sign(files, cfg=None, require=False, log=None):
    """Derleme zinciri yardımcısı: yapılandırma varsa dosyaları imzalar.

    require=True ise imza yapılandırması yoksa/imzalama başarısızsa hata fırlatır
    (CI kilidi). Yoksa uyarı verip imzasız devam eder (yerel geliştirici akışı).
    Dönen: {"signed": [dosyalar], "skipped": bool, "reason": str}
    """
    log = log or print
    if cfg is None:
        cfg = load_config()
    if not cfg.get("enabled"):
        msg = ("İmza yapılandırması yok (MERA_SIGN_PFX/MERA_SIGN_SHA1 + parola); "
               "dosyalar imzasız bırakılıyor.")
        if require:
            raise RuntimeError("İmza zorunlu (--require-sign): " + msg)
        log(f"[sign] UYARI: {msg}")
        return {"signed": [], "skipped": True, "reason": msg}
    signed = []
    for f in files:
        sign_file(f, cfg)
        if not verify_signature(f):
            if require:
                raise RuntimeError(f"İmza doğrulaması başarısız: {f}")
            log(f"[sign] UYARI: imza doğrulanamadı: {f}")
            continue
        signed.append(f)
        log(f"[sign] İmzalandı: {f}")
    return {"signed": signed, "skipped": False, "reason": ""}


def main():
    """Komut satırı: imzala / doğrula / durum sorgula."""
    import argparse
    ap = argparse.ArgumentParser(description="MERA-BİS PRO Authenticode imzalama")
    ap.add_argument("command", choices=["sign", "verify", "status"])
    ap.add_argument("files", nargs="+", help="İmzalanacak/doğrulanacak dosyalar")
    ap.add_argument("--pfx", help="PFX sertifika dosyası")
    ap.add_argument("--pfx-password-env", default=ENV_PFX_PASSWORD,
                    help=f"PFX parolasının bulunduğu ortam değişkeni (varsayılan {ENV_PFX_PASSWORD})")
    ap.add_argument("--sha1", help="Sertifika SHA1 parmak izi (sertifika deposunda)")
    ap.add_argument("--timestamp-url", default=None, help="RFC3161 zaman damgası URL'si")
    args = ap.parse_args()

    cfg = load_config({
        "pfx": args.pfx, "pfx_password_env": args.pfx_password_env,
        "sha1": args.sha1, "timestamp_url": args.timestamp_url,
    })
    if args.command == "sign":
        result = maybe_sign(args.files, cfg=cfg, require=True)
        print(f"İmzalanan: {len(result['signed'])} dosya")
        return 0
    ok = True
    for f in args.files:
        if args.command == "verify":
            valid = verify_signature(f)
            print(f"{'GEÇERLİ' if valid else 'GEÇERSİZ'}: {f}")
            ok = ok and valid
        else:
            st = get_signature_status(f)
            print(f"{f}: {st['detail']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
