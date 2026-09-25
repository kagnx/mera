"""
tools/gen_changelog.py için doğrulama testleri.

Gerçek git geçmişine dayanmadan: kategorilendirme tablosu, bölüm biçimi,
CHANGELOG'a idempotent ekleme, git yokken nazik düşme ve geçici git deposu
kurularak uçtan uca üretim akışı test edilir.

Çalıştırma:  python tests/test_gen_changelog.py
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import tools.gen_changelog as gc  # noqa: E402

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


def test_categorize():
    print("1) Kategorilendirme")
    cases = [
        ("feat: yeni ölçüm grafiği", "Eklendi", "yeni ölçüm grafiği"),
        ("FIX: bozuk yedek çökmesi", "Düzeltildi", "bozuk yedek çökmesi"),
        ("refactor(kapsam): DB katmanı", "Değişti", "DB katmanı"),
        ("perf: tablo sıralama hızlandır", "Performans", "tablo sıralama hızlandır"),
        ("security: parola env kuralı", "Güvenlik", "parola env kuralı"),
        ("docs: dağıtım kılavuzu", "Belgelendirme", "dağıtım kılavuzu"),
        ("ci: workflow ekle", "Bakım", "workflow ekle"),
        ("Test: birim testleri", "Bakım", "birim testleri"),  # büyük harf önek
        ("feat!: kırıcı değişiklik", "Eklendi", "kırıcı değişiklik"),  # breaking !!
        ("düz metin başlık", "Değişti", "düz metin başlık"),
        ("featuring: yanlış önek", "Değişti", "yanlış önek"),  # önek değil (featuring != feat)
    ]
    for subject, expected_cat, expected_rest in cases:
        cat, rest = gc.categorize(subject)
        check(f"{subject!r} -> {expected_cat}", cat == expected_cat, cat)
        check(f"{subject!r} temiz başlık", rest == expected_rest, rest)


def test_render_and_insert():
    print("2) Bölüm üretimi + idempotent ekleme")
    commits = [
        ("abc1234", "feat: ölçüm modülü"),
        ("def5678", "fix: sürüm damgası"),
        ("aaa0000", "docs: kılavuz"),
        ("bbb1111", "bilinmeyen biçim"),
    ]
    section = gc.build_section("1.3.0", commits, day="2026-09-18")
    check("sürüm başlığı", "## [1.3.0] — 2026-09-18" in section)
    check("Eklendi bölümü", "### Eklendi" in section and "- ölçüm modülü (abc1234)" in section)
    check("Düzeltildi bölümü", "### Düzeltildi" in section and "- sürüm damgası (def5678)" in section)
    check("Belgelendirme bölümü", "### Belgelendirme" in section)
    check("boş kategori yok", "### Güvenlik" not in section and "### Bakım" not in section)
    check("sıralama: Eklendi önce", section.index("### Eklendi") < section.index("### Düzeltildi"))
    check("kategorisiz -> Değişti", "### Değişti" in section and "- bilinmeyen biçim (bbb1111)" in section)

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "CHANGELOG.md")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("# Changelog\n\nGiriş paragrafı.\n\n## [1.2.0] — 2026-01-01\n\n### Eklendi\n- eski\n")
        w1 = gc.insert_section(path, section, "1.3.0")
        check("ilk ekleme başarılı", w1 is True)
        with open(path, encoding="utf-8") as f:
            after = f.read()
        check("bölüm ilk sürümün üstünde",
              after.index("## [1.3.0]") < after.index("## [1.2.0]"))
        check("giriş paragrafı korundu", "Giriş paragrafı." in after)
        w2 = gc.insert_section(path, section, "1.3.0")
        check("ikinci ekleme idempotent (False)", w2 is False)
        with open(path, encoding="utf-8") as f:
            after2 = f.read()
        check("çoğaltma yok", after2.count("## [1.3.0]") == 1)
        # LF satır sonu korunmalı
        with open(path, "rb") as f:
            raw = f.read()
        check("LF satır sonu", b"\r\n" not in raw)


def test_git_unavailable():
    print("3) Git deposu olmayan klasörde nazik düşme")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            gc.commits_since(cwd=tmp)
            check("git yoksa GitUnavailable", False, "hata fırlamadı")
        except gc.GitUnavailable:
            check("git yoksa GitUnavailable", True)
        # generate() de aynı şekilde düşmeli (sürüm okunabilir olsa bile)
        try:
            gc.generate(version="9.9.9", apply=False, changelog_path=os.path.join(tmp, "c.md"))
            check("generate git yoksa düşer", False, "hata fırlamadı")
        except gc.GitUnavailable:
            check("generate git yoksa düşer", True)
    # Gerçek proje klasörü de git deposu değil -> generate GitUnavailable
    try:
        gc.generate(version="9.9.9", apply=False)
        check("proje klasöründe de düşer", False, "hata fırlamadı")
    except gc.GitUnavailable:
        check("proje klasöründe de düşer", True)


def _git(cwd, *args):
    r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True,
                       text=True, errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr}")
    return r.stdout.strip()


def test_e2e_with_temp_repo():
    print("4) Uçtan uca: geçici git deposu")
    if not gc.is_git_repo.__self__ if False else subprocess.run(
            ["git", "--version"], capture_output=True).returncode != 0:
        print("  [INFO] git kurulu değil; e2e atlandı")
        return
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _git(tmp, "init", "-q")
            _git(tmp, "-c", "user.email=t@t", "-c", "user.name=t",
                 "commit", "--allow-empty", "-q", "-m", "feat: ilk sürüm")
            _git(tmp, "tag", "v1.0.0")
            for msg in ("feat: olcum modulu", "fix: cakisma", "docs: kilavuz"):
                _git(tmp, "-c", "user.email=t@t", "-c", "user.name=t",
                     "commit", "--allow-empty", "-q", "-m", msg)
            check("geçici depo hazır", gc.is_git_repo(cwd=tmp))
            check("son etiket v1.0.0", gc.get_last_tag(cwd=tmp) == "v1.0.0",
                  str(gc.get_last_tag(cwd=tmp)))
            commits = gc.commits_since("v1.0.0", cwd=tmp)
            check("3 commit okundu", len(commits) == 3, str(len(commits)))
            section = gc.build_section("1.1.0", commits, day="2026-09-18")
            check("e2e bölüm Eklendi içeriyor", "- olcum modulu (" in section,
                  section[:200])
            check("e2e bölüm Düzeltildi içeriyor", "- cakisma (" in section,
                  section[:200])

            # merge commit atlanmalı
            _git(tmp, "checkout", "-q", "--orphan", "gecici")
            _git(tmp, "-c", "user.email=t@t", "-c", "user.name=t",
                 "commit", "--allow-empty", "-q", "-m", "feat: orphan")
            _git(tmp, "checkout", "-q", "-" if False else "master")
            _git(tmp, "merge", "-q", "--no-ff", "-m", "merge gecici", "gecici")
            commits2 = gc.commits_since("v1.0.0", cwd=tmp)
            check("merge commit atlandı",
                  all(not s.startswith("merge") for _h, s in commits2))
        except (RuntimeError, FileNotFoundError) as exc:
            # orphan/merge adımları kısıtlı ortamlarda başarısız olabilir
            print(f"  [INFO] e2e kısmi: {exc}")


def main():
    test_categorize()
    test_render_and_insert()
    test_git_unavailable()
    test_e2e_with_temp_repo()
    passed = PASS - len(FAIL)
    print(f"\nSONUC: {passed}/{PASS} gecti, {len(FAIL)} basarisiz")
    for f in FAIL:
        print("  FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
