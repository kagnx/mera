#!/usr/bin/env python3
"""
MERA-BİS PRO — CHANGELOG.md için otomatik sürüm bölümü üretimi.

Son `v*` etiketinden bu yana commit geçmişini okur, Keep a Changelog
biçiminde yeni sürüm bölümü üretir ve CHANGELOG.md'nin başına ekler.

## Kategorilendirme (conventional commits)

| Önek (büyük/küçük harf duyarsız) | Bölüm |
|----------------------------------|-------|
| feat / feature / add             | Eklendi |
| fix / bugfix / hotfix            | Düzeltildi |
| change / changed / refactor      | Değişti |
| perf                             | Performans |
| security                         | Güvenlik |
| deprecated                       | Kullanımdan kaldırıldı |
| removed                          | Kaldırıldı |
| docs                             | Belgelendirme |
| test / chore / ci / build        | Bakım |
| (önek yok)                       | Değişti |

## Kullanım

    python tools/gen_changelog.py                 # plan (dry-run)
    python tools/gen_changelog.py --apply         # CHANGELOG.md'ye yaz
    python tools/gen_changelog.py --version 1.3.0 # sürümü elle sabitle
    python tools/gen_changelog.py --from v1.2.0   # başlangıç etiketi

## Derleme entegrasyonu

`build_release.py` her derlemede (bayrak verilmezse) yeni sürüm için bölüm
üretir. Git deposu/etiket yoksa uyarı verip derlemeyi bozmadan geçer.

NOT: Bu çalışma klasörü git deposu olmadığından yerelde etiket araması
boş döner; CI'da (actions/checkout fetch-depth: 0) tam geçmiş okunur.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG_PATH = os.path.join(PROJECT_ROOT, "CHANGELOG.md")

CATEGORY_ORDER = [
    "Eklendi", "Düzeltildi", "Değişti", "Performans", "Güvenlik",
    "Kullanımdan kaldırıldı", "Kaldırıldı", "Belgelendirme", "Bakım",
]
CATEGORY_MAP = {
    "feat": "Eklendi", "feature": "Eklendi", "add": "Eklendi",
    "fix": "Düzeltildi", "bugfix": "Düzeltildi", "hotfix": "Düzeltildi",
    "change": "Değişti", "changed": "Değişti", "refactor": "Değişti",
    "perf": "Performans",
    "security": "Güvenlik",
    "deprecated": "Kullanımdan kaldırıldı",
    "removed": "Kaldırıldı",
    "docs": "Belgelendirme",
    "test": "Bakım", "chore": "Bakım", "ci": "Bakım", "build": "Bakım",
}
_COMMIT_RE = re.compile(
    r"^(?P<prefix>[a-zA-Z]+)(?:\([^)]*\))?!?:\s*(?P<rest>.+)$"
)


def _run_git(args, cwd=PROJECT_ROOT):
    """git komutunu çalıştırır; başarısızlıkta None döner (yok sayılır)."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        r = subprocess.run([git] + args, cwd=cwd, capture_output=True,
                           text=True, errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip()


def is_git_repo(cwd=PROJECT_ROOT):
    return _run_git(["rev-parse", "--is-inside-work-tree"], cwd=cwd) == "true"


def get_last_tag(cwd=PROJECT_ROOT):
    """Son v* etiketini döndürür; yoksa/depo yoksa None."""
    out = _run_git(["tag", "--list", "v*", "--sort=-creatordate"], cwd=cwd)
    if not out:
        return None
    return out.splitlines()[0].strip()


def commits_since(tag=None, cwd=PROJECT_ROOT):
    """Etiketten bu yana (hash, subject) listesi; en yeniden eskiye.

    tag None ise tüm geçmiş. Merge commit'leri atlanır.
    Depo yoksa GitUnavailable hatası fırlatır.
    """
    if not is_git_repo(cwd):
        raise GitUnavailable("git deposu değil (yerel klasör) — changelog atlandı")
    args = ["log", "--no-merges", "--pretty=format:%h%x09%s"]
    if tag:
        args.append(f"{tag}..HEAD")
    out = _run_git(args, cwd=cwd)
    if out is None:
        raise GitUnavailable("git log başarısız")
    commits = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        h, subject = line.split("\t", 1)
        if subject.strip():
            commits.append((h.strip(), subject.strip()))
    return commits


class GitUnavailable(RuntimeError):
    pass


def categorize(subject):
    """Commit başlığını (kategori, temiz başlık) ikilisine çevirir."""
    m = _COMMIT_RE.match(subject)
    if not m:
        return "Değişti", subject.strip()
    prefix = m.group("prefix").lower()
    rest = m.group("rest").strip()
    category = CATEGORY_MAP.get(prefix, "Değişti")
    return category, rest or subject.strip()


def render_section(version, entries, day=None):
    """Keep a Changelog bölümü üretir; boş kategoriler atlanır."""
    day = day or date.today().isoformat()
    lines = [f"## [{version}] — {day}", ""]
    for cat in CATEGORY_ORDER:
        items = entries.get(cat) or []
        if not items:
            continue
        lines.append(f"### {cat}")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def build_section(version, commits, day=None):
    """(hash, subject) listesinden sürüm bölümü üretir."""
    entries = {}
    for h, subject in commits:
        cat, clean = categorize(subject)
        entries.setdefault(cat, []).append(f"{clean} ({h})")
    return render_section(version, entries, day=day)


def insert_section(changelog_path, section, version):
    """Bölümü CHANGELOG'a ekler; zaten varsa False (idempotent), yoksa True.

    Yerleşim: başlık/giriş paragrafından sonra, ilk `## [` satırının hemen
    üstü. Hiç sürüm bölümü yoksa dosya sonuna eklenir.
    """
    with open(changelog_path, encoding="utf-8") as f:
        text = f.read()
    marker = f"## [{version}]"
    if marker in text:
        return False
    m = re.search(r"^## \[", text, re.M)
    if m:
        text = text[:m.start()] + section + "\n" + text[m.start():]
    else:
        text = text.rstrip("\n") + "\n\n" + section
    with open(changelog_path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return True


def read_version():
    try:
        with open(os.path.join(PROJECT_ROOT, "build_data", "version.json"),
                  encoding="utf-8") as f:
            return json.load(f).get("version")
    except (OSError, ValueError):
        return None


def generate(version=None, from_tag=None, apply=False, changelog_path=None):
    """Üretim akışı: (bölüm_metni, dosyaya_yazıldı) döner.

    Git yoksa GitUnavailable fırlatır (çağıran uyarı verip geçer).
    """
    version = version or read_version()
    if not version:
        raise RuntimeError("sürüm belirsiz (build_data/version.json okunamadı)")
    tag = from_tag or get_last_tag()
    commits = commits_since(tag)
    if not commits:
        raise GitUnavailable(f"{'etiketten ' + tag + ' beri ' if tag else ''}commit yok")
    section = build_section(version, commits)
    if not apply:
        return section, False
    path = changelog_path or CHANGELOG_PATH
    written = insert_section(path, section, version)
    return section, written


def main():
    ap = argparse.ArgumentParser(description="Otomatik changelog üretimi")
    ap.add_argument("--version", help="Sürüm (varsayılan: build_data/version.json)")
    ap.add_argument("--from", dest="from_tag", help="Başlangıç etiketi (varsayılan: son v* etiketi)")
    ap.add_argument("--apply", action="store_true", help="CHANGELOG.md'ye yaz (yoksa yalnız göster)")
    args = ap.parse_args()

    try:
        section, written = generate(version=args.version,
                                    from_tag=args.from_tag, apply=args.apply)
    except GitUnavailable as exc:
        print(f"[changelog] UYARI: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"[changelog] HATA: {exc}")
        return 1

    print(section)
    if args.apply:
        print(f"[changelog] {'Eklendi' if written else 'Zaten mevcut — atlandı'}: {CHANGELOG_PATH}")
    else:
        print("[changelog] Dry-run: yazılmadı (--apply ile yaz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
