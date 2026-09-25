"""
tools/clean_dist.py için birim ve fonksiyonel testler (gerçek derleme
dizinlerine dokunmaz; tüm dizinler geçici olarak taklit edilir).

Çalıştırma:  python tests/test_clean_dist.py
"""
import hashlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools.clean_dist as cd  # noqa: E402

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


def content_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# Test başındaki gerçek proje dizinlerinin varlık durumu (dokunulmazlık karşılaştırması)
_REAL_STATE = {name: os.path.isdir(getattr(cd, name))
               for name in ("RELEASE_DIR", "UPDATES_DIR", "INSTALLER_DIR",
                            "ARCHIVE_DIR")}
# Gerçek staging klasörleri (gh_release_*) — test sonunda da durmalı
_REAL_STAGING = {d: os.path.isdir(d) for d in cd.staging_dirs()}


def test_version_of():
    print("1) Sürüm tespiti (dosya adı kalıbı)")
    check("taşınabilir exe", cd.version_of("MERA_BIS_PRO_v1.2.1.exe") == "1.2.1")
    check("updates zip", cd.version_of("MERA_BIS_PRO_1.2.4.zip") == "1.2.4")
    check("setup exe", cd.version_of("MERA_BIS_PRO_Setup_v1.2.3.exe") == "1.2.3")
    check("sürümsüz exe -> None", cd.version_of("random_tool.exe") is None)
    check("sürümsüz uzantı -> None", cd.version_of("notes.txt") is None)


def test_plan_and_apply():
    print("2) Plan + uygulama (geçici dizinlerde)")
    with tempfile.TemporaryDirectory() as root:
        saved = {k: getattr(cd, k) for k in
                 ("PROJECT_ROOT", "ARCHIVE_DIR", "DIST_DIR", "RELEASE_DIR",
                  "UPDATES_DIR", "INSTALLER_DIR", "BUILD_DIR")}
        try:
            release = os.path.join(root, "dist", "release")
            updates = os.path.join(root, "updates")
            outp = os.path.join(root, "installer", "Output")
            build = os.path.join(root, "build", "MERA_BIS_PRO")
            archive = os.path.join(root, "archive")
            for d in (release, updates, outp, build):
                os.makedirs(d, exist_ok=True)
            cd.PROJECT_ROOT = root
            cd.ARCHIVE_DIR = archive
            cd.DIST_DIR = os.path.join(root, "dist")
            cd.RELEASE_DIR = release
            cd.UPDATES_DIR = updates
            cd.INSTALLER_DIR = outp
            cd.BUILD_DIR = build

            # build_data/version.json -> güncel sürüm 1.2.4
            os.makedirs(os.path.join(root, "build_data"), exist_ok=True)
            with open(os.path.join(root, "build_data", "version.json"), "w",
                      encoding="utf-8") as f:
                f.write('{"version": "1.2.4"}')

            def w(path, data=b"x" * 1024):
                with open(path, "wb") as f:
                    f.write(data)

            w(os.path.join(release, "MERA_BIS_PRO_v1.2.1.exe"))
            w(os.path.join(release, "MERA_BIS_PRO_v1.2.4.exe"))
            w(os.path.join(release, "sürümsüz_arac.exe"))
            # GitHub Release staging klasörleri (koruma testi için)
            staging1 = os.path.join(release, "gh_release_v1.2.1")
            staging4 = os.path.join(release, "gh_release_v1.2.4")
            os.makedirs(os.path.join(staging1, "alt"), exist_ok=True)
            os.makedirs(staging4, exist_ok=True)
            w(os.path.join(staging1, "MERA_BIS_PRO_v1.2.1.exe"))
            w(os.path.join(staging1, "SHA256SUMS_v1.2.1.txt"))
            w(os.path.join(staging1, "alt", "RELEASE_NOTES.md"))
            w(os.path.join(staging4, "MERA_BIS_PRO_v1.2.4.exe"))
            w(os.path.join(updates, "MERA_BIS_PRO_1.2.1.zip"))
            w(os.path.join(updates, "manifest.json"), b'{"version": "1.2.4"}')
            w(os.path.join(outp, "MERA_BIS_PRO_Setup_v1.2.3.exe"))
            w(os.path.join(build, "proj.toc"))

            # --- scan ---
            info = cd.scan()
            check("scan sürümleri", set(info["versions"]) == {"1.2.1", "1.2.3", "1.2.4"},
                  str(set(info["versions"])))
            check("manifest taranmadı",
                  all(os.path.basename(p) != "manifest.json"
                      for ps in info["versions"].values() for p in ps))
            check("sürümsüz algılandı", len(info["unversioned"]) == 1)
            check("güncel sürüm okundu", info["current"] == "1.2.4")
            check("staging klasörleri taranmadı (scan yüzeysel)",
                  all("gh_release_" not in p
                      for ps in info["versions"].values() for p in ps))

            # --- plan (varsayılan) ---
            planned = cd.plan()
            kinds = [a for a, _t, _v in planned["actions"]]
            check("arşiv aksiyon sayısı (2.2.1 exe+zip, 1.2.3 setup)",
                  kinds.count("archive") == 3, str(kinds))
            check("build silme aksiyonu", kinds.count("delete_dir") == 1)
            # Staging koruması: ne arşiv ne silme hedefi staging olamaz
            staging_paths = [os.path.join(release, "gh_release_v1.2.1"),
                             os.path.join(release, "gh_release_v1.2.4")]
            check("plan staging'e arşiv/silme aksiyonu ÜRETMEZ",
                  all(not any(str(t).startswith(s) for a, t, _v in planned["actions"]
                              if a in ("archive", "delete_dir", "purge"))
                      for s in staging_paths))
            check("güncel sürüm arşivlenmez",
                  all("1.2.4" not in os.path.basename(t)
                      for a, t, _v in planned["actions"] if a == "archive"))
            check("istatistik boyut > 0", planned["stats"]["archive_bytes"] > 0)

            # --- plan keep ---
            planned_keep = cd.plan(keep={"1.2.3"})
            kept = [os.path.basename(t) for a, t, _v in planned_keep["actions"]
                    if a == "archive"]
            check("keep koruması", kept == ["MERA_BIS_PRO_v1.2.1.exe",
                                            "MERA_BIS_PRO_1.2.1.zip"], str(kept))

            # --- plan current_override ---
            planned_cur = cd.plan(current_override="1.2.1")
            cur_arch = sorted(os.path.basename(t) for a, t, _v in planned_cur["actions"]
                              if a == "archive")
            check("current_override: 1.2.1 durur, diğerleri arşivlenir",
                  cur_arch == ["MERA_BIS_PRO_Setup_v1.2.3.exe",
                               "MERA_BIS_PRO_v1.2.4.exe"], str(cur_arch))

            # --- apply ---
            before_hash = content_hash(os.path.join(release, "MERA_BIS_PRO_v1.2.1.exe"))
            done = cd.apply(planned)
            check("3 dosya arşivlendi", done["archived"] == 3)
            check("build klasörü silindi",
                  done["build_removed"] and not os.path.isdir(build))
            a121 = os.path.join(archive, "v1.2.1", "MERA_BIS_PRO_v1.2.1.exe")
            a123 = os.path.join(archive, "v1.2.3", "MERA_BIS_PRO_Setup_v1.2.3.exe")
            check("v1.2.1 exe arşivde", os.path.isfile(a121))
            check("v1.2.3 setup arşivde", os.path.isfile(a123))
            # Staging apply-değişmezliği: uygulama sonrası içerik yerinde
            check("staging apply sonrası yerinde",
                  os.path.isfile(os.path.join(staging1, "MERA_BIS_PRO_v1.2.1.exe"))
                  and os.path.isfile(os.path.join(staging1, "alt", "RELEASE_NOTES.md"))
                  and os.path.isfile(os.path.join(staging4, "MERA_BIS_PRO_v1.2.4.exe")))
            check("arşiv içerik birebir", content_hash(a121) == before_hash)
            check("kaynaktan kalktı", not os.path.exists(
                os.path.join(release, "MERA_BIS_PRO_v1.2.1.exe")))
            check("manifest yerinde", os.path.isfile(
                os.path.join(updates, "manifest.json")))
            check("güncel exe yerinde", os.path.isfile(
                os.path.join(release, "MERA_BIS_PRO_v1.2.4.exe")))
            sums = os.path.join(archive, "v1.2.1", "SHA256SUMS.txt")
            check("SHA256SUMS yazıldı", os.path.isfile(sums))
            if os.path.isfile(sums):
                with open(sums, "rb") as f:
                    raw = f.read()
                check("SHA256SUMS LF satır sonu (CRLF yok)", b"\r\n" not in raw)
                lines = [l for l in raw.decode("utf-8").splitlines() if l.strip()]
                expected = [cd.sha256_of(os.path.join(archive, "v1.2.1", l.split("  ")[1]))
                            for l in lines]
                check("SHA256SUMS hash'leri doğru",
                      [l.split("  ")[0] for l in lines] == expected)

            # --- purge ---
            planned_purge = cd.plan(purge_archive=["1.2.3"])
            check("purge aksiyonu", any(a == "purge" for a, _t, _v in
                                        planned_purge["actions"]))
            cd.apply(planned_purge, write_checksums=False)
            check("v1.2.3 arşivi silindi", not os.path.isdir(
                os.path.join(archive, "v1.2.3")))
            check("v1.2.1 arşivi duruyor", os.path.isdir(
                os.path.join(archive, "v1.2.1")))
            check("var olmayan purge güvenli", cd.plan(
                purge_archive=["9.9.9"]) is not None)
        finally:
            for k, v in saved.items():
                setattr(cd, k, v)
    # Gerçek proje dizinleri dokunulmadan kaldı mı?
    # (test başındaki varlık durumuyla karşılaştırılır — dizin harici olarak
    #  silinmişse test bunu başarısızlık sayamaz)
    for name, existed in _REAL_STATE.items():
        check(f"gerçek {name} dokunulmadı ({'var' if existed else 'yok'})",
              os.path.isdir(getattr(cd, name)) == existed)
    for d, existed in _REAL_STAGING.items():
        check(f"gerçek staging korundu ({os.path.basename(d)})",
              os.path.isdir(d) == existed)


def _tree_snapshot(dirs):
    """Dizin ağaçlarının (yol -> boyut) haritası; dry-run değişmezlik denetimi için."""
    snap = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for r, _ds, fs in os.walk(d):
            for f in fs:
                p = os.path.join(r, f)
                try:
                    snap[p] = os.path.getsize(p)
                except OSError:
                    pass
    return snap


def test_real_project_dry_run():
    print("3) Gerçek proje dry-run (dokunma garantisi)")
    before = _tree_snapshot([cd.RELEASE_DIR, cd.UPDATES_DIR, cd.INSTALLER_DIR,
                             cd.ARCHIVE_DIR])
    planned = cd.plan()
    cur = planned["current"]
    check("güncel sürüm okundu", bool(cur), str(cur))
    after = _tree_snapshot([cd.RELEASE_DIR, cd.UPDATES_DIR, cd.INSTALLER_DIR,
                            cd.ARCHIVE_DIR])
    check("dry-run dosyaya dokunmaz", before == after,
          "plan() çağrısı dosya ağacını değiştirdi")
    archive_hits = [os.path.basename(t) for a, t, v in planned["actions"]
                    if a == "archive" and v == cur]
    check("güncel sürüm plana girmedi", archive_hits == [], str(archive_hits))


def main():
    test_version_of()
    test_plan_and_apply()
    test_real_project_dry_run()
    passed = PASS - len(FAIL)
    print(f"\nSONUC: {passed}/{PASS} gecti, {len(FAIL)} basarisiz")
    for f in FAIL:
        print("  FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
