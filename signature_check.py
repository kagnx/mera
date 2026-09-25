"""
Uygulama imzası denetimi — imzasız paket çalıştığında kullanıcıyı uyarır.

Authenticode imzalama (DER/PKCS#7) saf Python'da ayrıştırılamayacağı için
kontrol üç katmanlıdır:

1. **WinVerifyTrust (Windows, paketli mod)**: PowerShell
   `Get-AuthenticodeSignature` ile imza durumunu sorgular; `Valid` → imzalı,
   diğer her durum → imzasız/uyarılmalı.
2. **Kaynak ağacı (source tree)**: `sys.frozen` yoksa geliştirme ortamıdır;
   uyarı gösterilmez (geliştirici imzayı kendisi doğrular) — `NotApplicable`.
3. **Windows dışı / PowerShell yoksa**: `UnknownPlatform` — paketli modda
   muhafazakâr davranıp uyarı gösterilir (yanlış negatiften iyidir).

Dönüş değeri: {"state", "detail", "signed"} — `state` ∈
{"Valid", "NotSigned", "HashMismatch", "UnknownError", "NotApplicable",
"UnknownPlatform"}.
"""
import logging
import os
import shutil
import subprocess
import sys

LOG = logging.getLogger("merabis.signature")

KNOWN_STATES = {
    "Valid", "NotSigned", "HashMismatch", "UnknownError",
    "NotApplicable", "UnknownPlatform",
}


def check_executable_signature(path=None):
    """Verilen exe'nin (varsayılan: çalışan yürütülebilir) imza durumunu döndürür.

    Kaynak modda imza sorgusu yapılmaz (NotApplicable). PowerShell yoksa veya
    sorgu başarısızsa paketli modda UnknownPlatform döner (uyarılmalı sayılır).
    """
    if not (getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")):
        return {"state": "NotApplicable", "detail": "source tree", "signed": True}

    exe = path or sys.executable
    if not exe or not os.path.isfile(exe):
        return {"state": "UnknownError", "detail": f"dosya yok: {exe}", "signed": False}

    ps = shutil.which("powershell")
    if ps is None:
        return {"state": "UnknownPlatform", "detail": "powershell yok", "signed": False}

    try:
        r = subprocess.run(
            [
                ps, "-NoProfile", "-NonInteractive", "-Command",
                "(Get-AuthenticodeSignature -LiteralPath '%s').Status.ToString()"
                % exe.replace("'", "''"),
            ],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        LOG.warning("İmza sorgusu başarısız: %s", exc)
        return {"state": "UnknownPlatform", "detail": str(exc), "signed": False}

    status = (r.stdout or "").strip()
    if r.returncode != 0 or status not in KNOWN_STATES:
        detail = status or (r.stderr or "").strip()[:200] or f"rc={r.returncode}"
        return {"state": "UnknownPlatform", "detail": detail, "signed": False}

    return {
        "state": status,
        "detail": exe,
        "signed": status == "Valid",
    }


def should_warn(result=None):
    """Verilen denetim sonucu için kullanıcı uyarısı gerekli mi?"""
    if result is None:
        result = check_executable_signature()
    return not result.get("signed", False)


def warning_message(result):
    """Uyarı diyaloğunda gösterilecek metni üretir (i18n anahtarı + parametreler)."""
    state = result.get("state", "UnknownError")
    detail = result.get("detail", "")
    if state == "NotSigned":
        key = "signature.warn.not_signed"
    elif state == "HashMismatch":
        key = "signature.warn.hash_mismatch"
    elif state == "UnknownPlatform":
        key = "signature.warn.unknown_platform"
    else:
        key = "signature.warn.generic"
    return {
        "key": key,
        "params": {"detail": detail},
        "log": f"İmza denetimi: state={state} detail={detail}",
    }
