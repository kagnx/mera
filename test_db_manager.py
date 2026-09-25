"""
MERA-BİS PRO veritabanı katmanı için regresyon testleri.

pytest'e bağımlılık yoktur:  `python tests/test_db_manager.py`  ile çalıştırılabilir.
"""
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from database.db_manager import DatabaseManager  # noqa: E402
from database.validation import is_valid_code_format  # noqa: E402

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


def test_seed_only_when_empty():
    print("1) Örnek veri yalnızca boş tabloya yüklenir (kullanıcı verisi korunur)")
    db = new_db()
    check("ilk açılışta 81 kayıt", db.get_statistics()["total_count"] == 81)

    pid = db.add_pasture({
        "code": "MRA-99-99", "name": "Kullanıcı Merası", "city": "Test",
        "district": "X", "region": "Ege", "area_hectares": 500.0,
    })
    db2 = DatabaseManager(db.db_path)  # yeniden açılış simülasyonu
    check("yeniden açılışta kullanıcı kaydı korunur",
          db2.get_pasture_by_id(pid) is not None)

    db2.delete_pasture(1)
    db2.delete_pasture(2)  # 80 kayıt < 81
    db3 = DatabaseManager(db.db_path)  # yeniden açılış
    stats = db3.get_statistics()
    check("silme sonrası yeniden tohumlama YAPILMAZ (80 kalır)",
          stats["total_count"] == 80,
          f"beklenen 80, gelen {stats['total_count']}")
    check("silme sonrası kullanıcı kaydı da korunur",
          db3.get_pasture_by_id(pid) is not None)


def test_duplicate_code_raises():
    print("2) Tekil (UNIQUE) kod ihlali IntegrityError üretir (GUI yakalar)")
    db = new_db()
    try:
        db.add_pasture({"code": "MRA-01-01", "name": "Dup", "city": "X",
                        "district": "Y", "region": "Ege", "area_hectares": 10.0})
        check("çakışan kod eklenmemeli", False, "hata fırlatılmadı")
    except Exception as exc:
        check("IntegrityError fırlar", exc.__class__.__name__ == "IntegrityError")


def test_get_next_code():
    print("3) get_next_code benzersiz kod üretir")
    db = new_db()
    code = db.get_next_code()
    check("81 kayıttan sonra MRA-82-01", code == "MRA-82-01", f"gelen {code}")
    db.add_pasture({"code": code, "name": "Yeni", "city": "X", "district": "Y",
                    "region": "Ege", "area_hectares": 10.0})
    check("ardışık kod MRA-83-01", db.get_next_code() == "MRA-83-01")


def test_edit_preserves_fields():
    print("4) Düzenleme idari/erozyon/sezon alanlarını silmez (hata düzeltmesi)")
    db = new_db()
    p = db.get_pasture_by_id(1)
    data = dict(p)
    data["name"] = "Güncellendi"
    db.update_pasture(1, data)
    p2 = db.get_pasture_by_id(1)
    check("erozyon_risk korunur", p2["erosion_risk"] == p["erosion_risk"])
    check("sezon başlangıcı korunur", p2["grazing_season_start"] == p["grazing_season_start"])
    check("tahsis amacı korunur", p2["allocation_purpose"] == p["allocation_purpose"])
    check("yönetim birimi korunur", p2["management_entity"] == p["management_entity"])
    check("isim güncellenir", p2["name"] == "Güncellendi")


def test_statistics_aliases():
    print("5) get_statistics anlamlı alias anahtarları döndürür")
    db = new_db()
    s = db.get_statistics()
    ok = all("total_area" in r and "count" in r for r in s["region_stats"]) and \
         all("total_area" in r and "count" in r for r in s["city_stats"]) and \
         all("count" in r for r in s["status_stats"])
    check("alias alanları mevcut", ok)
    check("toplam alan > 0", s["total_area"] > 0)


def test_filters():
    print("6) Filtreler çalışır")
    db = new_db()
    all_rows = db.get_all_pastures()
    ankara = db.get_all_pastures({"city": "Ankara"})
    check("il filtresi", len(ankara) == 1 and ankara[0]["city"] == "Ankara")
    search = db.get_all_pastures({"search": "Adana"})
    check("arama filtresi", len(search) >= 1)
    status = db.get_all_pastures({"status": "Dinlendirmede / Islah"})
    check("durum filtresi", len(status) >= 1)
    check("boş filtrelere tüm kayıtlar", len(db.get_all_pastures({"city": "Tümü", "region": "Tümü", "status": "Tümü"})) == len(all_rows))


def test_exports():
    print("7) Dışa aktarma işlevleri")
    db = new_db()
    tmp = tempfile.mkdtemp()
    csv_path = os.path.join(tmp, "m.csv")
    json_path = os.path.join(tmp, "m.json")
    check("CSV aktarımı", db.export_to_csv(csv_path) and os.path.getsize(csv_path) > 0)
    check("JSON aktarımı", db.export_to_json(json_path) and os.path.getsize(json_path) > 0)
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    check("JSON 81 kayıt", len(data) == 81)
    # Boş veride dışa aktarma False dönmeli (tutarlı davranış)
    e2 = DatabaseManager(os.path.join(tempfile.mkdtemp(), "e.db"))
    conn = e2.get_connection()
    conn.execute("DELETE FROM pastures")
    conn.commit()
    conn.close()
    check("boş veride CSV False", e2.export_to_csv(os.path.join(tmp, "e.csv")) is False)
    check("boş veride JSON False", e2.export_to_json(os.path.join(tmp, "e.json")) is False)


def test_schema_migration():
    print("8) Eski şemaya eksik kolon eklenir (migrasyon)")
    import sqlite3
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "old.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE pastures (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    conn.commit()
    conn.close()
    db = DatabaseManager(path)
    cols = db.get_all_pastures()
    check("migrasyon sonrası tablo sorgulanabilir", isinstance(cols, list))
    check("eksik kolonlar eklenmiş", bool(cols) and "status" in cols[0])
    check("eski veri korunmuş", all("name" in c for c in cols))


def test_code_exists():
    print("9) code_exists çakışma kontrolü")
    db = new_db()
    check("mevcut kod True", db.code_exists("MRA-01-01"))
    check("olmayan kod False", not db.code_exists("MRA-99-99"))
    check("düzenlemede kendi kaydı hariç (exclude_id)", not db.code_exists("MRA-01-01", exclude_id=1))
    check("başka kayıtla çakışma (exclude_id)", db.code_exists("MRA-01-01", exclude_id=2))


def test_code_normalization():
    print("10) Kod normalizasyonu (büyük/küçük harf ve boşluk)")
    db = new_db()
    check("normalize_code küçük harfi büyütür",
          DatabaseManager.normalize_code("mra-01-01") == "MRA-01-01")
    check("normalize_code boşlukları temizler",
          DatabaseManager.normalize_code("  MRA-01-01  ") == "MRA-01-01")
    check("normalize_code iç boşlukları sadeleştirir",
          DatabaseManager.normalize_code("MRA  01  01") == "MRA 01 01")
    check("None güvenli", DatabaseManager.normalize_code(None) == "")

    # Harf/boşluk farklarıyla çakışma tespiti
    check("küçük harfli kod çakışma olarak tespit edilir", db.code_exists("mra-01-01"))
    check("boşluklu kod çakışma olarak tespit edilir", db.code_exists("  MRA-01-01  "))
    check("normalleştirilmiş olmayan kod yok sayılır", not db.code_exists("MRA-99-99"))
    check("exclude_id ile küçük harfli çakışma atlanır", not db.code_exists("mra-01-01", exclude_id=1))

    # Eklemede/güncellemede kod normalleşerek saklanır
    pid = db.add_pasture({
        "code": "  mra-82-01 ", "name": "Norm Test", "city": "X", "district": "Y",
        "region": "Ege", "area_hectares": 10.0,
    })
    check("eklemede kod normalleşir", db.get_pasture_by_id(pid)["code"] == "MRA-82-01")
    p1 = db.get_pasture_by_id(1)
    data = dict(p1)
    data["code"] = " mra-90-01 "
    db.update_pasture(1, data)
    check("güncellemede kod normalleşir", db.get_pasture_by_id(1)["code"] == "MRA-90-01")
    # Normalleştirilmiş kod UNIQUE ihlali üretir (aynı koda farklı harfle ekleme)
    try:
        db.add_pasture({
            "code": "mra-82-01", "name": "Dup Norm", "city": "X", "district": "Y",
            "region": "Ege", "area_hectares": 10.0,
        })
        check("normalleştirilmiş kod UNIQUE ihlali", False)
    except Exception as exc:
        check("normalleştirilmiş kod UNIQUE ihlali", exc.__class__.__name__ == "IntegrityError")


def test_name_uniqueness():
    print("11) Aynı ilde aynı adlı mera kontrolü")
    db = new_db()
    p1 = db.get_pasture_by_id(1)  # Adana / Çukurova Taban Çayırı Merası
    check("aynı il aynı ad True", db.name_exists_in_city(p1["name"], "Adana"))
    check("aynı ad farklı il False", not db.name_exists_in_city(p1["name"], "İzmir"))
    check("harf/boşluk farkı yok sayılır",
          db.name_exists_in_city("  çukurova taban çayırı merası ", " adana "))
    check("exclude_id kendi kaydını atlar", not db.name_exists_in_city(p1["name"], "Adana", exclude_id=1))
    check("boş ad False", not db.name_exists_in_city("", "Adana"))
    check("boş il False", not db.name_exists_in_city(p1["name"], ""))


def test_search_codes():
    print("12) search_codes autocomplete önek araması")
    db = new_db()
    matches = db.search_codes("MRA-0")
    check("MRA-0 öneki 9 sonuç (MRA-01..09)", len(matches) == 9, str(len(matches)))
    check("sonuçlar önekle başlar", all(m.startswith("MRA-0") for m in matches))
    check("geniş önek varsayılan limit 10", len(db.search_codes("MRA-")) == 10)
    check("küçük harfli önek de eşleşir", "MRA-01-01" in db.search_codes("mra-01"))
    check("boşluklu önek normalleşir", "MRA-01-01" in db.search_codes(" mra-01 "))
    check("boş önek boş liste", db.search_codes("") == [])
    check("eşleşmeyen önek boş liste", db.search_codes("MRA-99") == [])
    check("limit parametresi uygulanır", len(db.search_codes("MRA-", limit=3)) == 3)


def test_audit_consistency_db():
    print("14) Toplu tutarlılık denetimi (audit_consistency, gerçek DB)")
    db = new_db()
    report = db.audit_consistency()
    check("örnek veri temiz",
          report["total"] == 81 and report["ok"] == 81
          and report["with_issues"] == 0 and report["issues"] == [])

    # Kural ihlallerini add_pasture'u atlayarak doğrudan SQL ile enjekte et
    # (add_pasture kodları normalleştirdiği için gerçek eski/kötü veriyi simüle eder)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("mra-99-99", "", "Adana", "Seyhan", "Akdeniz", 10.0,
                 "Aktif Otlatma", 37.0, 35.0))
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("MRA-98-98", "Denetim Testi Merası", "", "Merkez", "İç Anadolu", 5.0,
                 "Aktif Otlatma", 39.0, 32.0))
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("MRA-97-97", "Denetim Testi Merası", "Ankara", "Polatlı",
                 "İç Anadolu", 7.0, "Aktif Otlatma", 39.9, 32.8))
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("MRA-96-96", "Denetim Testi Merası", "Ankara", "Çubuk",
                 "İç Anadolu", 9.0, "Aktif Otlatma", 40.2, 33.0))
    conn.commit()
    conn.close()

    report = db.audit_consistency()
    check("total 85", report["total"] == 85, str(report["total"]))
    check("ok 81 korunur", report["ok"] == 81)
    check("with_issues 4", report["with_issues"] == 4)
    check("summary normalleştirme 1", report["summary"].get("code_normalize") == 1)
    check("summary boş ad 1", report["summary"].get("name_empty") == 1)
    check("summary boş il 1", report["summary"].get("city_empty") == 1)
    check("summary ad-il çakışması 2", report["summary"].get("name_city_duplicate") == 2)
    check("kopya kod yok (UNIQUE engeller)", "code_duplicate" not in report["summary"])

    # Sorunlu kayıt detayları doğru kayıtlara işaret ediyor
    by_code = {i["code"]: i for i in report["issues"]}
    check("küçük harfli kod raporlanır", "MRA-99-99" in by_code)
    check("boş ad kaydı ad-il çakışması sayılmaz",
          all(p["key"] != "name_city_duplicate"
              for p in by_code["MRA-99-99"]["problems"]))
    ankr = [i for i in report["issues"] if i["code"] in ("MRA-97-97", "MRA-96-96")]
    check("ankara ikilisi ad-il çakışması işaretlenir", len(ankr) == 2
          and all(any(p["key"] == "name_city_duplicate" for p in i["problems"])
                  for i in ankr))


def test_rule_migration_db():
    print("15) Kural sürümü ve otomatik veri göçü (gerçek DB)")
    db = new_db()
    check("yeni DB kural sürümü 1", db.get_rule_version() == 1,
          str(db.get_rule_version()))
    info = db.get_last_migration_info()
    check("ilk göç raporu kayıtlı (adım [1], değişiklik yok)",
          info is not None and info["applied_steps"] == [1]
          and info["changed"] == 0 and "date" in info, str(info))

    # Sürümlemeden önceki (0) veritabanı simülasyonu: küçük harfli kod doğrudan SQL ile
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA user_version = 0")
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("mra-99-99", "Göç Testi", "Ankara", "Polatlı", "İç Anadolu", 10.0,
                 "Aktif Otlatma", 39.9, 32.8))
    conn.commit()
    conn.close()

    # Yeniden açılış → init_db → otomatik göç
    db2 = DatabaseManager(db.db_path)
    p = db2.get_pasture_by_id(82)
    check("küçük harfli kod otomatik normalleşir",
          p["code"] == "MRA-99-99", str(p["code"]))
    check("sürüm 1'e yükseltildi", db2.get_rule_version() == 1)
    info2 = db2.get_last_migration_info()
    check("göç raporu changed 1", info2 is not None and info2["changed"] == 1)
    check("göç raporu adım [1]", info2["applied_steps"] == [1])

    # Çakışma senaryosu: göç sonrası aynı koda düşen iki kayıt değiştirilmez
    conn = db2.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA user_version = 0")
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("mra-98-98", "Çakışma A", "İzmir", "Merkez", "Ege", 5.0,
                 "Aktif Otlatma", 38.4, 27.1))
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("MRA-98-98", "Çakışma B", "İzmir", "Buca", "Ege", 6.0,
                 "Aktif Otlatma", 38.4, 27.2))
    conn.commit()
    conn.close()
    db3 = DatabaseManager(db.db_path)
    info3 = db3.get_last_migration_info()
    check("çakışan göç kaydı raporlanır",
          info3 is not None and len(info3["conflicts"]) == 1
          and info3["conflicts"][0]["id"] == 83
          and info3["conflicts"][0]["code"] == "MRA-98-98", str(info3))
    check("çakışan kayıtlar değiştirilmez",
          db3.get_pasture_by_id(83)["code"] == "mra-98-98"
          and db3.get_pasture_by_id(84)["code"] == "MRA-98-98")
    check("sürüm yine 1", db3.get_rule_version() == 1)

    # Mevcut (normal) veri göçten etkilenmez
    check("seed kayıtları göçten etkilenmez",
          db3.get_pasture_by_id(1)["code"] == "MRA-01-01")


def test_pre_backup_check():
    print("16) Yedek öncesi bakım ön-kontrolü (göç + sürüm doğrulama)")
    db = new_db()
    check_ = db.pre_backup_check()
    check("güncel veride ön-kontrol geçer",
          check_["ok"] is True and check_["migrated"] is False, str(check_))
    check("sürüm eşleşir",
          check_["rule_version"] == check_["expected_version"] == 1)
    check("ensure_migrated True", db.ensure_migrated() is True)

    # Bekleyen göç simülasyonu: sürüm 0'a düşür + küçük harfli kod ekle
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA user_version = 0")
    cur.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                ("mra-77-77", "Ön Kontrol Testi", "Antalya", "Merkez", "Akdeniz", 8.0,
                 "Aktif Otlatma", 36.9, 30.7))
    conn.commit()
    conn.close()

    check_ = db.pre_backup_check()
    check("bekleyen göç ön-kontrolde otomatik uygulanır",
          check_["migrated"] is True and check_["ok"] is True, str(check_))
    check("göç sonrası sürüm güncel", check_["rule_version"] == 1)
    check("küçük harfli kod göçle normalleşti",
          db.get_pasture_by_id(82)["code"] == "MRA-77-77")


def test_polygon_consistency_db():
    print("14) poligon–kayıtlı alan uyum denetimi (shoelace + eşik)")
    from database.geometry import polygon_area_hectares, is_seed_template
    from database import geometry as _g

    # --- Hesap paritesi (JS polygonAreaHectares ile aynı formül) ---
    sq = polygon_area_hectares([[39.0, 32.0], [39.0, 32.04],
                                [38.96, 32.04], [38.96, 32.0]])
    check("shoelace 0.04° kare ~1538 ha (39° enlem)",
          sq is not None and 1400.0 < sq < 1700.0, str(sq))
    check("2 nokta poligon None",
          polygon_area_hectares([[0, 0], [1, 1]]) is None)
    check("collinear (sıfır alan) None",
          polygon_area_hectares([[0, 0], [1, 1], [2, 2]]) is None)
    check("bozuk giriş None",
          polygon_area_hectares(None) is None
          and polygon_area_hectares([[1, "a"], [2, 3], [3, 4]]) is None)
    check("kapalı halka kabul edilir (son nokta = ilk)",
          polygon_area_hectares([[39.0, 32.0], [39.0, 32.04],
                                 [38.96, 32.04], [38.96, 32.0],
                                 [39.0, 32.0]]) is not None)

    db = new_db()
    p = db.get_pasture_by_id(1)
    coords = json.loads(p["polygon_coords_json"])
    check("seed şablonu (±0.02° kare) tanınır",
          is_seed_template(coords, p["lat"], p["lng"]))
    check("şablon bozulursa tanınmaz (3 nokta)",
          not is_seed_template(coords[:3], p["lat"], p["lng"]))

    # Temiz seed: tümü yer tutucu → rapor boş (sahte sapma YOK)
    ps = db.audit_polygon_consistency()
    check("temiz seed: 0 denetim, 81 yer tutucu, 0 sapma",
          ps["checked"] == 0 and ps["placeholder"] == 81
          and len(ps["deviations"]) == 0, str(ps))

    # Gerçek poligon + büyük sapma → raporlanır
    data = dict(p)
    coords2 = [
        [p["lat"] + 0.01, p["lng"] + 0.01],
        [p["lat"] + 0.01, p["lng"] + 0.035],
        [p["lat"] - 0.01, p["lng"] + 0.035],
        [p["lat"] - 0.01, p["lng"] + 0.01],
    ]
    data["polygon_coords_json"] = json.dumps(coords2)
    db.update_pasture(p["id"], data)
    ps2 = db.audit_polygon_consistency()
    check("değiştirilen mera denetime girer (1 denetim, 80 yer tutucu)",
          ps2["checked"] == 1 and ps2["placeholder"] == 80, str(ps2))
    check(">%25 sapma raporlandı (en kötü önce)",
          len(ps2["deviations"]) == 1
          and ps2["deviations"][0]["id"] == p["id"]
          and (ps2["deviations"][0]["deviation_pct"] or 0) > 25,
          str(ps2["deviations"]))
    d0 = ps2["deviations"][0]
    check("hesap alanı makul aralıkta (popup paritesi)",
          450.0 < d0["calc_ha"] < 550.0, str(d0.get("calc_ha")))

    # Eşik altı: kayıtlı alanı hesabın ~%15 üstüne çek → raporlanmaz
    ha = polygon_area_hectares(coords2)
    data["area_hectares"] = round(ha * 1.15, 1)
    db.update_pasture(p["id"], data)
    ps3 = db.audit_polygon_consistency()
    check("%15 sapma eşik altında kalmaya devam eder",
          len(ps3["deviations"]) == 0, str(ps3["deviations"]))

    # Kayıtlı alanı olmayan kayıt (savunma yolu) → missing_area
    fake = [{
        "id": 999, "code": "MRA-XX-XX", "name": "X", "city": "X",
        "lat": 39.0, "lng": 32.0, "area_hectares": None,
        "polygon_coords_json": json.dumps(
            [[39.01, 31.98], [39.01, 32.02], [38.99, 32.02], [38.99, 31.98]]),
    }]
    r = _g.audit_polygon_consistency(fake)
    check("kayıtsız alan → missing_area olarak raporlanır",
          len(r["deviations"]) == 1
          and r["deviations"][0]["reason"] == "missing_area", str(r))


def test_measurement_audit_log_db():
    print("15) ölçüm denetim izi (kaynak + diff + silme)")
    db = new_db()
    mid = db.add_measurement({
        "pasture_id": 1, "m_date": "2026-09-01",
        "dry_hay_yield_kg_per_ha": 1000.0, "observer": "Ali",
    }, source="map")
    log = db.get_measurement_audit_log(pasture_id=1)
    check("ekleme izi yazıldı (map kaynağı)",
          len(log) == 1 and log[0]["action"] == "add"
          and log[0]["source"] == "map"
          and log[0]["measurement_id"] == mid, str(log))
    check("iz mera koduyla birleşik",
          log[0]["pasture_code"] == "MRA-01-01", str(log[0].get("pasture_code")))

    db.update_measurement(mid, {
        "pasture_id": 1, "m_date": "2026-09-01",
        "dry_hay_yield_kg_per_ha": 1200.0, "observer": "Ali",
        "notes": "revize",
    }, source="menu")
    log = db.get_measurement_audit_log(pasture_id=1)
    check("güncelleme izi diff içeriyor (menu kaynağı)",
          log[0]["action"] == "update" and log[0]["source"] == "menu"
          and len(log[0]["changed_fields"]) == 2,
          str(log[0]["changed_fields"]))
    check("diff alan adları doğru",
          any(c.startswith("dry_hay_yield_kg_per_ha:") for c in log[0]["changed_fields"])
          and any(c.startswith("notes:") for c in log[0]["changed_fields"]),
          str(log[0]["changed_fields"]))

    db.add_measurement({"pasture_id": 2, "m_date": "2026-09-02"}, source="form")
    all_log = db.get_measurement_audit_log()
    check("tüm izler en-yeni-önce", len(all_log) == 3
          and all_log[0]["pasture_id"] == 2, str(len(all_log)))

    db.delete_measurement(mid, source="menu")
    log = db.get_measurement_audit_log(pasture_id=1)
    check("silme izi yazıldı",
          log[0]["action"] == "delete" and log[0]["source"] == "menu",
          str(log[0]))

    mid2 = db.add_measurement({"pasture_id": 3, "m_date": "2026-09-03"})
    log = db.get_measurement_audit_log(pasture_id=3)
    check("varsayılan kaynak 'form'",
          mid2 is not None and log[0]["source"] == "form", str(log[0]["source"]))


def test_audit_log_filters_db():
    print("16) denetim izi filtreleri (kaynak + tarih aralığı)")
    db = new_db()
    # Üç kaynak × üç gün: filter testleri için belirgin taban
    for src in ("map", "menu", "form"):
        db.add_measurement(
            {"pasture_id": 1, "m_date": "2026-09-01"}, source=src)
    # Sentetik zaman damgaları — API 'şimdi' yazdığından eski kayıtlar
    # doğrudan SQL ile yerleştirilir (aynı şema, aynı birleşim görünümü)
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO measurement_audit_log "
        "(measurement_id, pasture_id, action, source, changed_fields, timestamp) "
        "VALUES (NULL, 1, 'add', 'map', '[]', '2026-08-01T10:00:00')")
    conn.execute(
        "INSERT INTO measurement_audit_log "
        "(measurement_id, pasture_id, action, source, changed_fields, timestamp) "
        "VALUES (NULL, 1, 'update', 'menu', '[]', '2026-08-15T12:30:00')")
    conn.commit()

    all_rows = db.get_measurement_audit_log()
    check("filtresiz sorgu tüm satırları döndürür", len(all_rows) == 5,
          str(len(all_rows)))

    only_map = db.get_measurement_audit_log(source="map")
    check("kaynak filtresi yalnız map satırlarını döndürür",
          len(only_map) == 2 and all(r["source"] == "map" for r in only_map),
          str([(r["source"], r["timestamp"]) for r in only_map]))

    only_menu = db.get_measurement_audit_log(source="menu")
    check("kaynak filtresi menu (sentetik dahil)",
          len(only_menu) == 2 and all(r["source"] == "menu" for r in only_menu),
          str(len(only_menu)))

    day = db.get_measurement_audit_log(date_from="2026-08-01",
                                       date_to="2026-08-01")
    check("tek gün aralığı yalnız o günü döndürür",
          len(day) == 1 and day[0]["timestamp"].startswith("2026-08-01T10"),
          str([r["timestamp"] for r in day]))

    span = db.get_measurement_audit_log(date_from="2026-08-01",
                                        date_to="2026-08-15")
    check("iki haftalık aralık iki sentetik satırı döndürür", len(span) == 2,
          str([r["timestamp"] for r in span]))

    today = db.get_measurement_audit_log(
        date_from="2026-08-16", date_to="2026-08-31")
    check("aralık dışı sorgu boş döner", today == [], str(today))

    combo = db.get_measurement_audit_log(source="menu", date_from="2026-08-01",
                                         date_to="2026-08-31")
    check("birleşik filtre (kaynak + tarih)",
          len(combo) == 1 and combo[0]["source"] == "menu"
          and combo[0]["timestamp"].startswith("2026-08-15"),
          str(combo))

    # Geriye uyumluluk: yalnız pasture_id veren eski çağrı davranışı korur
    legacy = db.get_measurement_audit_log(pasture_id=1)
    check("geriye uyumlu pasture_id çağrısı filtrelerden etkilenmez",
          len(legacy) == 5, str(len(legacy)))


def test_random_code():
    print("13) get_random_code rastgele kod üretimi")
    db = new_db()
    ok = True
    for _ in range(30):
        code = db.get_random_code()
        if not is_valid_code_format(code) or db.code_exists(code):
            ok = False
            break
    check("30 rastgele kod biçimli ve veritabanında benzersiz", ok)
    code2 = db.get_random_code(exclude_id=1)
    check("exclude_id ile üretim", is_valid_code_format(code2) and not db.code_exists(code2, exclude_id=1))


if __name__ == "__main__":
    test_seed_only_when_empty()
    test_duplicate_code_raises()
    test_get_next_code()
    test_edit_preserves_fields()
    test_statistics_aliases()
    test_filters()
    test_exports()
    test_schema_migration()
    test_code_exists()
    test_code_normalization()
    test_name_uniqueness()
    test_search_codes()
    test_audit_consistency_db()
    test_rule_migration_db()
    test_pre_backup_check()
    test_random_code()
    test_polygon_consistency_db()
    test_measurement_audit_log_db()
    test_audit_log_filters_db()
    print(f"\nSONUC: {PASS} gecti, {FAIL} basarisiz")
    sys.exit(1 if FAIL else 0)
