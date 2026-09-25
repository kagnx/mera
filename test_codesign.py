"""
Kod imzalama modülü (tools/codesign.py) için statik ve davranışsal testler.

signtool/sertifika kurulu olmasını gerektirmez; komut üretimi, yapılandırma
önceliği, parola gizliliği ve maybe_sign davranışları sahte ortamda doğrulanır.

Çalıştırma:  python tests/test_codesign.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from tools import codesign  # noqa: E402

PASS = 0
FAIL = []


def check(name, condition, detail=""):
    global PASS
    PASS += 1
    if condition:
        print(f"  [OK]   {name}")
    else:
        FAIL.append(name)
        print(f"  [FAIL] {name} {detail}")


class EnvClean:
    """İmza ortam değişkenlerini test süresince temizler, sonra geri koyar."""

    VARS = [codesign.ENV_PFX, codesign.ENV_PFX_PASSWORD, codesign.ENV_SHA1,
            codesign.ENV_TIMESTAMP]

    def __enter__(self):
        self._saved = {v: os.environ.get(v) for v in self.VARS}
        for v in self.VARS:
            os.environ.pop(v, None)
        return self

    def __exit__(self, *exc):
        for v, val in self._saved.items():
            if val is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = val


class TmpConfig:
    """codesign.CONFIG_PATH'ı geçici dosyaya yönlendirir."""

    def __init__(self, data=None):
        self.tmp = tempfile.mkdtemp(prefix="sign_")
        self.path = os.path.join(self.tmp, "signing.json")
        self._saved = codesign.CONFIG_PATH
        if data is not None:
            import json
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f)

    def __enter__(self):
        codesign.CONFIG_PATH = self.path
        return self

    def __exit__(self, *exc):
        codesign.CONFIG_PATH = self._saved


def test_find_signtool_graceful():
    print("1) signtool bulucu güvenli davranış")
    result = codesign.find_signtool()
    check("bulucu çökmeden döner", result is None or os.path.isfile(result), str(result))
    if result is None:
        print("  [INFO] signtool kurulu değil; davranışsal testler sahte ortamda koşar")


def test_build_sign_command():
    print("2) İmza komutu üretimi")
    with EnvClean():
        cfg = {"pfx": "C:\\sertifika.pfx", "pfx_password_env": "MY_PW",
               "sha1": "", "timestamp_url": "http://ts.example.com"}
        cmd = codesign.build_sign_command("hedef.exe", cfg)
        joined = " ".join(cmd)
        check("/fd SHA256 var", "/fd" in cmd and "SHA256" in cmd)
        check("/f pfx yolu içerir", cmd[cmd.index("/f") + 1] == "C:\\sertifika.pfx")
        check("parola yer tutucusu var", f"${{MY_PW}}" in cmd)
        check("RFC3161 damgası var", "/tr" in cmd and "http://ts.example.com" in cmd)
        check("/td SHA256 var", "/td" in cmd and "SHA256" in cmd)
        check("hedef dosya sonda", cmd[-1] == "hedef.exe")
        # SHA1 parmak izi modu
        cfg2 = {"pfx": "", "pfx_password_env": "MY_PW", "sha1": "ABCDEF1234",
                "timestamp_url": codesign.DEFAULT_TIMESTAMP_URL}
        cmd2 = codesign.build_sign_command("x.exe", cfg2)
        check("sha1 modu", cmd2[cmd2.index("/sha1") + 1] == "ABCDEF1234")
        # Yapılandırmasız hata
        try:
            codesign.build_sign_command("x.exe", {"pfx": "", "sha1": ""})
            check("yapılandırmasız komut hatası", False)
        except ValueError:
            check("yapılandırmasız komut hatası", True)


def test_load_config_priority():
    print("3) Yapılandırma önceliği: ortam > dosya; komut satırı > hepsi")
    with EnvClean() as env:
        with TmpConfig({"pfx": "dosya.pfx", "sha1": "dosya_izi"}):
            cfg = codesign.load_config()
            check("dosya pfx okundu", cfg["pfx"] == "dosya.pfx")
            check("dosya sha1 okundu", cfg["sha1"] == "dosya_izi")
            # Ortam değişkeni dosyayı ezer
            os.environ[codesign.ENV_PFX] = "ortam.pfx"
            os.environ[codesign.ENV_SHA1] = "  ABC  "
            cfg = codesign.load_config()
            check("ortam pfx dosyayı ezer", cfg["pfx"] == "ortam.pfx")
            check("sha1 boşluksuz-küçük harf", cfg["sha1"] == "abc")
            # Komut satırı her şeyi ezer
            cfg = codesign.load_config({"pfx": "cli.pfx"})
            check("komut satırı en yüksek öncelik", cfg["pfx"] == "cli.pfx")
            # enabled: PFX kipi + parolasız -> devre dışı (SHA1 boş senaryo)
            saved_sha1 = os.environ.pop(codesign.ENV_SHA1, None)
            saved_pfx = os.environ.pop(codesign.ENV_PFX, None)
            with TmpConfig({"pfx": "ortam.pfx", "sha1": ""}):
                cfg = codesign.load_config()
                check("parolasız imza devre dışı", cfg["enabled"] is False)
            if saved_sha1 is not None:
                os.environ[codesign.ENV_SHA1] = saved_sha1
            if saved_pfx is not None:
                os.environ[codesign.ENV_PFX] = saved_pfx
            os.environ[codesign.ENV_PFX_PASSWORD] = "gizli"
            cfg = codesign.load_config()
            check("parola env'i ile etkin", cfg["enabled"] is True)
            # Parola değeri yapılandırmaya sızmiyor
            check("parola değeri config dışı", "gizli" not in str(cfg))

    # --- EV donanım token kipi: SHA1 parmak izi TEK BAŞINA yeterli ---
    # (1.2.5 öncesi kusur: SHA1 kipinde de PFX parolası env'i isteniyordu;
    #  EV token'da özel anahtar çıkarılamaz + PIN'i sürücü sorar -> parola yok)
    with EnvClean():
        with TmpConfig({"pfx": "", "sha1": "aabbccddeeff00112233445566778899aabbccdd"}):
            cfg = codesign.load_config()
            check("EV token: parolasız etkin", cfg["enabled"] is True,
                  str(cfg["enabled"]))
            check("EV token: sha1 korundu", cfg["sha1"].startswith("aabbccdd"))
            # PFX kipi hâlâ parola ister (regresyon koruması)
        with TmpConfig({"pfx": "C:\\x.pfx", "sha1": ""}):
            cfg = codesign.load_config()
            check("PFX: parolasız devre dışı", cfg["enabled"] is False)


def test_maybe_sign_requires():
    print("4) maybe_sign: require kilidi ve uyarılı devam")
    with EnvClean():
        cfg = {"pfx": "", "sha1": "", "pfx_password_env": codesign.ENV_PFX_PASSWORD,
               "timestamp_url": "", "enabled": False}
        logs = []
        # require=False: uyarı verip atlar
        r = codesign.maybe_sign(["x.exe"], cfg=cfg, require=False, log=logs.append)
        check("yapılandırmasız atlanır", r["skipped"] is True and r["signed"] == [])
        check("uyarı loglandı", any("UYARI" in m for m in logs))
        # require=True: hata fırlatır (CI kilidi)
        try:
            codesign.maybe_sign(["x.exe"], cfg=cfg, require=True)
            check("require ile hata fırlatır", False)
        except RuntimeError:
            check("require ile hata fırlatır", True)


def test_pfx_password_missing_raises():
    print("5) PFX parolası eksikse anlaşılır hata")
    with EnvClean():
        cfg = {"pfx": "yok.pfx", "pfx_password_env": "TEST_PW_ENV",
               "sha1": "", "timestamp_url": "", "enabled": True}
        # Parola yok -> sign_file parola hatası fırlatmalı (signtool bulunamasa bile parola önce)
        try:
            codesign.sign_file("x.exe", cfg)
            check("parolasız sign_file hatası", False, "hata fırlamadı")
        except (ValueError, FileNotFoundError) as exc:
            check("parolasız sign_file hatası",
                  "TEST_PW_ENV" in str(exc) or "signtool" in str(exc), str(exc))


def test_example_config_shape():
    print("6) Örnek yapılandırma dosyası biçimi")
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "build_data", "signing.example.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    check("örnek pfx alanı var", "pfx" in data)
    check("örnek password_env var", data.get("pfx_password_env") == codesign.ENV_PFX_PASSWORD)
    check("örnek parola İÇERMEZ", not any(
        "password" in k.lower() and k != "pfx_password_env" for k in data))
    check("parola değeri yok", not any(
        isinstance(v, str) and v and k.lower().endswith("password") for k, v in data.items()))


def test_ev_token_guide():
    print("7) EV token kılavuzu tutarlılığı")
    guide = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "EV_TOKEN_GUIDE.md",
    )
    check("kılavuz mevcut", os.path.isfile(guide), guide)
    if not os.path.isfile(guide):
        return
    with open(guide, encoding="utf-8") as f:
        doc = f.read()
    for token, name in [
        ("MERA_SIGN_SHA1", "ortam değişkeni adı doğru"),
        ("/sha1", "signtool kipi belgelenmiş"),
        ("Cert:\\CurrentUser\My", "sertifika deposu yolu"),
        ("RFC3161", "zaman damgası standardı"),
        ("/td", "özet algoritma bayrağı"),
        ("KeyLocker", "bulut imza servisi"),
        ("Trusted Signing", "Azure imza servisi"),
        ("PIN", "token PIN akışı"),
    ]:
        check(f"kılavuzda {name}", token in doc)
    # Kılavuz PFX parolası env adını da yanlış yazmamalı
    check("env adı birebir", codesign.ENV_PFX_PASSWORD in doc)


def test_parse_verify_output():
    print("8) signtool verify çıktı ayrıştırıcı (gerçek çıktı örnekleriyle)")
    unsigned = (
        "Verifying: dist/MERA_BIS_PRO.exe\n"
        "Number of files successfully Verified: 0\n"
        "Number of warnings: 0\n"
        "Number of errors: 1\n"
        "SignTool Error: No signature found.\n"
    )
    signed_no_trust = (
        "Verifying: build_data/_signtest/MERA_BIS_PRO_test.exe\n"
        "Signature Index: 0 (Primary Signature)\n"
        "Hash of file (sha256): 722B965E46304C1649247E0D1578030B6BD40EB3D4E38500B988D2B3E85CCBCD\n"
        "SignTool Error: A certificate chain processed, but terminated in a root "
        "certificate which is not trusted.\n"
    )
    signed_valid = (
        "Verifying: dist/MERA_BIS_PRO.exe\n"
        "Signature Index: 0 (Primary Signature)\n"
        "Hash of file (sha256): 722B965E46304C1649247E0D1578030B6BD40EB3D4E38500B988D2B3E85CCBCD\n"
        "Successfully verified: dist/MERA_BIS_PRO.exe\n"
    )
    s1, h1 = codesign._parse_verify_output(unsigned)
    check("imzasız: signed False", s1 is False)
    check("imzasız: hash None", h1 is None)
    s2, h2 = codesign._parse_verify_output(signed_no_trust)
    check("gömülü ama güvensiz: signed True", s2 is True)
    check("gömülü: dosya hash'i alındı", h2 == "722B965E46304C1649247E0D1578030B6BD40EB3D4E38500B988D2B3E85CCBCD")
    s3, h3 = codesign._parse_verify_output(signed_valid)
    check("geçerli: signed True", s3 is True)
    check("geçerli: hash alındı", h3 is not None)
    # 'No signature found' her zaman üstün gelir
    s4, _ = codesign._parse_verify_output("Signature Index: 0\nNo signature found")
    check("çelişkili çıktıda imzasız kazanır", s4 is False)


def main():
    test_find_signtool_graceful()
    test_build_sign_command()
    test_load_config_priority()
    test_maybe_sign_requires()
    test_pfx_password_missing_raises()
    test_example_config_shape()
    test_ev_token_guide()
    test_parse_verify_output()

    passed = PASS - len(FAIL)
    print(f"\nSONUC: {passed}/{PASS} gecti, {len(FAIL)} basarisiz")
    for f in FAIL:
        print("  FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
