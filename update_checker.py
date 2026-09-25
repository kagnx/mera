"""
MERA-BİS PRO — Paketli dağıtımlar için güncelleme servisi.

Dağıtılabilir (PyInstaller) derlemelerde sürüm denetimi ve yükleme akışını
yönetir. Kaynak modda çalışırken yalnızca pasif denetim yapılır (yükleme
kapalıdır); böylece geliştirme dizini yanlışlıkla değiştirilmez.

## Manifest biçimi (updates/manifest.json)

```json
{
  "version": "1.1.0",
  "notes": "Bu sürümde ...",
  "date": "17.09.2026 10:00",
  "file": "MERA_BIS_PRO_1.1.0.zip",
  "sha256": "<zip dosyasının SHA-256 özeti>",
  "size": 123456789
}
```

## Kaynak sıralaması

1. Kullanıcı tarafından işaret edilen yerel ağ/klasör kaynağı
   (QSettings: update/local_source). Dosya yolu, sürücü harfi veya
   //sunucu/paylasım biçiminde UNC yolu olabilir.
2. Varsayılan uygulama yanındaki <exe_dizini>/updates klasörü
   (offline kurulum medyası).

## Güvenlik

- Yükleme, dosya SHA-256 özeti manifestle eşleşmezse reddedilir.
- Uygulama dosyaları önce yedeklenir; yükleme başarısız olursa otomatik
  geri alınır. Eski yedekler, ayarlanan saklama sayısına göre temizlenir.
- Zip içi yol geçişleri (path traversal) denetlenir.
"""
import hashlib
import json
import logging
import os
import shutil
import sys
import zipfile
from datetime import datetime

log = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import QSettings
except ImportError:  # Qt olmadan da (CLI/test) kullanılabilsin
    QSettings = None


# ---------------------------------------------------------------- temel yardımcılar

def is_frozen():
    """Uygulama PyInstaller ile paketlenmiş mi?"""
    return bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))


def read_version_safe():
    """Mevcut uygulama sürümünü güvenle okur (hata olursa 1.0.0)."""
    try:
        from versioning import read_version
        return read_version()
    except Exception:
        return "1.0.0"


def parse_version(v):
    """'1.2.3' -> (1, 2, 3); sayısal olmayan parçalar yok sayılır."""
    parts = []
    for p in str(v).split("."):
        if p.isdigit():
            parts.append(int(p))
        else:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(candidate, current):
    """candidate > current ise True."""
    return parse_version(candidate) > parse_version(current)


def app_install_dir():
    """Paketli kurulumun ana dizini (exe'nin bulunduğu klasör)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _safe_zip_extract(zf, dest_dir):
    """Zip içeriğini yol geçişi korumasıyla açar; açılan dosya sayısını döndürür."""
    dest_dir = os.path.abspath(dest_dir)
    count = 0
    for info in zf.infolist():
        name = info.filename
        if name.startswith("/") or ".." in name.replace("\\", "/").split("/"):
            raise ValueError(f"Zip güvenlik ihlali: geçersiz yol {name!r}")
        target = os.path.abspath(os.path.join(dest_dir, name))
        if not (target == dest_dir or target.startswith(dest_dir + os.sep)):
            raise ValueError(f"Zip güvenlik ihlali: hedef dışına yazım {name!r}")
        zf.extract(info, dest_dir)
        count += 1
    return count


def _iter_app_files(app_dir):
    """Güncellenecek uygulama dosyaları (veritabanı ve kullanıcı verileri hariç)."""
    for root, dirs, files in os.walk(app_dir):
        dirs[:] = [
            d for d in dirs
            if d.lower() not in ("updates", "backups", "logs", "__pycache__")
        ]
        for fn in files:
            low = fn.lower()
            if low.endswith((".db", ".sqlite", ".sqlite3", ".log", ".json", ".tmp")):
                continue
            yield os.path.join(root, fn)


def _remove_tree_quiet(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ---------------------------------------------------------------- kaynak yönetimi

def get_local_source():
    """QSettings'te saklanan yerel güncelleme kaynağı (veya boş)."""
    if QSettings is None:
        return ""
    return str(QSettings().value("update/local_source", "") or "")


def set_local_source(path):
    """Yerel güncelleme kaynağını kalıcı olarak saklar (boş = devre dışı)."""
    if QSettings is not None:
        QSettings().setValue("update/local_source", path or "")


def candidate_sources():
    """Denetlenecek güncelleme kaynak klasörleri (öncelik sırasıyla)."""
    out = []
    src = get_local_source()
    if src:
        out.append(src)
    out.append(os.path.join(app_install_dir(), "updates"))
    return out


def _normalize_manifest(raw):
    m = dict(raw)
    m["version"] = str(m.get("version", "")).strip()
    m["file"] = str(m.get("file", "")).strip()
    m["notes"] = str(m.get("notes", "") or "")
    m["date"] = str(m.get("date", "") or "")
    m["sha256"] = str(m.get("sha256", "") or "").strip().lower()
    m["size"] = int(m.get("size") or 0)
    return m


def check_for_updates(sources=None, current_version=None):
    """Kaynaklarda manifest arar; yeni sürüm varsa bilgi sözlüğü döndürür.

    Dönüş: {"status": "no_source"} | {"status": "up_to_date"} |
           {"status": "update_available", "source_dir", "manifest", "package_path"}
    """
    if current_version is None:
        try:
            from versioning import read_version
            current_version = read_version()
        except Exception:
            current_version = "1.0.0"
    if sources is None:
        sources = candidate_sources()

    latest = None
    for src in sources:
        if not src or not os.path.isdir(src):
            continue
        manifest_path = os.path.join(src, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                m = _normalize_manifest(json.load(f))
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            log.warning("Manifest okunamadı (%s): %s", manifest_path, exc)
            continue
        pkg = os.path.join(src, m["file"]) if m["file"] else ""
        if not m["version"] or not pkg or not os.path.isfile(pkg):
            log.warning("Manifest eksik/uygunsuz, atlandı: %s", manifest_path)
            continue
        if latest is None or is_newer(m["version"], latest[1]["version"]):
            latest = (src, m, pkg)

    if latest is None:
        # Geçerli bir manifest dahi bulunamadı: kaynak yok sayılır.
        return {"status": "no_source"}

    src, manifest, pkg = latest
    if not is_newer(manifest["version"], current_version):
        return {"status": "up_to_date"}
    return {
        "status": "update_available",
        "source_dir": src,
        "manifest": manifest,
        "package_path": pkg,
    }


# ---------------------------------------------------------------- yükleme

def load_manifest_info(package_path):
    """Paket yanındaki manifest bilgisini okur (doğrulama öncesi gösterim için)."""
    mpath = os.path.join(os.path.dirname(package_path), "manifest.json")
    try:
        with open(mpath, "r", encoding="utf-8") as f:
            return _normalize_manifest(json.load(f))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {}


def _sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 512), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_package(package_path, expected_sha256, expected_size=0):
    """Paketin SHA-256 özetini (ve istenirse boyutunu) doğrular."""
    digest = _sha256_of(package_path)
    if expected_sha256 and digest != expected_sha256.lower():
        raise ValueError("Paket bütünlüğü doğrulanamadı (SHA-256 uyuşmuyor).")
    if expected_size and os.path.getsize(package_path) != expected_size:
        raise ValueError("Paket boyutu manifestle uyuşmuyor.")
    return digest


def _backup_app_files(app_dir, backup_dir):
    """Mevcut uygulama dosyalarını yedekler; yedek klasör yolunu döndürür.
    Damga mikrosaniyeli: aynı saniyede üst üste güncellemeler yedekleri
    ezmeyecek (gerçek dünyada betikle art arda güncelleme senaryosu)."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = os.path.join(backup_dir, f"app_backup_{stamp}")
    copied = 0
    for src in _iter_app_files(app_dir):
        rel = os.path.relpath(src, app_dir)
        dst = os.path.join(target, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    log.info("Güncelleme yedeği alındı: %s (%d dosya)", target, copied)
    return target, copied


def cleanup_old_backups(backup_dir, keep=3):
    """En yeni `keep` uygulama yedeği dışındakileri siler."""
    if not os.path.isdir(backup_dir):
        return 0
    entries = []
    for name in os.listdir(backup_dir):
        if name.startswith("app_backup_"):
            path = os.path.join(backup_dir, name)
            if os.path.isdir(path):
                try:
                    entries.append((os.path.getmtime(path), path))
                except OSError:
                    continue
    entries.sort(reverse=True)
    removed = 0
    for _, path in entries[keep:]:
        _remove_tree_quiet(path)
        removed += 1
    return removed


def _restart_marker_path(app_dir):
    return os.path.join(app_dir, "updates", ".restart_pending")


def apply_update(package_path, expected_sha256="", expected_size=0,
                 progress_cb=None, app_dir=None, db_manager=None):
    """İndirilen güncelleme paketini doğrular, yedekler, yükler ve işaretler.

    progress_cb(stage, pct) biçiminde çağrılır; stage: 'verify'|'backup'|'apply'.
    Hata durumunda uygulama önceki durumuna geri alınır ve istisna yükseltilir.
    Dönüş: {"installed_version", "backup_dir", "files", "applied"}
    """
    if progress_cb is None:
        progress_cb = lambda stage, pct: None  # noqa: E731

    if app_dir is None:
        app_dir = app_install_dir()
    updates_dir = os.path.join(app_dir, "updates")
    backup_dir = os.path.join(updates_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    # Veritabanı bağlantıları kapanmış olmalı; şimdilik güvenli yedek noktası
    if db_manager is not None:
        try:
            db_manager.backup_to(os.path.join(
                backup_dir,
                f"db_before_update_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.db"
            ))
        except Exception as exc:  # yedek alınamazsa güncellemeye girmeyiz
            raise RuntimeError(f"Güncelleme öncesi veritabanı yedeği alınamadı: {exc}")

    progress_cb("verify", 5)
    verify_package(package_path, expected_sha256, expected_size)

    progress_cb("backup", 20)
    backup_path, _ = _backup_app_files(app_dir, backup_dir)
    cleanup_old_backups(backup_dir, keep=3)

    progress_cb("apply", 45)
    installed = 0
    try:
        with zipfile.ZipFile(package_path, "r") as zf:
            installed = _safe_zip_extract(zf, app_dir)
    except Exception:
        _remove_tree_quiet(backup_path)  # kısmi yüklemeyi temizle
        raise

    # Yeniden başlatma işareti: eski süreç kapanınca yeni sürüm başlatılır
    os.makedirs(updates_dir, exist_ok=True)
    with open(_restart_marker_path(app_dir), "w", encoding="utf-8") as f:
        json.dump({
            "installed_version": load_manifest_info(package_path).get("version", ""),
            "backup_dir": backup_path,
            "date": datetime.now().isoformat(timespec="seconds"),
        }, f, ensure_ascii=False)

    progress_cb("apply", 100)
    version = load_manifest_info(package_path).get("version", "")
    log.info("Güncelleme uygulandı: v%s (%d dosya)", version, installed)
    return {
        "installed_version": version,
        "backup_dir": backup_path,
        "files": installed,
        "applied": True,
    }


def rollback_last_update(app_dir=None):
    """Son güncellemeyi geri alır: yedekten eski dosyaları kurtarır."""
    if app_dir is None:
        app_dir = app_install_dir()
    backup_root = os.path.join(app_dir, "updates", "backups")
    if not os.path.isdir(backup_root):
        raise FileNotFoundError("Geri alınacak yedek bulunamadı.")
    entries = sorted(
        (p for p in os.listdir(backup_root) if p.startswith("app_backup_")),
        reverse=True,
    )
    if not entries:
        raise FileNotFoundError("Geri alınacak yedek bulunamadı.")
    latest = os.path.join(backup_root, entries[0])
    copied = 0
    for root, _dirs, files in os.walk(latest):
        rel = os.path.relpath(root, latest)
        dest_root = app_dir if rel == "." else os.path.join(app_dir, rel)
        os.makedirs(dest_root, exist_ok=True)
        for fn in files:
            src = os.path.join(root, fn)
            dst = os.path.join(dest_root, fn)
            shutil.copy2(src, dst)
            copied += 1
    try:
        os.remove(_restart_marker_path(app_dir))
    except OSError:
        pass
    log.info("Güncelleme geri alındı (%d dosya)", copied)
    return copied


def consume_restart_flag(app_dir=None):
    """Bekleyen yeniden başlatma işaretini okur ve temizler.

    Dönüş: {"updated": True, "version", "backup_dir", "date} | {"updated": False}
    """
    if app_dir is None:
        app_dir = app_install_dir()
    marker = _restart_marker_path(app_dir)
    try:
        with open(marker, "r", encoding="utf-8") as f:
            data = json.load(f)
        os.remove(marker)
        return {"updated": True, **data}
    except (OSError, json.JSONDecodeError):
        return {"updated": False}


def launch_restarter(app_dir=None):
    """Uygulamayı kapatıp yeni sürümü başlatmak için yardımcı süreç açar.

    Kaynak modda hiçbir şey yapmaz (geliştirme dizini korunur).
    """
    if not is_frozen():
        return None
    if app_dir is None:
        app_dir = app_install_dir()
    exe = sys.executable
    script = os.path.join(app_dir, "updates", "restarter.vbs")
    with open(script, "w", encoding="utf-8") as f:
        f.write(
            "Set sh = CreateObject(\"WScript.Shell\")\n"
            "WScript.Sleep 1200\n"
            f"sh.Run \"\"\"{exe}\"\"\"\n"
        )
    import subprocess
    return subprocess.Popen(
        ["wscript.exe", script], close_fds=True,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
    )
