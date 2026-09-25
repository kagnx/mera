import sqlite3
import os
import sys
import json
import csv
import shutil
import random
import logging
from datetime import datetime, timedelta

from database import geometry

LOG = logging.getLogger("merabis.db")

from database.validation import RULES_VERSION as _RULES_VERSION
from database.validation import apply_rule_migrations as _apply_rule_migrations
from database.validation import audit_all_records as _audit_all_records
from database.validation import normalize_code as _norm_code
from database.validation import normalize_text as _norm_text

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = self._default_db_path()
        self.db_path = db_path
        self.init_db()

    @staticmethod
    def _default_db_path():
        """
        Paketlenmiş (PyInstaller) uygulamada veritabanı geçici dizine değil,
        kullanıcının kalıcı veri dizinine yazılır. Böylece her açılışta
        kullanıcı verileri kaybolmaz. Kaynak koddan çalışırken proje dizini
        kullanılır (geliştirme kolaylığı).
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
            if os.name == "nt":
                data_dir = os.environ.get("APPDATA") or os.path.expanduser("~")
                data_dir = os.path.join(data_dir, "MeraBisPro")
            elif sys.platform == "darwin":
                data_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "MeraBisPro")
            else:
                data_dir = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
                data_dir = os.path.join(data_dir, "merabispro")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, "mera_otomasyonu.db")
        return os.path.join(base_dir, "mera_otomasyonu.db")

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # FK kısıtları (örn. ölçüm -> mera cascade silme) bağlantı bazında açılır
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pastures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                district TEXT NOT NULL,
                village TEXT,
                region TEXT NOT NULL,
                area_hectares REAL NOT NULL,
                elevation_m INTEGER,
                bbhb_capacity INTEGER,
                kbhb_capacity INTEGER,
                dry_hay_yield_kg_per_ha REAL,
                vegetation_coverage_pct INTEGER,
                dominant_plants TEXT,
                water_source TEXT,
                soil_type TEXT,
                erosion_risk TEXT,
                allocation_purpose TEXT,
                management_entity TEXT,
                status TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                polygon_coords_json TEXT,
                grazing_season_start TEXT,
                grazing_season_end TEXT,
                notes TEXT
            )
        ''')

        # Eksik kolon varsa tabloyu güncelle (şema sürüm uyumluluğu)
        self._ensure_schema(cursor)

        # Göç/denetim meta verileri tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        # Vejetasyon ölçüm/gözlem kayıtları (mera başına zaman serisi)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vegetation_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pasture_id INTEGER NOT NULL,
                m_date TEXT NOT NULL,
                dry_hay_yield_kg_per_ha REAL,
                vegetation_coverage_pct INTEGER,
                avg_height_cm REAL,
                dominant_plants TEXT,
                observer TEXT,
                method TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (pasture_id) REFERENCES pastures(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_meas_pasture_date "
            "ON vegetation_measurements (pasture_id, m_date)"
        )

        # Ölçüm denetim izi: kim ne zaman ekledi/güncelledi/sildi (kaynak etiketi + alan diff'i)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS measurement_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                measurement_id INTEGER,
                pasture_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'form',
                changed_fields TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (pasture_id) REFERENCES pastures(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_meas_audit_pasture "
            "ON measurement_audit_log (pasture_id, timestamp)"
        )

        # Servis kural sürümü değiştiyse mevcut veriyi otomatik göçür
        self._migrate_rules(cursor)

        cursor.execute("SELECT COUNT(*) FROM pastures")
        count = cursor.fetchone()[0]
        # Örnek veri SADECE ilk çalıştırmada (tablo boşken) yüklenir.
        # NOT: Kullanıcı verilerini asla silme; 81 kayıttan az olması
        # yeniden tohumlama gerekçesi değildir (kullanıcı kayıt silmiş olabilir).
        if count == 0:
            self._seed_81_provinces_data(cursor)

        conn.commit()
        conn.close()

    def _ensure_schema(self, cursor):
        """Eski sürümlerden kalan veritabanlarında eksik kolonları ekler."""
        expected_columns = {
            "code": "TEXT",
            "name": "TEXT",
            "city": "TEXT",
            "district": "TEXT",
            "village": "TEXT",
            "region": "TEXT",
            "area_hectares": "REAL",
            "elevation_m": "INTEGER",
            "bbhb_capacity": "INTEGER",
            "kbhb_capacity": "INTEGER",
            "dry_hay_yield_kg_per_ha": "REAL",
            "vegetation_coverage_pct": "INTEGER",
            "dominant_plants": "TEXT",
            "water_source": "TEXT",
            "soil_type": "TEXT",
            "erosion_risk": "TEXT",
            "allocation_purpose": "TEXT",
            "management_entity": "TEXT",
            "status": "TEXT",
            "lat": "REAL",
            "lng": "REAL",
            "polygon_coords_json": "TEXT",
            "grazing_season_start": "TEXT",
            "grazing_season_end": "TEXT",
            "notes": "TEXT",
        }
        cursor.execute("PRAGMA table_info(pastures)")
        existing = {row[1] for row in cursor.fetchall()}
        for col, decl in expected_columns.items():
            if col not in existing:
                cursor.execute(f"ALTER TABLE pastures ADD COLUMN {col} {decl}")

    def _seed_81_provinces_data(self, cursor):
        provinces = [
            ("Adana", "Çukurova Taban Çayırı Merası", "Seyhan", "Akdeniz", 3200.0, 45, 2500, 14000, 2400.0, 90, 37.0000, 35.3200, "04-01", "11-15"),
            ("Adıyaman", "Nemrut Etekleri Merası", "Kahta", "Güneydoğu Anadolu", 4100.0, 1450, 2100, 16000, 1350.0, 70, 37.7600, 38.2700, "04-15", "10-15"),
            ("Afyonkarahisar", "Frigya Yazılıkaya Otlağı", "İhsaniye", "Ege", 2800.0, 1150, 1500, 11000, 1250.0, 68, 39.0250, 30.5180, "04-15", "09-30"),
            ("Ağrı", "Ağrı Dağı Etekleri Merası", "Doğubayazıt", "Doğu Anadolu", 8900.0, 2250, 4200, 28000, 2100.0, 86, 39.7200, 44.0500, "05-15", "10-05"),
            ("Amasya", "Merzifon Ova Çayırı", "Merzifon", "Karadeniz", 2400.0, 750, 1800, 9500, 1900.0, 82, 40.8700, 35.4600, "04-20", "10-10"),
            ("Ankara", "Polatlı Stepleri Merası", "Polatlı", "İç Anadolu", 6500.0, 870, 1600, 21000, 850.0, 50, 39.5800, 32.1400, "04-01", "07-15"),
            ("Antalya", "Elmalı Gömbe Yaylası Merası", "Elmalı", "Akdeniz", 3100.0, 1850, 1600, 14500, 1550.0, 78, 36.5410, 29.6250, "05-01", "10-15"),
            ("Artvin", "Kafkasör Yaylası Merası", "Merkez", "Karadeniz", 2100.0, 1650, 1900, 6800, 2700.0, 96, 41.1700, 41.8100, "06-01", "09-25"),
            ("Aydın", "Madra Dağı Otlatma Alanı", "Söke", "Ege", 1950.0, 980, 1200, 8900, 1400.0, 72, 37.8500, 27.8400, "04-10", "10-20"),
            ("Balıkesir", "Kazdağı Madra Yayla Merası", "Edremit", "Ege", 2150.0, 1220, 1400, 8500, 1850.0, 82, 39.6580, 26.9450, "04-15", "10-30"),
            ("Bilecik", "Bozüyük Yayla Otlağı", "Bozüyük", "Marmara", 1800.0, 1100, 1300, 7400, 1600.0, 76, 39.9100, 30.0300, "04-20", "10-10"),
            ("Bingöl", "Solhan Murat Dağı Merası", "Solhan", "Doğu Anadolu", 5600.0, 1950, 3100, 21000, 1950.0, 84, 38.9600, 41.0500, "05-10", "10-01"),
            ("Bitlis", "Nemrut Krater Çevresi Merası", "Tatvan", "Doğu Anadolu", 4800.0, 2150, 2800, 18500, 2050.0, 85, 38.6200, 42.2300, "05-15", "09-30"),
            ("Bolu", "Köroğlu Dağları Merası", "Gerede", "Karadeniz", 3400.0, 1480, 2300, 11000, 2200.0, 89, 40.7300, 31.6000, "05-01", "10-15"),
            ("Burdur", "Salda Yayla Otlağı", "Yeşilova", "Akdeniz", 2200.0, 1320, 1400, 9200, 1300.0, 68, 37.5400, 29.7000, "04-25", "10-05"),
            ("Bursa", "Uludağ Yayla Merası", "Keles", "Marmara", 2900.0, 1750, 2100, 9800, 2350.0, 91, 40.1000, 29.1300, "05-15", "10-10"),
            ("Çanakkale", "Kazdağları Orman İçi Mera", "Yenice", "Marmara", 2300.0, 890, 1500, 8200, 1750.0, 80, 39.7500, 26.8500, "04-15", "10-25"),
            ("Çankırı", "Ilgaz Dağları Güney Merası", "Ilgaz", "İç Anadolu", 3100.0, 1620, 1900, 11500, 1700.0, 79, 40.6000, 33.6100, "05-01", "10-05"),
            ("Çorum", "Alaca Ova Merası", "Alaca", "Karadeniz", 3800.0, 950, 2200, 14000, 1450.0, 73, 40.1600, 34.8400, "04-20", "10-01"),
            ("Denizli", "Honaz Dağı Otlatma Alanı", "Honaz", "Ege", 2600.0, 1580, 1700, 10500, 1600.0, 75, 37.7600, 29.2700, "04-25", "10-15"),
            ("Diyarbakır", "Karacadağ Volkanik Otlağı", "Çermik", "Güneydoğu Anadolu", 7200.0, 1250, 3400, 29000, 1100.0, 60, 37.7000, 39.8000, "03-20", "07-01"),
            ("Edirne", "Meriç Taban Çayırları", "Uzunköprü", "Marmara", 3500.0, 60, 2600, 12000, 2500.0, 92, 41.6700, 26.5500, "04-01", "11-01"),
            ("Elazığ", "Hazar Gözü Yayla Merası", "Sivrice", "Doğu Anadolu", 4500.0, 1550, 2700, 17000, 1700.0, 78, 38.4800, 39.4000, "05-01", "10-05"),
            ("Erzincan", "Munzur Dağları Kuzey Merası", "Tercan", "Doğu Anadolu", 6800.0, 1850, 3900, 24000, 2000.0, 87, 39.6000, 39.4500, "05-10", "10-01"),
            ("Erzurum", "Kargapazarı Yayla Merası", "Palandöken", "Doğu Anadolu", 4850.5, 2450, 3200, 18500, 2100.0, 88, 39.8540, 41.3420, "05-15", "09-30"),
            ("Eskişehir", "Seyitgazi Frig Vadisi Merası", "Seyitgazi", "İç Anadolu", 4100.0, 1020, 2100, 14500, 1150.0, 66, 39.4400, 30.6900, "04-15", "09-25"),
            ("Gaziantep", "İslahiye Otlatma Alanı", "İslahiye", "Güneydoğu Anadolu", 2700.0, 650, 1600, 12500, 1300.0, 67, 37.0200, 36.6300, "03-25", "08-15"),
            ("Giresun", "Kümbet Yaylası Merası", "Dereli", "Karadeniz", 2800.0, 1720, 2200, 7900, 2550.0, 94, 40.5600, 38.4300, "06-01", "09-25"),
            ("Gümüşhane", "Zigana Otlatma Alanı", "Torul", "Karadeniz", 2500.0, 1950, 1900, 7100, 2150.0, 86, 40.6300, 39.4000, "05-20", "09-30"),
            ("Hakkari", "Cilo Sat Yaylaları Merası", "Yüksekova", "Doğu Anadolu", 9200.0, 2650, 4100, 31000, 2300.0, 90, 37.4520, 44.1250, "06-01", "09-30"),
            ("Hatay", "Amanos Dağları Yayla Merası", "Dörtyol", "Akdeniz", 2400.0, 1150, 1500, 9800, 1600.0, 76, 36.4000, 36.3500, "04-10", "11-01"),
            ("Isparta", "Davraz Dağı Otlatma Alanı", "Eğirdir", "Akdeniz", 2900.0, 1680, 1800, 11000, 1450.0, 74, 37.7700, 30.7500, "05-01", "10-10"),
            ("Mersin", "Toroslar Yörük Merası", "Mut", "Akdeniz", 3600.0, 1420, 2100, 16500, 1350.0, 70, 36.8000, 34.6200, "04-15", "10-20"),
            ("İstanbul", "Silivri Çayır Merası", "Silivri", "Marmara", 1900.0, 120, 1500, 6800, 2100.0, 88, 41.0700, 28.2400, "04-01", "11-10"),
            ("İzmir", "Ödemiş Bozdağ Yayla Merası", "Ödemiş", "Ege", 2500.0, 1450, 1700, 9200, 1750.0, 79, 38.3500, 28.0800, "04-15", "10-25"),
            ("Kars", "Göle Ova Çayırları Merası", "Göle", "Doğu Anadolu", 6200.0, 2030, 4500, 22000, 2450.0, 92, 40.7850, 42.6050, "05-20", "10-10"),
            ("Kastamonu", "Ilgaz Dağı Yayla Merası", "Tosya", "Karadeniz", 2300.0, 1780, 1700, 7800, 2050.0, 86, 41.0850, 34.0250, "05-15", "10-10"),
            ("Kayseri", "Erciyes Etekleri Develi Otlağı", "Develi", "İç Anadolu", 4100.0, 1420, 2100, 13500, 1350.0, 72, 38.3580, 35.5120, "04-20", "10-01"),
            ("Kırklareli", "Istranca Dağları Merası", "Vize", "Marmara", 2700.0, 680, 1900, 9500, 2200.0, 90, 41.7300, 27.2200, "04-10", "11-05"),
            ("Kırşehir", "Mucur Stepleri Merası", "Mucur", "İç Anadolu", 3900.0, 1050, 1800, 13000, 980.0, 58, 39.0600, 34.3700, "04-05", "08-20"),
            ("Kocaeli", "Samanlı Dağları Yayla Merası", "Kartepe", "Marmara", 1600.0, 1150, 1200, 5400, 2300.0, 93, 40.6500, 29.9800, "04-20", "11-01"),
            ("Konya", "Karapınar Stepleri Merası", "Karapınar", "İç Anadolu", 8400.0, 995, 1200, 14000, 650.0, 45, 37.7120, 33.5480, "04-01", "06-30"),
            ("Kütahya", "Murat Dağı Yayla Merası", "Gediz", "Ege", 3200.0, 1620, 2100, 12000, 1800.0, 81, 38.9500, 29.6000, "05-01", "10-15"),
            ("Malatya", "Hekimhan Yayla Merası", "Hekimhan", "Doğu Anadolu", 4600.0, 1680, 2600, 17500, 1650.0, 77, 38.8200, 38.0700, "05-01", "10-01"),
            ("Manisa", "Spil Dağı Otlatma Alanı", "Şehzadeler", "Ege", 2100.0, 1250, 1400, 8100, 1550.0, 74, 38.5600, 27.4500, "04-15", "10-20"),
            ("Kahramanmaraş", "Ahır Dağı Yayla Merası", "Onikişubat", "Akdeniz", 3800.0, 1750, 2300, 15000, 1600.0, 76, 37.6200, 36.9200, "04-20", "10-15"),
            ("Mardin", "Mazıdağı Otlatma Merası", "Mazıdağı", "Güneydoğu Anadolu", 4300.0, 1080, 2100, 18000, 1050.0, 56, 37.5200, 40.4800, "03-25", "07-15"),
            ("Muğla", "Sandras Dağı Yayla Merası", "Köyceğiz", "Ege", 2300.0, 1820, 1300, 8900, 1650.0, 78, 37.0700, 28.8400, "05-01", "10-25"),
            ("Muş", "Muş Ovası Taban Çayırları", "Merkez", "Doğu Anadolu", 6800.0, 1260, 5200, 19000, 2800.0, 94, 38.7420, 41.5280, "05-01", "10-20"),
            ("Nevşehir", "Cappadocian Stepleri", "Ürgüp", "İç Anadolu", 3100.0, 1180, 1400, 10500, 900.0, 54, 38.6200, 34.7100, "04-10", "08-30"),
            ("Niğde", "Aladağlar Yayla Merası", "Çamardı", "İç Anadolu", 4200.0, 1920, 2200, 14000, 1400.0, 73, 37.8000, 35.1500, "05-05", "10-05"),
            ("Ordu", "Çambaşı Yaylası Merası", "Kabadüz", "Karadeniz", 3300.0, 1850, 2500, 9200, 2600.0, 95, 40.6200, 37.9500, "05-25", "09-30"),
            ("Rize", "Ayder ve Anzer Yaylaları Merası", "İkizdere", "Karadeniz", 3500.0, 2200, 2800, 8500, 2850.0, 97, 40.9500, 41.1000, "06-01", "09-20"),
            ("Sakarya", "Hendek Çiğdem Yaylası", "Hendek", "Marmara", 2000.0, 1380, 1500, 6700, 2250.0, 91, 40.7000, 30.7500, "05-01", "10-25"),
            ("Samsun", "Bafra Kızılırmak Deltası Çayırı", "Bafra", "Karadeniz", 4100.0, 25, 3200, 15000, 2650.0, 95, 41.5800, 35.9000, "04-01", "11-15"),
            ("Siirt", "Pervari Yayla Otlağı", "Pervari", "Güneydoğu Anadolu", 4700.0, 1650, 2500, 20000, 1500.0, 72, 37.9300, 42.5400, "04-15", "10-01"),
            ("Sinop", "Boyabat Dağ Meraları", "Boyabat", "Karadeniz", 2600.0, 980, 1700, 8300, 1950.0, 83, 41.4600, 34.7700, "04-25", "10-15"),
            ("Sivas", "Kangal Çamurlu Yayla Merası", "Kangal", "İç Anadolu", 3900.0, 1650, 2100, 16500, 1400.0, 75, 39.2340, 37.3890, "05-01", "09-15"),
            ("Tekirdağ", "Hayrabolu Çayırları", "Hayrabolu", "Marmara", 2800.0, 110, 2000, 9800, 2200.0, 89, 41.2100, 27.1100, "04-05", "11-01"),
            ("Tokat", "Niksar Çamiçi Yaylası Merası", "Niksar", "Karadeniz", 3000.0, 1350, 2300, 10500, 2100.0, 87, 40.6200, 36.9500, "05-01", "10-10"),
            ("Trabzon", "Kadırga Yaylası Merası", "Tonya", "Karadeniz", 1890.0, 2300, 2400, 6200, 2600.0, 95, 40.6820, 39.1850, "06-01", "09-20"),
            ("Tunceli", "Ovacık Munzur Vadisi Merası", "Ovacık", "Doğu Anadolu", 5400.0, 1420, 3400, 19500, 2200.0, 89, 39.3600, 39.2100, "05-10", "10-05"),
            ("Şanlıurfa", "Ceylanpınar Doğal Otlağı", "Ceylanpınar", "Güneydoğu Anadolu", 12500.0, 380, 1800, 28000, 820.0, 52, 36.8350, 39.9210, "03-01", "06-15"),
            ("Uşak", "Banaz Yayla Merası", "Banaz", "Ege", 2400.0, 1280, 1600, 9400, 1500.0, 74, 38.7400, 29.7400, "04-20", "10-15"),
            ("Van", "Özalp Sugeçer Mera Alanı", "Özalp", "Doğu Anadolu", 7100.0, 2150, 3800, 26000, 1950.0, 84, 38.6540, 43.9850, "05-10", "10-05"),
            ("Yozgat", "Bozok Platosu Otlatma Alanı", "Sorgun", "İç Anadolu", 5400.0, 1280, 2200, 16000, 1100.0, 65, 39.8120, 35.1850, "04-20", "09-25"),
            ("Zonguldak", "Devrek Orman İçi Çayır", "Devrek", "Karadeniz", 1700.0, 450, 1300, 5200, 2250.0, 91, 41.2200, 31.9500, "04-15", "11-01"),
            ("Aksaray", "Hasan Dağı Etekleri Merası", "Güzelyurt", "İç Anadolu", 4500.0, 1480, 2400, 15500, 1150.0, 64, 38.1600, 34.1800, "04-15", "09-20"),
            ("Bayburt", "Kop Dağı Yayla Merası", "Merkez", "Karadeniz", 3600.0, 2150, 2600, 11000, 2050.0, 86, 40.2500, 40.2200, "05-20", "09-25"),
            ("Karaman", "Ayrancı Stepleri Merası", "Ayrancı", "İç Anadolu", 5100.0, 1120, 1500, 17500, 750.0, 48, 37.3600, 33.7000, "04-01", "07-15"),
            ("Kırıkkale", "Keskin Otlatma Alanı", "Keskin", "İç Anadolu", 3200.0, 1100, 1600, 11500, 920.0, 55, 39.6700, 33.6100, "04-05", "08-25"),
            ("Batman", "Sason Yayla Merası", "Sason", "Güneydoğu Anadolu", 3800.0, 1550, 2200, 16000, 1400.0, 70, 38.3300, 41.4100, "04-15", "10-05"),
            ("Şırnak", "Cudi Dağı Otlatma Merası", "Silopi", "Güneydoğu Anadolu", 6100.0, 1780, 3200, 23000, 1300.0, 68, 37.5100, 42.4500, "04-01", "09-30"),
            ("Bartın", "Küre Dağları Orman Çayırı", "Amasra", "Karadeniz", 1900.0, 620, 1400, 6100, 2300.0, 92, 41.6300, 32.3300, "04-20", "11-01"),
            ("Ardahan", "Yalnızçam Yayla Merası", "Merkez", "Doğu Anadolu", 6400.0, 2150, 4100, 21000, 2500.0, 93, 41.1100, 42.7000, "05-20", "10-05"),
            ("Iğdır", "Pamuk Dağı Etekleri Merası", "Tuzluca", "Doğu Anadolu", 3700.0, 1100, 2200, 14500, 1450.0, 71, 39.9200, 44.0400, "04-15", "09-30"),
            ("Yalova", "Armutlu Yayla Merası", "Armutlu", "Marmara", 1200.0, 650, 900, 4100, 2000.0, 88, 40.5200, 28.8300, "04-15", "11-01"),
            ("Karabük", "Safranbolu Yayla Merası", "Safranbolu", "Karadeniz", 2100.0, 1050, 1500, 7200, 2100.0, 87, 41.2500, 32.6800, "04-25", "10-20"),
            ("Kilis", "Elbeyli Otlatma Merası", "Elbeyli", "Güneydoğu Anadolu", 1800.0, 520, 1100, 8500, 1100.0, 58, 36.6700, 37.4600, "03-20", "07-20"),
            ("Osmaniye", "Zorkun Yaylası Merası", "Merkez", "Akdeniz", 2500.0, 1550, 1600, 10500, 1750.0, 81, 37.0200, 36.3500, "04-20", "10-25"),
            ("Düzce", "Yığılca Orman İçi Mera", "Yığılca", "Karadeniz", 1850.0, 780, 1300, 6200, 2400.0, 93, 40.9600, 31.4500, "04-20", "11-01")
        ]

        for idx, (city, name, district, region, area, elev, bbhb, kbhb, yield_val, cov, lat, lng, s_start, s_end) in enumerate(provinces, start=1):
            code = f"MRA-{idx:02d}-01"
            village = "Merkez Köyü"
            dominant_plants = "Yonca, Korunga, Çayır Yumağı, Ak Üçgül, Ot Türleri"
            water_source = "Pınar Kaynakları, Gölet ve Çeşmeler"
            soil_type = "Tınlı Humuslu Verimli Toprak"
            erosion_risk = "Düşük - Orta"
            allocation_purpose = "Büyükbaş ve Küçükbaş Hayvancılık Otlatması"
            management_entity = f"{city} İl Tarım ve Orman Müdürlüğü & Mera Komisyonu"
            status = "Aktif Otlatma" if idx % 5 != 0 else "Dinlendirmede / Islah"
            notes = f"Tarım ve Orman Bakanlığı Çayır Mera Daire Başkanlığı kayıtlı {city} ili resmi mera alanı."
            
            polygon_coords = json.dumps([
                [round(lat + 0.02, 4), round(lng - 0.02, 4)],
                [round(lat + 0.02, 4), round(lng + 0.02, 4)],
                [round(lat - 0.02, 4), round(lng + 0.02, 4)],
                [round(lat - 0.02, 4), round(lng - 0.02, 4)]
            ])

            cursor.execute('''
                INSERT INTO pastures (
                    code, name, city, district, village, region, area_hectares,
                    elevation_m, bbhb_capacity, kbhb_capacity, dry_hay_yield_kg_per_ha,
                    vegetation_coverage_pct, dominant_plants, water_source, soil_type,
                    erosion_risk, allocation_purpose, management_entity, status,
                    lat, lng, polygon_coords_json, grazing_season_start, grazing_season_end, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code, name, city, district, village, region, area,
                elev, bbhb, kbhb, yield_val, cov, dominant_plants,
                water_source, soil_type, erosion_risk, allocation_purpose,
                management_entity, status, lat, lng, polygon_coords, s_start, s_end, notes
            ))

    # ---------- Vejetasyon Ölçüm / Gözlem Kayıtları ----------

    _AUDIT_FIELDS = (
        "m_date", "dry_hay_yield_kg_per_ha", "vegetation_coverage_pct",
        "avg_height_cm", "dominant_plants", "observer", "method", "notes",
    )

    @staticmethod
    def _audit_field_changes(old, new):
        """Değişen alanları 'alan: eski → yeni' metinleri olarak döndürür."""
        changes = []
        for f in DatabaseManager._AUDIT_FIELDS:
            ov = old.get(f)
            nv = new.get(f)
            if ov != nv:
                changes.append(f"{f}: {ov if ov is not None else '—'} → "
                               f"{nv if nv is not None else '—'}")
        return changes

    def _log_measurement_audit(self, conn, action, pasture_id, measurement_id,
                               source, changed_fields=None):
        """Denetim izi satırı yazar (çağıran bağlantıda, aynı işlemde).

        Log hatası ana işlemi asla bozmaz — denetim izi ikincil veridir.
        """
        try:
            conn.execute(
                "INSERT INTO measurement_audit_log "
                "(measurement_id, pasture_id, action, source, changed_fields, "
                "timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (measurement_id, int(pasture_id), action, source or "form",
                 json.dumps(changed_fields or [], ensure_ascii=False),
                 datetime.now().isoformat(timespec="seconds")),
            )
        except Exception as exc:
            LOG.warning("Denetim izi yazılamadı (işlem etkilenmedi): %s", exc)

    def add_measurement(self, data, source="form"):
        """Yeni ölçüm kaydı ekler; yeni kaydın id'sini döndürür.

        source: 'form' (gömülü form), 'map' (harita popup'ı), 'menu' (Araçlar menüsü).
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO vegetation_measurements (
                    pasture_id, m_date, dry_hay_yield_kg_per_ha,
                    vegetation_coverage_pct, avg_height_cm, dominant_plants,
                    observer, method, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    int(data["pasture_id"]),
                    str(data.get("m_date") or datetime.now().strftime("%Y-%m-%d")),
                    data.get("dry_hay_yield_kg_per_ha"),
                    data.get("vegetation_coverage_pct"),
                    data.get("avg_height_cm"),
                    data.get("dominant_plants"),
                    data.get("observer"),
                    data.get("method"),
                    data.get("notes"),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            new_id = cursor.lastrowid
            self._log_measurement_audit(conn, "add", data["pasture_id"],
                                        new_id, source)
            conn.commit()
            return new_id
        finally:
            conn.close()

    def get_measurements(self, pasture_id, order="ASC"):
        """Meranın ölçümlerini tarih sırasıyla döndürür (order: 'ASC'|'DESC')."""
        conn = self.get_connection()
        try:
            direction = "DESC" if str(order).upper() == "DESC" else "ASC"
            rows = conn.execute(
                f"SELECT * FROM vegetation_measurements WHERE pasture_id = ? "
                f"ORDER BY m_date {direction}, id {direction}",
                (pasture_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_measurement(self, measurement_id, data, source="form"):
        """Ölçüm kaydını günceller; değişen alanları denetim izine yazar."""
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM vegetation_measurements WHERE id = ?",
                (measurement_id,),
            ).fetchone()
            old = dict(row) if row else {}
            pasture_id = old.get("pasture_id") or data.get("pasture_id")
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE vegetation_measurements SET
                    m_date=?, dry_hay_yield_kg_per_ha=?, vegetation_coverage_pct=?,
                    avg_height_cm=?, dominant_plants=?, observer=?, method=?, notes=?
                WHERE id=?
                ''',
                (
                    str(data.get("m_date") or datetime.now().strftime("%Y-%m-%d")),
                    data.get("dry_hay_yield_kg_per_ha"),
                    data.get("vegetation_coverage_pct"),
                    data.get("avg_height_cm"),
                    data.get("dominant_plants"),
                    data.get("observer"),
                    data.get("method"),
                    data.get("notes"),
                    measurement_id,
                ),
            )
            if pasture_id is not None:
                changes = (self._audit_field_changes(old, data)
                           if old else ["*"])
                self._log_measurement_audit(
                    conn, "update", pasture_id, measurement_id, source, changes)
            conn.commit()
        finally:
            conn.close()

    def delete_measurement(self, measurement_id, source="form"):
        """Ölçüm kaydını siler; silinen kaydı denetim izine yazar."""
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT pasture_id FROM vegetation_measurements WHERE id = ?",
                (measurement_id,),
            ).fetchone()
            pasture_id = row[0] if row else None
            conn.execute(
                "DELETE FROM vegetation_measurements WHERE id = ?", (measurement_id,)
            )
            if pasture_id is not None:
                self._log_measurement_audit(
                    conn, "delete", pasture_id, measurement_id, source)
            conn.commit()
        finally:
            conn.close()

    def get_measurement_audit_log(self, pasture_id=None, limit=100,
                                  source=None, date_from=None, date_to=None):
        """Denetim izini döndürür: en yeni önce, mera kodu/adıyla birleşik.

        pasture_id verilirse yalnızca o meranın izleri; yoksa tümü (limit ile).
        Kaynak etiketi ve değişen alanlar (diff) dahil.

        İsteğe bağlı filtreler (geriye uyumlu — tümü None ise davranış aynı):
          source     : 'map' / 'menu' / 'form' — yalnızca o kaynağın izleri
          date_from  : 'YYYY-MM-DD' — timestamp >= bu günün 00:00:00'ı (dahil)
          date_to    : 'YYYY-MM-DD' — timestamp <= bu günün 23:59:59'u (dahil)
        """
        conn = self.get_connection()
        try:
            base = ("SELECT l.*, p.code AS pasture_code, p.name AS pasture_name "
                    "FROM measurement_audit_log l "
                    "JOIN pastures p ON p.id = l.pasture_id ")
            clauses, params = [], []
            if pasture_id is not None:
                clauses.append("l.pasture_id = ?")
                params.append(pasture_id)
            if source:
                clauses.append("l.source = ?")
                params.append(str(source))
            # ISO timestamp sözlüksel karşılaştırması kronolojik sıraya denktir;
            # üst sınır ertesi gün (ayrı `T`/boşluk ve mikrosaniyeden bağımsız):
            # `timestamp < gün+1` tüm o-günü kayıtlarını güvenle kapsar.
            if date_from:
                clauses.append("l.timestamp >= ?")
                params.append(str(date_from))
            if date_to:
                upper = (datetime.strptime(str(date_to), "%Y-%m-%d")
                         + timedelta(days=1)).strftime("%Y-%m-%d")
                clauses.append("l.timestamp < ?")
                params.append(upper)
            where = ("WHERE " + " AND ".join(clauses) + " ") if clauses else ""
            params.append(int(limit))
            rows = conn.execute(
                base + where + "ORDER BY l.timestamp DESC, l.id DESC LIMIT ?",
                params,
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["changed_fields"] = json.loads(d.get("changed_fields") or "[]")
                except (ValueError, TypeError):
                    d["changed_fields"] = []
                out.append(d)
            return out
        finally:
            conn.close()

    def latest_measurement(self, pasture_id):
        """Meranın en güncel ölçümünü döndürür (yoksa None)."""
        rows = self.get_measurements(pasture_id, order="DESC")
        return rows[0] if rows else None

    def measurements_export_rows(self):
        """Tüm ölçümleri mera kodu/adıyla birleştirilmiş olarak döndürür (dışa aktarma için)."""
        conn = self.get_connection()
        try:
            rows = conn.execute(
                '''
                SELECT m.*, p.code AS pasture_code, p.name AS pasture_name,
                       p.city AS pasture_city
                FROM vegetation_measurements m
                JOIN pastures p ON p.id = m.pasture_id
                ORDER BY p.code, m.m_date, m.id
                '''
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_all_pastures(self, filters=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM pastures WHERE 1=1"
        params = []

        if filters:
            if filters.get("city") and filters["city"] != "Tümü":
                query += " AND city = ?"
                params.append(filters["city"])
            if filters.get("region") and filters["region"] != "Tümü":
                query += " AND region = ?"
                params.append(filters["region"])
            if filters.get("status") and filters["status"] != "Tümü":
                query += " AND status = ?"
                params.append(filters["status"])
            if filters.get("search"):
                term = f"%{filters['search']}%"
                query += " AND (name LIKE ? OR code LIKE ? OR district LIKE ? OR city LIKE ? OR dominant_plants LIKE ?)"
                params.extend([term, term, term, term, term])

        query += " ORDER BY id ASC"
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_pasture_by_id(self, pasture_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pastures WHERE id = ?", (pasture_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_pasture(self, data):
        data = dict(data)
        data["code"] = self.normalize_code(data.get("code", ""))
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pastures (
                code, name, city, district, village, region, area_hectares,
                elevation_m, bbhb_capacity, kbhb_capacity, dry_hay_yield_kg_per_ha,
                vegetation_coverage_pct, dominant_plants, water_source, soil_type,
                erosion_risk, allocation_purpose, management_entity, status,
                lat, lng, polygon_coords_json, grazing_season_start, grazing_season_end, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get("code"), data.get("name"), data.get("city"), data.get("district"),
            data.get("village"), data.get("region"), data.get("area_hectares", 0.0),
            data.get("elevation_m", 0), data.get("bbhb_capacity", 0), data.get("kbhb_capacity", 0),
            data.get("dry_hay_yield_kg_per_ha", 0.0), data.get("vegetation_coverage_pct", 0),
            data.get("dominant_plants", ""), data.get("water_source", ""), data.get("soil_type", ""),
            data.get("erosion_risk", ""), data.get("allocation_purpose", ""), data.get("management_entity", ""),
            data.get("status", "Aktif Otlatma"), data.get("lat", 39.0), data.get("lng", 35.0),
            data.get("polygon_coords_json", "[]"), data.get("grazing_season_start", "05-01"),
            data.get("grazing_season_end", "10-01"), data.get("notes", "")
        ))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def update_pasture(self, pasture_id, data):
        data = dict(data)
        data["code"] = self.normalize_code(data.get("code", ""))
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pastures SET
                code=?, name=?, city=?, district=?, village=?, region=?, area_hectares=?,
                elevation_m=?, bbhb_capacity=?, kbhb_capacity=?, dry_hay_yield_kg_per_ha=?,
                vegetation_coverage_pct=?, dominant_plants=?, water_source=?, soil_type=?,
                erosion_risk=?, allocation_purpose=?, management_entity=?, status=?,
                lat=?, lng=?, polygon_coords_json=?, grazing_season_start=?, grazing_season_end=?, notes=?
            WHERE id=?
        ''', (
            data.get("code"), data.get("name"), data.get("city"), data.get("district"),
            data.get("village"), data.get("region"), data.get("area_hectares", 0.0),
            data.get("elevation_m", 0), data.get("bbhb_capacity", 0), data.get("kbhb_capacity", 0),
            data.get("dry_hay_yield_kg_per_ha", 0.0), data.get("vegetation_coverage_pct", 0),
            data.get("dominant_plants", ""), data.get("water_source", ""), data.get("soil_type", ""),
            data.get("erosion_risk", ""), data.get("allocation_purpose", ""), data.get("management_entity", ""),
            data.get("status", "Aktif Otlatma"), data.get("lat", 39.0), data.get("lng", 35.0),
            data.get("polygon_coords_json", "[]"), data.get("grazing_season_start", "05-01"),
            data.get("grazing_season_end", "10-01"), data.get("notes", ""),
            pasture_id
        ))
        conn.commit()
        conn.close()

    def delete_pasture(self, pasture_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pastures WHERE id = ?", (pasture_id,))
        conn.commit()
        conn.close()

    # ---------- Yedekleme & Geri Yükleme ----------

    def get_db_info(self):
        """Veritabanı dosyası hakkında bilgi döndürür."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pastures")
            count = cursor.fetchone()[0] or 0
        finally:
            conn.close()
        size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        mtime = os.path.getmtime(self.db_path) if os.path.exists(self.db_path) else 0.0
        return {
            "path": self.db_path,
            "size": size,
            "modified": mtime,
            "count": count,
        }

    def get_backup_dir(self):
        """Yedeklerin tutulduğu klasörü döndürür (yoksa oluşturur)."""
        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    def backup_to(self, file_path):
        """Veritabanını tutarlı bir anlık görüntü olarak yedekler (sqlite backup API)."""
        src = sqlite3.connect(self.db_path)
        try:
            dst = sqlite3.connect(file_path)
            try:
                with dst:
                    src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        return True

    def restore_from(self, file_path):
        """
        Yedek dosyasını doğrular ve mevcut veritabanını onunla değiştirir.
        Geçersiz dosya için ValueError, bulunamayan dosya için FileNotFoundError fırlatır.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Yedek dosyası bulunamadı: {file_path}")
        with open(file_path, "rb") as f:
            header = f.read(16)
        if header[:15] != b"SQLite format 3":
            raise ValueError("Seçilen dosya geçerli bir SQLite veritabanı değil.")
        check = sqlite3.connect(file_path)
        try:
            table = check.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pastures'"
            ).fetchone()
        finally:
            check.close()
        if not table:
            raise ValueError("Dosyada 'pastures' tablosu bulunamadı; geçerli bir yedek dosyası seçin.")
        shutil.copy2(file_path, self.db_path)
        self.init_db()  # şema kontrolü + (boşsa) ilk veri
        return True

    def list_backups(self):
        """Yedek klasöründeki dosyaları en yeni önce olacak şekilde listeler."""
        backup_dir = self.get_backup_dir()
        entries = []
        for name in os.listdir(backup_dir):
            if name.lower().endswith((".db", ".sqlite", ".sqlite3")):
                path = os.path.join(backup_dir, name)
                try:
                    entries.append({
                        "name": name,
                        "path": path,
                        "size": os.path.getsize(path),
                        "modified": os.path.getmtime(path),
                    })
                except OSError:
                    continue
        entries.sort(key=lambda e: e["modified"], reverse=True)
        return backup_dir, entries

    @staticmethod
    def normalize_text(text):
        """Metni normalleştirir (ortak doğrulama servisi)."""
        return _norm_text(text)

    @staticmethod
    def normalize_code(code):
        """Kodu normalleştirir (ortak doğrulama servisi). 'mra-01-01 ' = 'MRA-01-01'."""
        return _norm_code(code)

    # ---------- Kural Sürümü & Veri Göçü ----------

    @staticmethod
    def _get_rule_version(cursor):
        """Veritabanına yazılmış kural sürümünü okur (PRAGMA user_version)."""
        row = cursor.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _set_rule_version(cursor, version):
        """Uygulanmış kural sürümünü yazar (PRAGMA user_version, tam sayı)."""
        cursor.execute("PRAGMA user_version = %d" % int(version))

    def _migrate_rules(self, cursor):
        """
        Servis kural seti (validation.RULES_VERSION) yükseldiyse mevcut veriyi
        otomatik göçürür: eksik sürüm adımları sırayla uygulanır, sonuç meta
        tablosuna kaydedilir ve sürüm güncellenir. Yedekten geri yükleme eski
        sürümlü bir dosya getirirse init_db üzerinden göç otomatik yeniden çalışır.
        """
        current = self._get_rule_version(cursor)
        if current >= _RULES_VERSION:
            return
        rows = cursor.execute("SELECT * FROM pastures ORDER BY id").fetchall()
        records = [dict(row) for row in rows]
        report = _apply_rule_migrations(
            records, from_version=current, to_version=_RULES_VERSION
        )
        for upd in report["updates"]:
            cursor.execute(
                "UPDATE pastures SET code = ? WHERE id = ?",
                (upd["code"], upd["id"]),
            )
        self._set_rule_version(cursor, _RULES_VERSION)
        report["date"] = datetime.now().isoformat(timespec="seconds")
        cursor.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("last_rule_migration", json.dumps(report, ensure_ascii=False)),
        )
        # Göçü atomik yap: UPDATE'ler ve PRAGMA user_version yazımı, çağıran
        # taraf commit etmese bile kalıcı olsun (init_db dışındaki çağrılar
        # örn. pre_backup_check/ensure_migrated bağlantıyı commit'siz kapatır).
        cursor.connection.commit()
        return report

    def get_rule_version(self):
        """Veritabanına uygulanmış kural seti sürümü (validation.RULES_VERSION)."""
        conn = self.get_connection()
        try:
            return self._get_rule_version(conn.cursor())
        finally:
            conn.close()

    def ensure_migrated(self):
        """Kural sürümü güncel değilse veri göçünü otomatik çalıştırır.

        True dönerse sürüm güncel; False dönerse göç başarısız/uyumsuz.
        """
        conn = self.get_connection()
        try:
            self._migrate_rules(conn.cursor())
        finally:
            conn.close()
        return self.get_rule_version() == _RULES_VERSION

    def pre_backup_check(self):
        """Yedeklemeden önce bakım ön-kontrolü.

        Bekleyen kural göçünü otomatik çalıştırır, sürümü doğrular ve rapor
        döndürür. Yedekleme akışı bu kontrolü geçmeden yedek almaz.

        Dönen rapor:
          {ok, rule_version, expected_version, migrated, last_migration}
        """
        conn = self.get_connection()
        try:
            before = self._get_rule_version(conn.cursor())
            self._migrate_rules(conn.cursor())
        finally:
            conn.close()
        after = self.get_rule_version()
        return {
            "ok": after == _RULES_VERSION,
            "rule_version": after,
            "expected_version": _RULES_VERSION,
            "migrated": before != after,
            "last_migration": self.get_last_migration_info(),
        }

    def get_last_migration_info(self):
        """Son kural göçü raporunu döndürür (göç hiç çalışmadıysa None)."""
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'last_rule_migration'"
            ).fetchone()
            return json.loads(row["value"]) if row else None
        finally:
            conn.close()

    def get_taken_codes(self, exclude_id=None):
        """Veritabanındaki tüm mera kodlarının normalleştirilmiş seti.
        Doğrulama servisiyle birlikte çakışma denetimi için kullanılır."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if exclude_id is not None:
                cursor.execute("SELECT code FROM pastures WHERE id != ?", (exclude_id,))
            else:
                cursor.execute("SELECT code FROM pastures")
            return {self.normalize_code(row["code"]) for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_taken_name_city_pairs(self, exclude_id=None):
        """Veritabanındaki (normalleştirilmiş il, normalleştirilmiş ad) çiftlerinin seti."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if exclude_id is not None:
                cursor.execute("SELECT name, city FROM pastures WHERE id != ?", (exclude_id,))
            else:
                cursor.execute("SELECT name, city FROM pastures")
            return {
                (self.normalize_text(row["name"]), self.normalize_text(row["city"]))
                for row in cursor.fetchall()
            }
        finally:
            conn.close()

    def code_exists(self, code, exclude_id=None):
        """Kod zaten başka bir kayıtta kullanılıyor mu? (düzenlemede kendi kaydı hariç tutulur)
        Karşılaştırma büyük/küçük harf ve boşluk farklarını yok sayar (ortak servis kuralı)."""
        code = self.normalize_code(code)
        if not code:
            return False
        return code in self.get_taken_codes(exclude_id=exclude_id)

    def audit_consistency(self):
        """Tüm kayıtları kural setine göre toplu denetler ve rapor üretir.

        Rapor biçimi validation.audit_all_records çıktısıyla aynıdır:
        {total, ok, with_issues, issues, summary, severity}. Mesajlar aktif
        dile göre (MessageCatalog) üretilir.
        """
        return _audit_all_records(self.get_all_pastures())

    def audit_polygon_consistency(self, threshold=geometry.DEFAULT_THRESHOLD):
        """Poligon geometrisi ile kayıtlı alan arasındaki uyumu denetler.

        Yalnızca hesaplanan alanı min_ha (1 ha) üstünde olan poligonlar
        denetlenir — seed/örnek verideki küçük yer tutucu poligonlar raporu
        doldurmasın. Dönüş: database/geometry.audit_polygon_consistency.
        """
        return geometry.audit_polygon_consistency(
            self.get_all_pastures(), threshold=threshold)

    def search_codes(self, prefix, limit=10):
        """Verilen önekle başlayan mevcut mera kodlarını döndürür (autocomplete için).
        Önek normalleştirilerek karşılaştırılır; sonuçlar koda göre sıralı ve sınırlıdır."""
        prefix = self.normalize_code(prefix)
        if not prefix:
            return []
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT code FROM pastures WHERE code LIKE ? ORDER BY code LIMIT ?",
                (prefix + "%", limit)
            )
            return [row["code"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def name_exists_in_city(self, name, city, exclude_id=None):
        """Aynı ilde aynı adla başka bir mera var mı? (harf/boşluk farklarını yok sayar)
        Karşılaştırma ortak doğrulama servisinin normalleştirmesiyle yapılır."""
        pair = (self.normalize_text(name), self.normalize_text(city))
        if not pair[0] or not pair[1]:
            return False
        return pair in self.get_taken_name_city_pairs(exclude_id=exclude_id)

    def get_random_code(self, exclude_id=None):
        """Rastgele ama biçimli ve veritabanında benzersiz bir mera kodu üretir."""
        for _ in range(100):
            code = f"MRA-{random.randint(1, 999):02d}-{random.randint(1, 99):02d}"
            if not self.code_exists(code, exclude_id=exclude_id):
                return code
        # Çok sayıda deneme sonucu çakışma olursa sıralı koda dön
        return self.get_next_code()

    def get_next_code(self):
        """Yeni kayıt için benzersiz bir mera kodu üretir (örn. MRA-82-01)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM pastures")
        max_num = 0
        for (code,) in cursor.fetchall():
            parts = code.split("-")
            if len(parts) == 3 and parts[0] == "MRA" and parts[1].isdigit():
                max_num = max(max_num, int(parts[1]))
        conn.close()
        return f"MRA-{max_num + 1:02d}-01"

    def get_statistics(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*), SUM(area_hectares), SUM(bbhb_capacity), SUM(kbhb_capacity) FROM pastures")
        total_count, total_area, total_bbhb, total_kbhb = cursor.fetchone()

        cursor.execute("SELECT region, COUNT(*) AS count, SUM(area_hectares) AS total_area FROM pastures GROUP BY region")
        region_stats = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT city, COUNT(*) AS count, SUM(area_hectares) AS total_area FROM pastures GROUP BY city ORDER BY total_area DESC LIMIT 10")
        city_stats = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT status, COUNT(*) AS count FROM pastures GROUP BY status")
        status_stats = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return {
            "total_count": total_count or 0,
            "total_area": round(total_area or 0, 1),
            "total_bbhb": total_bbhb or 0,
            "total_kbhb": total_kbhb or 0,
            "region_stats": region_stats,
            "city_stats": city_stats,
            "status_stats": status_stats
        }

    def export_to_csv(self, file_path):
        pastures = self.get_all_pastures()
        if not pastures:
            return False
        headers = pastures[0].keys()
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(pastures)
        return True

    def export_to_json(self, file_path):
        pastures = self.get_all_pastures()
        if not pastures:
            return False
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(pastures, f, ensure_ascii=False, indent=2)
        return True
