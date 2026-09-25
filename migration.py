"""
Veritabanı taşıma servisi — eski MERA-BİS PRO kurulumundan veri devralma.

Kurulum sihirbazı yeni veri dizinini (%APPDATA%\\MeraBisPro) açtığında, eski
kurulumun veritabanı eski dizinde/açılan klasörde kalabilir. Bu servis:

1. Bilinen konumlarda eski veritabanlarını tarar ve inceler (`find_source_databases`).
2. Kaynağı WAL-güvenli anlık görüntüye alır (sqlite backup API; olmazsa
   db+wal+shm dosya kopyası) — kaynak kurulum açıkken bile bozulma olmaz.
3. Taşıma ÖNCE mevcut veritabanını `pre_migration_*.db` olarak yedekler;
   yedek alınamazsa taşıma reddedilir.
4. "merge" (varsayılan): kaynak kayıtları mevcut veriye ekler —
   • aynı kod + aynı içerik  → atlanır (örnek veri yankısı / çift kayıt yok)
   • aynı kod + FARKLI içerik → kod sonuna "-T2" eklenerek eklenir
   • ölçüm kayıtları mera eşlemesiyle taşınır; aynı tarihli ölçüm atlanır
   "replace": mevcut kayıtlar temizlenip kaynak birebir alınır.
5. Sihirbazın açılışta öneri yapabilmesi için işaret dosyası yönetimi
   (`write_marker` / `consume_marker` / `clear_marker`).

GUI katmanı `gui/migration_wizard.py` içindedir; bu modül bilinçli olarak
Qt'suz yazılmıştır (birim testleri GUI olmadan koşar).
"""
import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime

LOG = logging.getLogger("merabis")

DB_FILENAME = "mera_otomasyonu.db"
WAL_SUFFIXES = ("-wal", "-shm")
SEED_COUNT = 81  # kurulumla gelen örnek veri kayıt sayısı (init_db tohumu)

# Eski sürüm kurulumlarının kullanabileceği veri dizini adları (yeni: MeraBisPro)
CANDIDATE_DATA_DIRS = ("MeraBisPro", "MeraBIS", "Mera Bis Pro", "merabispro")

# pastures tablosunun içerik karşılaştırmalı kolonları (id hariç)
PASTURE_FIELDS = (
    "code", "name", "city", "district", "village", "region", "area_hectares",
    "elevation_m", "bbhb_capacity", "kbhb_capacity", "dry_hay_yield_kg_per_ha",
    "vegetation_coverage_pct", "dominant_plants", "water_source", "soil_type",
    "erosion_risk", "allocation_purpose", "management_entity", "status",
    "lat", "lng", "polygon_coords_json", "grazing_season_start",
    "grazing_season_end", "notes",
)
_NUMERIC_FIELDS = {
    "area_hectares", "elevation_m", "bbhb_capacity", "kbhb_capacity",
    "dry_hay_yield_kg_per_ha", "vegetation_coverage_pct", "lat", "lng",
}


# ---------------------------------------------------------------------------
# Yol keşfi
# ---------------------------------------------------------------------------

def app_data_root():
    """Kullanıcı başına uygulama verisi kök dizini (Windows: %APPDATA%)."""
    if os.name == "nt":
        return os.environ.get("APPDATA") or os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    return os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")


def default_data_dir():
    """Yeni kurulumun veri dizini (db_manager._default_db_path ile aynı kök)."""
    if os.name == "nt":
        return os.path.join(app_data_root(), "MeraBisPro")
    if sys.platform == "darwin":
        return os.path.join(app_data_root(), "MeraBisPro")
    return os.path.join(app_data_root(), "merabispro")


def candidate_install_dirs():
    """Eski kurulumların veri dizini adayları (var olanlar önce, yinelenmeden)."""
    root = app_data_root()
    dirs = []
    for name in CANDIDATE_DATA_DIRS:
        p = os.path.join(root, name)
        if p not in dirs:
            dirs.append(p)
    # Var olan dizinleri öne al (kararlı sıralama)
    dirs.sort(key=lambda p: not os.path.isdir(p))
    return dirs


def find_source_databases(exclude_paths=None):
    """Bilinen konumlarda geçerli eski veritabanlarını arar; en yeni önce döndürür.

    Her aday için `inspect_database` çıktısı döndürülür; geçersiz dosyalar
    (valid=False) listelenmez. `exclude_paths` içindeki yollar atlanır
    (ör. yürürlükteki veritabanı).
    """
    exclude = {os.path.abspath(p) for p in (exclude_paths or [])}
    search_dirs = list(candidate_install_dirs())
    home = os.path.expanduser("~")
    for extra in ("Desktop", "Downloads", "Documents"):
        d = os.path.join(home, extra)
        if os.path.isdir(d):
            search_dirs.append(d)

    found = []
    for d in search_dirs:
        path = os.path.join(d, DB_FILENAME)
        if not os.path.isfile(path):
            continue
        if os.path.abspath(path) in exclude:
            continue
        info = inspect_database(path)
        if info.get("valid"):
            found.append(info)
    found.sort(key=lambda i: i["mtime"], reverse=True)
    return found


# ---------------------------------------------------------------------------
# İnceleme
# ---------------------------------------------------------------------------

def inspect_database(path):
    """Veritabanı dosyasını açmadan okunur biçimde inceler.

    Dönüş: {path, size, mtime, modified, valid, error, pastures,
            measurements, is_seed_only}
    """
    info = {
        "path": path,
        "size": 0,
        "mtime": 0.0,
        "modified": "",
        "valid": False,
        "error": "",
        "pastures": 0,
        "measurements": 0,
        "is_seed_only": False,
    }
    try:
        info["size"] = os.path.getsize(path)
        info["mtime"] = os.path.getmtime(path)
        info["modified"] = datetime.fromtimestamp(info["mtime"]).strftime("%Y-%m-%d %H:%M")
    except OSError as exc:
        info["error"] = str(exc)
        return info

    if info["size"] < 100:
        info["error"] = "empty"
        return info
    try:
        with open(path, "rb") as f:
            if f.read(15) != b"SQLite format 3":
                info["error"] = "not_sqlite"
                return info
    except OSError as exc:
        info["error"] = str(exc)
        return info

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "pastures" not in tables:
            info["error"] = "no_pastures_table"
            return info
        # Hızlı bütünlük denetimi (büyük dosyada bile hızlıdır)
        quick = conn.execute("PRAGMA quick_check").fetchone()
        if not quick or str(quick[0]).lower() != "ok":
            info["error"] = "integrity_failed"
            return info
        info["pastures"] = int(conn.execute("SELECT COUNT(*) FROM pastures").fetchone()[0] or 0)
        if "vegetation_measurements" in tables:
            info["measurements"] = int(
                conn.execute("SELECT COUNT(*) FROM vegetation_measurements").fetchone()[0] or 0
            )
        info["is_seed_only"] = info["pastures"] == SEED_COUNT and info["measurements"] == 0
        info["valid"] = True
        return info
    except sqlite3.Error as exc:
        info["error"] = f"sqlite: {exc}"
        return info
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Anlık görüntü (WAL-güvenli)
# ---------------------------------------------------------------------------

def _snapshot(source_path, workdir):
    """Kaynak veritabanının tutarlı kopyasını üretir; kopya yolunu döndürür.

    Önce sqlite backup API denenir (kaynak WAL modunda/açıkken bile tutarlıdır);
    o başarısızsa db + wal + shm dosyaları birlikte kopyalanır (kopya açılırken
    WAL yeniden oynatılır).
    """
    os.makedirs(workdir, exist_ok=True)
    snap = os.path.join(workdir, "source_snapshot.db")
    try:
        src = sqlite3.connect(source_path)
        try:
            dst = sqlite3.connect(snap)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        return snap
    except sqlite3.Error as exc:
        LOG.warning("Backup API başarısız (%s); dosya kopyasına dönülüyor", exc)
    try:
        shutil.copy2(source_path, snap)
        for suf in WAL_SUFFIXES:
            side = source_path + suf
            if os.path.isfile(side):
                shutil.copy2(side, snap + suf)
        return snap
    except OSError as exc:
        raise RuntimeError(f"Kaynak veritabanı kopyalanamadı: {exc}") from exc


# ---------------------------------------------------------------------------
# İçerik karşılaştırma ve birleştirme
# ---------------------------------------------------------------------------

def _same_content(a, b):
    """İki mera satırının içeriği eşit mi? (id hariç, toleranslı sayısal karşılaştırma)"""
    for field in PASTURE_FIELDS:
        va, vb = a.get(field), b.get(field)
        if field in _NUMERIC_FIELDS:
            try:
                fa = None if va is None or str(va).strip() == "" else float(va)
                fb = None if vb is None or str(vb).strip() == "" else float(vb)
            except (TypeError, ValueError):
                fa, fb = va, vb
            if fa is None and fb is None:
                continue
            if fa is None or fb is None:
                return False
            if abs(float(fa) - float(fb)) > 1e-9:
                return False
        else:
            sa = "" if va is None else str(va).strip()
            sb = "" if vb is None else str(vb).strip()
            if sa != sb:
                return False
    return True


def _load_pastures(snapshot_path):
    """Anlık görüntüdeki mera satırlarını dict listesi olarak döndürür."""
    conn = sqlite3.connect(snapshot_path)
    conn.row_factory = sqlite3.Row
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(pastures)").fetchall()}
        wanted = [c for c in PASTURE_FIELDS if c in cols] + (
            ["id"] if "id" in cols else []
        )
        rows = conn.execute(
            "SELECT %s FROM pastures" % ", ".join(wanted)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _load_measurements(snapshot_path):
    """Anlık görüntüdeki ölçüm satırlarını döndürür; tablo yoksa boş liste."""
    conn = sqlite3.connect(snapshot_path)
    conn.row_factory = sqlite3.Row
    try:
        has_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='vegetation_measurements'"
        ).fetchone()
        if not has_table:
            return []
        rows = conn.execute("SELECT * FROM vegetation_measurements").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _unique_code(db, base, taken):
    """Kod çakışmasında taşıma soneki ekleyerek boş kod üretir (MRA-01-01-T2)."""
    if base not in taken:
        return base
    n = 2
    while True:
        candidate = f"{base}-T{n}"
        if candidate not in taken:
            return candidate
        n += 1


def migrate(db, source_path, mode="merge", make_backup=True):
    """Kaynak veritabanını yürürlükteki veritabanına taşır.

    Args:
        db: DatabaseManager (hedef).
        source_path: eski kurulumun veritabanı dosyası.
        mode: "merge" (varsayılan) veya "replace".
        make_backup: taşıma öncesi hedefin pre_migration yedeği alınır;
            False birim testlerinde kullanılır (dosya taşımayan hızlı senaryolar).

    Returns:
        Rapor dict'i (imported, skipped_identical, conflicts, ... anahtarları).

    Raises:
        ValueError: kaynak geçersiz/okunamaz.
        RuntimeError: ön yedek alınamazsa veya anlık görüntü başarısızsa.
    """
    info = inspect_database(source_path)
    if not info.get("valid"):
        raise ValueError(f"Kaynak veritabanı geçersiz: {source_path} ({info.get('error')})")

    started = datetime.now().isoformat(timespec="seconds")
    report = {
        "mode": mode,
        "source": source_path,
        "source_pastures": info["pastures"],
        "source_measurements": info["measurements"],
        "backup": "",
        "snapshot": "",
        "imported": 0,
        "skipped_identical": 0,
        "conflicts_renamed": 0,
        "imported_measurements": 0,
        "skipped_measurements": 0,
        "pastures_before": 0,
        "pastures_after": 0,
        "measurements_after": 0,
        "started": started,
        "finished": "",
        "errors": [],
    }

    # 1) Ön yedek — taşıma asla yedeksiz yapılmaz
    if make_backup:
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = os.path.join(
                db.get_backup_dir(), f"pre_migration_{stamp}.db"
            )
            db.backup_to(backup_path)
            report["backup"] = backup_path
        except (OSError, sqlite3.Error) as exc:
            raise RuntimeError(f"Taşıma öncesi yedek alınamadı: {exc}") from exc

    # 2) Kaynağı anlık görüntüye al (kaynak açık/WAL modunda olabilir)
    tmpdir = tempfile.mkdtemp(prefix="merabis_migration_")
    try:
        snapshot = _snapshot(source_path, tmpdir)
        report["snapshot"] = snapshot
        _apply(db, snapshot, mode, report)
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass

    report["finished"] = datetime.now().isoformat(timespec="seconds")
    db_info = db.get_db_info()
    report["pastures_after"] = db_info["count"]
    report["measurements_after"] = _total_measurements(db)
    _write_meta_report(db, report)
    LOG.info(
        "Veri taşıma tamamlandı (%s): +%d mera, +%d ölçüm, %d özdeş atlandı, %d kod çakışması",
        mode, report["imported"], report["imported_measurements"],
        report["skipped_identical"], report["conflicts_renamed"],
    )
    return report


def _total_measurements(db):
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) FROM vegetation_measurements").fetchone()
        return int(row[0] or 0)
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def _apply(db, snapshot, mode, report):
    """Anlık görüntüyü hedefe uygular (merge veya replace)."""
    conn = db.get_connection()
    try:
        conn.execute("BEGIN")
        cursor = conn.cursor()
        if mode == "replace":
            cursor.execute("DELETE FROM vegetation_measurements")
            cursor.execute("DELETE FROM pastures")
            try:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='pastures'")
            except sqlite3.Error:
                pass  # sqlite_sequence yoksa (hiç AUTOINCREMENT kullanılmadıysa)
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise RuntimeError(f"Hedef temizlenemedi (replace): {exc}") from exc
    finally:
        conn.close()

    code_to_id = {}
    for row in db.get_all_pastures():
        code_to_id[db.normalize_code(row["code"])] = int(row["id"])
    taken = db.get_taken_codes()
    name_city = db.get_taken_name_city_pairs()

    source_rows = _load_pastures(snapshot)
    id_map = {}  # kaynak id -> yeni id

    for row in source_rows:
        try:
            code = db.normalize_code(row.get("code") or "")
            data = {f: row.get(f) for f in PASTURE_FIELDS}
            data["code"] = code

            if code and code in code_to_id:
                existing = db.get_pasture_by_id(code_to_id[code])
                if existing is not None and _same_content(existing, row):
                    report["skipped_identical"] += 1
                    id_map[int(row["id"])] = int(existing["id"])
                    continue
                # Farklı içerik + aynı kod: taşıma sonekiyle ekle
                new_code = _unique_code(db, code, taken)
                data["code"] = new_code
                report["conflicts_renamed"] += 1
            elif not code:
                data["code"] = db.get_next_code()
            elif code not in taken:
                # (name, city) benzersizliği yalnızca kod boşken zorunlu;
                # kod varken kod kimliktir.
                pass

            # (il, ad) çakışması güvenlik ağı: kod farklıysa bile birebir aynı
            # kaydı iki kez eklememek için içerik eşitse atla
            pair = (db.normalize_text(data.get("name") or ""), db.normalize_text(data.get("city") or ""))
            if pair in name_city and code not in taken:
                report["skipped_identical"] += 1
                continue

            new_id = db.add_pasture(data)
            taken.add(db.normalize_code(data["code"]))
            name_city.add(pair)
            code_to_id[db.normalize_code(data["code"])] = new_id
            if row.get("id") is not None:
                id_map[int(row["id"])] = int(new_id)
            report["imported"] += 1
        except (sqlite3.Error, KeyError, TypeError, ValueError) as exc:
            report["errors"].append(
                f"mera '{row.get('code', '?')}': {exc}"
            )
            LOG.warning("Kayıt taşınamadı: %s", exc)

    # Ölçüm kayıtları: kaynak mera id'sini yeni id'ye eşle
    measurements = _load_measurements(snapshot)
    for m in measurements:
        try:
            src_pid = m.get("pasture_id")
            new_pid = id_map.get(int(src_pid)) if src_pid is not None else None
            if new_pid is None:
                # Mera özdeş bulunup atlandıysa kod üzerinden eşle
                src_row = next((r for r in source_rows if r.get("id") == src_pid), None)
                if src_row:
                    c = db.normalize_code(src_row.get("code") or "")
                    new_pid = code_to_id.get(c)
            if new_pid is None:
                report["skipped_measurements"] += 1
                continue
            m_date = str(m.get("m_date") or "")
            existing_dates = _measurement_dates(db, new_pid)
            if m_date and m_date in existing_dates:
                report["skipped_measurements"] += 1
                continue
            _insert_measurement(db, new_pid, m)
            report["imported_measurements"] += 1
        except (sqlite3.Error, TypeError, ValueError) as exc:
            report["errors"].append(f"ölçüm #{m.get('id', '?')}: {exc}")
            LOG.warning("Ölçüm taşınamadı: %s", exc)


def _measurement_dates(db, pasture_id):
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT m_date FROM vegetation_measurements WHERE pasture_id = ?",
            (pasture_id,),
        ).fetchall()
        return {str(r[0]) for r in rows}
    except sqlite3.Error:
        return set()
    finally:
        conn.close()


def _insert_measurement(db, pasture_id, m):
    """Ölçümü orijinal created_at damgasıyla ekler."""
    conn = db.get_connection()
    try:
        conn.execute(
            '''INSERT INTO vegetation_measurements (
                   pasture_id, m_date, dry_hay_yield_kg_per_ha,
                   vegetation_coverage_pct, avg_height_cm, dominant_plants,
                   observer, method, notes, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                int(pasture_id),
                str(m.get("m_date") or ""),
                m.get("dry_hay_yield_kg_per_ha"),
                m.get("vegetation_coverage_pct"),
                m.get("avg_height_cm"),
                m.get("dominant_plants"),
                m.get("observer"),
                m.get("method"),
                m.get("notes"),
                str(m.get("created_at") or datetime.now().isoformat(timespec="seconds")),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _write_meta_report(db, report):
    """Taşıma raporunu meta tablosuna yazar (Denetim görünümü için iz)."""
    lite = {k: v for k, v in report.items() if k not in ("snapshot",)}
    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("last_data_migration", json.dumps(lite, ensure_ascii=False)),
        )
        conn.commit()
    except sqlite3.Error as exc:
        LOG.warning("Taşıma raporu meta'ya yazılamadı: %s", exc)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Açılış işareti (kurulum sihirbazı -> ilk açılış önerisi)
# ---------------------------------------------------------------------------

def marker_path():
    return os.path.join(default_data_dir(), "migration_pending.json")


def write_marker(source_path):
    """Kurulum sihirbazı yeni veri dizininde eski DB gördüğünde işaret bırakır."""
    path = marker_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"source": source_path, "seen": False}, f, ensure_ascii=False)
        return True
    except OSError as exc:
        LOG.warning("Taşıma işareti yazılamadı: %s", exc)
        return False


def consume_marker():
    """İşareti okur ve 'görüldü' olarak işaretler; kaynak yolu (veya None) döner."""
    path = marker_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    source = data.get("source") or None
    if not data.get("seen"):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"source": source, "seen": True}, f, ensure_ascii=False)
        except OSError:
            pass
    return source


def clear_marker():
    try:
        os.remove(marker_path())
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Otomatik öneri
# ---------------------------------------------------------------------------

def auto_proposal(current_db_path):
    """Açılışta otomatik öneri: mevcut DB yalnızca örnek veri iken ve bilinen
    konumlarda daha zengin geçerli bir eski DB varsa kaynağı döndürür; aksi halde None."""
    current = inspect_database(current_db_path)
    if not current.get("valid") or current["pastures"] == 0:
        return None
    if not current.get("is_seed_only"):
        return None  # kullanıcı verisi var; öneri yapılmaz
    candidates = find_source_databases(exclude_paths=[current_db_path])
    for cand in candidates:
        if cand["pastures"] > SEED_COUNT or cand["measurements"] > 0:
            return cand
    return None
