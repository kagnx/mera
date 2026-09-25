"""
Veritabanı yedekleme / geri yükleme birim testleri.

Çalıştırma:  python tests/test_backup.py
"""
import os
import sys
import tempfile
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from database.db_manager import DatabaseManager  # noqa: E402

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK]   {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def new_db():
    tmp = tempfile.mkdtemp()
    return DatabaseManager(os.path.join(tmp, "test.db"))


def test_backup_roundtrip():
    print("1) Yedek al - geri yükle döngüsü")
    db = new_db()
    pid = db.add_pasture({
        "code": "MRA-99-99", "name": "Yedek Test Merası", "city": "Test",
        "district": "X", "region": "Ege", "area_hectares": 500.0,
    })
    check("kayıt eklendi (82)", db.get_statistics()["total_count"] == 82)

    backup_path = os.path.join(tempfile.mkdtemp(), "yedek.db")
    db.backup_to(backup_path)
    check("yedek dosyası oluştu", os.path.exists(backup_path))

    with open(backup_path, "rb") as f:
        check("yedek geçerli SQLite başlığı", f.read(15) == b"SQLite format 3")

    # Mevcut veritabanını boz: 2 kayıt sil
    db.delete_pasture(1)
    db.delete_pasture(2)
    check("silme sonrası 80 kayıt", db.get_statistics()["total_count"] == 80)

    db.restore_from(backup_path)
    check("geri yükleme sonrası 82 kayıt", db.get_statistics()["total_count"] == 82)
    check("kullanıcı kaydı geri geldi", db.get_pasture_by_id(pid) is not None)
    check("silinen kayıtlar da geri geldi", db.get_pasture_by_id(1) is not None)


def test_restore_rejects_invalid():
    print("2) Geçersiz dosyalar reddedilir")
    db = new_db()
    tmp = tempfile.mkdtemp()

    bad = os.path.join(tmp, "not_db.txt")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("bu bir veritabanı değil")
    try:
        db.restore_from(bad)
        check("metin dosyası reddedildi", False)
    except ValueError:
        check("metin dosyası reddedildi", True)

    # SQLite ama pastures tablosu yok
    other = os.path.join(tmp, "other.db")
    conn = sqlite3.connect(other)
    conn.execute("CREATE TABLE foo (id INTEGER)")
    conn.commit()
    conn.close()
    try:
        db.restore_from(other)
        check("pastures'sız dosya reddedildi", False)
    except ValueError:
        check("pastures'sız dosya reddedildi", True)

    try:
        db.restore_from(os.path.join(tmp, "yok.db"))
        check("olmayan dosya FileNotFoundError", False)
    except FileNotFoundError:
        check("olmayan dosya FileNotFoundError", True)


def test_list_backups():
    print("3) Yedek listesi")
    db = new_db()
    backup_dir, entries = db.list_backups()
    check("yeni klasörde liste boş", len(entries) == 0)

    db.backup_to(os.path.join(backup_dir, "a.db"))
    db.backup_to(os.path.join(backup_dir, "b.db"))
    _, entries = db.list_backups()
    check("2 yedek listeleniyor", len(entries) == 2)
    check("en yeni önce sıralı", entries[0]["modified"] >= entries[1]["modified"])
    check("dosya adları doğru", {e["name"] for e in entries} == {"a.db", "b.db"})

    # yedek klasörü veritabanının yanında
    check("yedek klasörü db'nin yanında", os.path.dirname(backup_dir) == os.path.dirname(db.db_path))


def test_db_info():
    print("4) get_db_info")
    db = new_db()
    info = db.get_db_info()
    check("kayıt sayısı 81", info["count"] == 81)
    check("dosya yolu doğru", info["path"] == db.db_path)
    check("boyut > 0", info["size"] > 0)
    check("son değişiklik > 0", info["modified"] > 0)


if __name__ == "__main__":
    test_backup_roundtrip()
    test_restore_rejects_invalid()
    test_list_backups()
    test_db_info()
    print(f"\nSONUC: {PASS} gecti, {FAIL} basarisiz")
    sys.exit(1 if FAIL else 0)
