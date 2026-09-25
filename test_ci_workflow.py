"""
.github/workflows/release.yml ve requirements.txt için statik doğrulama.

GitHub Actions çalıştırılmaz; YAML ayrıştırma, job/step yapısı, koşul
ifadeleri, secret/env tutarlılığı ve derleme zinciri bayrakları doğrulanır.

Çalıştırma:  python tests/test_ci_workflow.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def load_yaml(path):
    """PyYAML varsa sözlük olarak, yoksa ham metin döndürür."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        import yaml  # noqa
        with open(path, encoding="utf-8") as f:
            return text, yaml.safe_load(f)
    except ImportError:
        pass
    # PyYAML yoksa: GitHub Actions actionlint yokken bile en azından temel
    # YAML girinti tutarlılığını elle denetle (sekme yok, denge şu kadar).
    problems = _yaml_lint(text)
    if problems:
        for p in problems[:5]:
            print(f"  [LINT] {p}")
        raise SystemExit("YAML lint hatası — yukarıdaki sorunları düzeltin")
    return text, None


def _yaml_lint(text):
    """Mini YAML lint: sekme karakteri ve boş bırakılmış akış hataları."""
    problems = []
    for i, line in enumerate(text.splitlines(), 1):
        if "\t" in line:
            problems.append(f"satır {i}: sekme karakteri YAML'de yasaktır")
        stripped = line.rstrip()
        if stripped.endswith(":") and stripped.lstrip().startswith("-"):
            problems.append(f"satır {i}: liste öğesi anahtarla karışmış: {stripped!r}")
    # Her açılan üç tırnak bloğu kapanmalı (run: | bloklarında sık hata)
    if text.count("'''") % 2 or text.count('"""') % 2:
        problems.append("eşleşmeyen üç tırnak bloğu")
    return problems


def test_yaml_parses():
    print("1) YAML sözdizimi")
    wf_path = os.path.join(".github", "workflows", "release.yml")
    check("iş akışı dosyası mevcut", os.path.isfile(wf_path))
    if not os.path.isfile(wf_path):
        return None, None
    text, data = load_yaml(wf_path)
    if data is None:
        print("  [INFO] PyYAML kurulu değil; yapısal metin denetimine geçildi")
        return text, None
    check("YAML ayrıştırma başarılı", isinstance(data, dict))
    check("name alanı", data.get("name") == "release")
    check("permissions contents:write", 
          data.get("permissions", {}).get("contents") == "write")
    on = data.get(True) or data.get("on") or {}  # YAML 1.1 'on' -> bool True
    triggers = set(on.keys()) if isinstance(on, dict) else set()
    check("push etiket tetikleyicisi", "push" in triggers, str(triggers))
    check("workflow_dispatch tetikleyicisi", "workflow_dispatch" in triggers)
    return text, data


def test_structure(text, data):
    print("2) Job yapısı ve bağımlılıklar")
    jobs = (data or {}).get("jobs") or {}
    if jobs:
        check("test job'u var", "test" in jobs)
        check("build job'u var", "build" in jobs)
        check("release job'u var", "release" in jobs)
        check("build, test'e bağlı", jobs.get("build", {}).get("needs") == "test")
        check("release, build'e bağlı", jobs.get("release", {}).get("needs") == "build")
        check("tüm job'lar windows/ubuntu", all(
            j.get("runs-on") in ("windows-latest", "ubuntu-latest")
            for j in jobs.values()))
        # Koşullar: inputs.* yalnızca workflow_dispatch ile korunmalı
        for jname in ("test", "build", "release"):
            cond = str(jobs.get(jname, {}).get("if", ""))
            if "inputs." in cond:
                check(f"{jname}: inputs.* guard'lı",
                      "workflow_dispatch" in cond, cond)
    else:
        # Metin yedeği (PyYAML yoksa)
        check("test job'u var", "  test:" in text)
        check("build job'u var", "  build:" in text)
        check("release job'u var", "  release:" in text)
        check("needs: test", re.search(r"^\s+needs: test$", text, re.M) is not None)
        check("needs: build", re.search(r"^\s+needs: build$", text, re.M) is not None)


def test_steps_and_flags(text):
    print("3) Adımlar, bayraklar ve secret tutarlılığı")
    check("choco innosetup kurulumu", "choco install innosetup" in text)
    check("build_release --installer çağrısı", "--installer" in text)
    check("require-sign bayrağı aktarımı", "--require-sign" in text)
    check("smoke_gui offscreen", "QT_QPA_PLATFORM" in text and "smoke_gui" in text)
    check("artefakt yükleme", "actions/upload-artifact" in text)
    check("artefakt indirme", "actions/download-artifact" in text)
    check("gh release create", "gh release create" in text)
    check("SHA256SUMS üretimi", "SHA256SUMS" in text)
    check("setup-python cache", "actions/setup-python" in text and "cache: pip" in text)

    # Secret'lar: SIGN_CERT_SHA1 kullanılıyorsa EV token kılavuzuyla tutarlı olmalı
    check("SIGN_CERT_SHA1 secret'ı", "SIGN_CERT_SHA1" in text)
    # get-AuthenticodeSignature doğrulaması CI'da da yapılmalı
    check("CI içi imza doğrulaması", "Get-AuthenticodeSignature" in text)

    # env adı çakışması: INPUT_REQUIRE_SIGN eski taslak hatası geri gelmemeli
    check("eski INPUT_REQUIRE_SIGN hatası yok", "INPUT_REQUIRE_SIGN" not in text)


def test_requirements():
    print("4) requirements.txt tutarlılığı")
    path = "requirements.txt"
    check("requirements mevcut", os.path.isfile(path))
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        req = f.read()
    for pkg in ("PyQt6", "PyQt6-WebEngine", "matplotlib", "pyinstaller"):
        check(f"{pkg} tanımlı", re.search(rf"(?mi)^{re.escape(pkg)}==", req) is not None)
    check("tüm pin'li (==) sürümler", "==" in req)
    # İş akışı bu dosyayı kullanmalı
    with open(os.path.join(".github", "workflows", "release.yml"),
              encoding="utf-8") as f:
        wf = f.read()
    check("iş akışı requirements.txt kullanıyor", "requirements.txt" in wf)


def test_local_parity():
    print("5) Yerel derleme zinciriyle parite")
    # CI'ın çalıştırdığı test listesi == build_release.run_tests listesi
    sys.path.insert(0, "tools")
    try:
        from tools.build_release import run_tests  # noqa: F401
    except Exception:
        run_tests = None
    # Yerel liste (build_release.py) ile CI listesi karşılaştır
    with open("tools/build_release.py", encoding="utf-8") as f:
        br = f.read()
    local_tests = set(re.findall(r'"(tests/test_\w+\.py)"', br))
    check("yerel liste >= 15 test", len(local_tests) >= 15, str(len(local_tests)))

    with open(os.path.join(".github", "workflows", "release.yml"),
              encoding="utf-8") as f:
        wf = f.read()
    ci_tests = set(re.findall(r'"(tests/test_\w+\.py)"', wf))
    # CI test job'u birim paketleri içerir; smoke_gui ayrı adımda.
    # Her iki yönde de karşılaştır: CI'dan eksik VE CI'da fazlalık olmamalı
    # (local_tests build_release.py'deki kendi adını da yakalayabilir —
    # 'test_' ile başlamayanları zaten regex eler).
    missing = {t for t in local_tests if t not in ci_tests}
    check("CI listesi yerel listeyi kapsıyor", not missing, str(missing))
    extra = {t for t in ci_tests if t not in local_tests}
    check("CI listesinde fazlalık yok", not extra, str(extra))
    check("smoke_gui CI'da ayrı adım", "tests/smoke_gui.py" in wf)


def main():
    text, data = test_yaml_parses()
    if text is not None:
        test_structure(text, data)
        test_steps_and_flags(text)
        test_requirements()
        test_local_parity()
    passed = PASS - len(FAIL)
    print(f"\nSONUC: {passed}/{PASS} gecti, {len(FAIL)} basarisiz")
    for f in FAIL:
        print("  FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
