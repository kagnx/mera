"""
Inno Setup kurulum betiği ve derleyici aracı için statik doğrulama testleri.

ISCC kurulu olmasını gerektirmez; betiğin yapısını, araç mantığını ve
sürüm damgalamayı doğrular.

Çalıştırma:  python tests/test_installer_script.py
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.build_installer import (  # noqa: E402
    ISS_PATH, stamp_version, _expected_output_path, find_iscc,
)

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


def read_iss():
    with open(ISS_PATH, encoding="utf-8") as f:
        return f.read()


def test_iss_structure():
    print("1) ISS betiği yapısı")
    text = read_iss()
    checks = [
        ("AppId tanımlı", re.search(r"AppId=\{\{[0-9A-Fa-f-]+\}", text)),
        ("AppName tanımlı", re.search(r"AppName=\{#MyAppName\}", text)),
        ("AppVersion tanımlı", re.search(r"AppVersion=\{#MyAppVersion\}", text)),
        ("PrivilegesRequired=lowest (yönetici gerektirmez)",
         "PrivilegesRequired=lowest" in text),
        ("exe kaynağı doğru", r'Source: "..\dist\MERA_BIS_PRO.exe"' in text),
        ("ignoreversion bayrağı var", "Flags: ignoreversion" in text),
        ("Türkçe dil dosyası", "Turkish.isl" in text),
        ("İngilizce dil dosyası", "Default.isl" in text),
        ("masaüstü kısayolu görevi", "desktopicon" in text),
        ("başlangıç kısayolu görevi", "startupicon" in text),
        ("kaldırıcı girdisi (UninstallDisplayName)", "UninstallDisplayName" in text),
        ("kaldırma öncesi uygulama kapatma", "[UninstallRun]" in text),
        ("veri dizini oluşturma", "{userappdata}\\MeraBisPro" in text),
        ("setup ikonu bağlı", "SetupIconFile" in text),
        ("sürüm kaynak bilgisi", "VersionInfoVersion" in text),
        ("telif kaynak bilgisi (VersionInfoCopyright)", "VersionInfoCopyright" in text),
        ("şirket kaynağı yayıncıdan (VersionInfoCompany)",
         "VersionInfoCompany={#MyAppPublisher}" in text),
        ("sessiz kurulumda başlatma atlanır", "skipifsilent" in text),
        # --- Kurumsal dağıtım (GPO/Intune) yönergeleri ---
        ("kurulum günlüğü açıkmı (SetupLogging)", "SetupLogging=yes" in text),
        ("çalışan uygulama kapatma (CloseApplications)", "CloseApplications=yes" in text),
        ("yeniden başlatma kapalı (RestartApplications)", "RestartApplications=no" in text),
        ("/NOICONS onayı (AllowNoIcons)", "AllowNoIcons=yes" in text),
        ("kurulum bağlamı geçersiz kılma (OverridesAllowed)",
         "PrivilegesRequiredOverridesAllowed=commandline" in text),
    ]
    for name, cond in checks:
        check(name, bool(cond))


def test_version_stamp():
    print("2) Sürüm damgalama")
    with tempfile.TemporaryDirectory() as tmp:
        fake_iss = os.path.join(tmp, "test.iss")
        with open(fake_iss, "w", encoding="utf-8") as f:
            f.write('#define MyAppVersion "0.0.0"\n#define MyAppName "X"\n'
                    '#define MyAppPublisher "Y"\n#define MyAppCopyright "C"\n')
        stamp_version(fake_iss, "1.2.3")
        with open(fake_iss, encoding="utf-8") as f:
            content = f.read()
        check("sürüm güncellendi", '#define MyAppVersion "1.2.3"' in content, content)
        check("diğer satırlar korundu", '#define MyAppName "X"' in content)
        # Tekrar damgalama idempotent olmalı
        stamp_version(fake_iss, "2.0.0")
        with open(fake_iss, encoding="utf-8") as f:
            content = f.read()
        check("tekrar damgalama çalışır", '#define MyAppVersion "2.0.0"' in content)
        # MyAppVersion satırı yoksa hata fırlatmalı
        with open(fake_iss, "w", encoding="utf-8") as f:
            f.write("#define MyAppName \"X\"\n")
        try:
            stamp_version(fake_iss, "3.0.0")
            check("eksik MyAppVersion hatası", False)
        except RuntimeError:
            check("eksik MyAppVersion hatası", True)

        # Publisher/copyright metadata merkezî sabitlerden damgalanır
        with open(fake_iss, "w", encoding="utf-8") as f:
            f.write('#define MyAppVersion "0.0.0"\n'
                    '#define MyAppPublisher "Eski"\n'
                    '#define MyAppCopyright "Eski Telif"\n')
        stamp_version(fake_iss, "1.2.3")
        with open(fake_iss, encoding="utf-8") as f:
            content = f.read()
        import versioning
        check("publisher versioning.COMPANY_NAME'den",
              f'#define MyAppPublisher "{versioning.COMPANY_NAME}"' in content)
        check("copyright versioning.LEGAL_COPYRIGHT'tan",
              f'#define MyAppCopyright "{versioning.LEGAL_COPYRIGHT}"' in content)
        # MyAppPublisher satırı yoksa da hata fırlatmalı
        with open(fake_iss, "w", encoding="utf-8") as f:
            f.write('#define MyAppVersion "0.0.0"\n')
        try:
            stamp_version(fake_iss, "3.0.0")
            check("eksik MyAppPublisher hatası", False)
        except RuntimeError:
            check("eksik MyAppPublisher hatası", True)


def test_expected_output_path():
    print("3) Çıktı yolu çözümleme")
    with tempfile.TemporaryDirectory() as tmp:
        iss = os.path.join(tmp, "a.iss")
        with open(iss, "w", encoding="utf-8") as f:
            f.write("OutputDir=Output\nOutputBaseFilename=Setup_v{#MyAppVersion}\n")
        expected = _expected_output_path(iss)
        check("göreli OutputDir çözümlenir",
              expected == os.path.join(tmp, "Output", "Setup_v{#MyAppVersion}.exe"),
              str(expected))
        # Yer tutucu sürüm parametresiyle çözümlenir
        expected = _expected_output_path(iss, version="1.2.3")
        check("yer tutucu sürümle değişir (parametre)",
              expected == os.path.join(tmp, "Output", "Setup_v1.2.3.exe"), str(expected))
        # Yer tutucu ISS #define satırından çözümlenir (--skip-version uyumlu)
        expected = _expected_output_path(iss)
        with open(iss, "w", encoding="utf-8") as f:
            f.write('#define MyAppVersion "9.9.9"\n'
                    "OutputDir=Output\nOutputBaseFilename=Setup_v{#MyAppVersion}\n")
        expected = _expected_output_path(iss)
        check("yer tutucu ISS'ten çözümlenir",
              expected == os.path.join(tmp, "Output", "Setup_v9.9.9.exe"), str(expected))
        # Parametre ISS tanımına üstün gelir
        expected = _expected_output_path(iss, version="2.0.0")
        check("parametre üstünlüğü",
              expected == os.path.join(tmp, "Output", "Setup_v2.0.0.exe"), str(expected))
        # Mutlak yol
        with open(iss, "w", encoding="utf-8") as f:
            f.write(f"OutputDir={tmp}\\out\nOutputBaseFilename=Setup\n")
        expected = _expected_output_path(iss)
        check("mutlak OutputDir çözümlenir",
              expected == os.path.join(tmp, "out", "Setup.exe"), str(expected))


def test_project_version_sync():
    print("4) Proje sürümüyle uyum")
    with open(os.path.join(os.path.dirname(ISS_PATH), "..", "build_data", "version.json"),
              encoding="utf-8") as f:
        import json
        project_version = json.load(f)["version"]
    text = read_iss()
    m = re.search(r'#define MyAppVersion "([^"]+)"', text)
    check("ISS sürüm satırı mevcut", m is not None)
    if m:
        # Not: ISS sürümü son derlemede damgalanır; proje sürümüyle eşleşmesi
        # build_installer.py çalıştırıldığında garanti edilir. Burada yalnızca
        # biçim doğrulaması yapıyoruz (semantik sürüm).
        check("ISS sürümü semantik biçimde",
              re.fullmatch(r"\d+\.\d+\.\d+", m.group(1)) is not None, m.group(1))
        print(f"  [INFO] proje sürümü: {project_version}, ISS damgası: {m.group(1)}")


def test_enterprise_doc():
    print("5) Kurumsal dağıtım kılavuzu")
    doc_path = os.path.join(
        os.path.dirname(ISS_PATH), "..", "ENTERPRISE_DEPLOYMENT.md"
    )
    check("kılavuz mevcut", os.path.isfile(doc_path), doc_path)
    if not os.path.isfile(doc_path):
        return
    with open(doc_path, encoding="utf-8") as f:
        doc = f.read()
    for token, name in [
        ("/VERYSILENT", "temel sessiz parametre"),
        ("/SUPPRESSMSGBOXES", "mesaj kutusu bastırma"),
        ("/ALLUSERS", "makine bazlı kurulum"),
        ("/CURRENTUSER", "kullanıcı bazlı kurulum"),
        ("/LOG=", "kurulum günlüğü"),
        ("/NOICONS", "kısayolsuz kurulum"),
        ("/LOADINF", "INF şablonu"),
        ("3010", "yeniden başlatma çıkış kodu"),
        ("IntuneWinAppUtil", "Intune paketleme aracı"),
        ("{6F2A9C41-8B7D-4E63-9A15-3C2B7A91D8E4}", "AppId tutarlılığı (ISS ile aynı)")
    ]:
        check(f"kılavuzda {name}", token in doc)
    # AppId ISS ile kılavuz arasında birebir aynı olmalı
    iss_text = read_iss()
    m = re.search(r"AppId=\{\{([0-9A-Fa-f-]+)\}", iss_text)
    if m:
        check("AppId kılavuz-ISS tutarlı", "{%s}" % m.group(1) in doc,
              "ISS: {%s}" % m.group(1))


def test_find_iscc_graceful():
    print("6) ISCC bulucu güvenli davranış")
    result = find_iscc()
    # Kurulu olmayabilir — önemli olan çökmemesi ve None/yol döndürmesi
    check("bulucu çökmeden döner", result is None or os.path.isfile(result), str(result))
    if result is None:
        print("  [INFO] ISCC kurulu değil; statik testler yine de geçer")


def main():
    test_iss_structure()
    test_version_stamp()
    test_expected_output_path()
    test_enterprise_doc()
    test_project_version_sync()
    test_find_iscc_graceful()

    passed = PASS - len(FAIL)
    print(f"\nSONUC: {passed}/{PASS} gecti, {len(FAIL)} basarisiz")
    for f in FAIL:
        print("  FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
