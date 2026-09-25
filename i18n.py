"""Merkezi çeviri (i18n) modülü — tüm arayüz metinleri tek katalogda (tr/en).

- `T` (Translator tekil nesnesi): `T.set_language("en")` ile dil değişir;
  aynı çağrı doğrulama mesajlarını da senkronize eder (MessageCatalog).
- `T.get("key", **fmt)`: aktif dildeki metni döndürür (format argümanlarıyla).
- `T.get_list("months")`: liste tipindeki çeviriler (ay, hafta günü adları).

Görünümler `retranslate()` metoduyla kendi statik metinlerini günceller;
MainWindow dil değişince tüm görünümlerin retranslate() yöntemini çağırır.
"""

from database.validation import MessageCatalog

# Kural sürümü gibi sabitler değişmedi; sadece çeviri kataloğu burada.


class Translator:
    """Tüm arayüz metinlerinin tek çeviri kataloğu (Türkçe/İngilizce)."""

    _lang = "tr"

    _strings = {
        # ---- Ana pencere / kenar çubuğu ----
        "window.title": {
            "tr": "Türkiye Mera ve Otlatma Alanları Bilgi Sistemi (MERA-BİS PRO)",
            "en": "Turkey Pasture and Grazing Areas Information System (MERA-BIS PRO)",
        },
        "sidebar.subtitle": {
            "tr": "Türkiye Mera Bilgi Sistemi",
            "en": "Turkey Pasture Information System",
        },
        "nav.map": {"tr": "🌍 Harita Görünümü", "en": "🌍 Map View"},
        "nav.analytics": {"tr": "📊 Analiz & İstatistik", "en": "📊 Analytics & Statistics"},
        "nav.table": {"tr": "📋 Mera Veri Listesi", "en": "📋 Pasture Data List"},
        "nav.calc": {"tr": "🧮 Otlatma Hesaplayıcısı", "en": "🧮 Grazing Calculator"},
        "nav.rotation": {"tr": "🔄 Rotasyon Planı", "en": "🔄 Rotation Plan"},
        "nav.backup": {"tr": "💾 Yedekleme", "en": "💾 Backup"},
        "nav.audit": {"tr": "🔎 Veri Denetimi", "en": "🔎 Data Audit"},
        "nav.about": {"tr": "ℹ️ Hakkında", "en": "ℹ️ About"},
        "sidebar.quick_title": {
            "tr": "Türkiye Mera Özeti (81 İl)",
            "en": "Turkey Pasture Summary (81 Provinces)",
        },
        "sidebar.stats_count": {"tr": "{n} Kayıtlı Mera", "en": "{n} Registered Pastures"},
        "footer.programmer": {
            "tr": "Programlayan: kagnx",
            "en": "Programmed by: kagnx",
        },
        "footer.role": {"tr": "Kaldırım Mühendisi", "en": "Sidewalk Engineer"},
        "footer.copyright": {
            "tr": "Copyright © 2026 - Her Hakkı Saklıdır!  D :D :D",
            "en": "Copyright © 2026 - All Rights Reserved!  D :D :D",
        },
        "msg.error_title": {"tr": "Hata", "en": "Error"},
        "msg.add_error": {
            "tr": "Kayıt eklenirken bir hata oluştu:\n{exc}",
            "en": "An error occurred while adding the record:\n{exc}",
        },
        "msg.code_in_use": {
            "tr": "'{code}' kodu zaten kullanılıyor. Lütfen farklı bir kod girin.",
            "en": "The code '{code}' is already in use. Please enter a different code.",
        },
        "msg.update_error": {
            "tr": "Kayıt güncellenirken bir hata oluştu:\n{exc}",
            "en": "An error occurred while updating the record:\n{exc}",
        },
        "msg.code_used_edit": {
            "tr": "'{code}' kodu başka bir mera tarafından kullanılıyor. Lütfen farklı bir kod girin.",
            "en": "The code '{code}' is used by another pasture. Please enter a different code.",
        },
        "msg.delete_confirm_title": {"tr": "Silme Onayı", "en": "Delete Confirmation"},
        "msg.delete_confirm": {
            "tr": "Bu mera kaydını silmek istediğinizden emin misiniz?",
            "en": "Are you sure you want to delete this pasture record?",
        },
        "msg.delete_error": {
            "tr": "Kayıt silinirken bir hata oluştu:\n{exc}",
            "en": "An error occurred while deleting the record:\n{exc}",
        },

        # ---- Harita (map_template.html) ----
        "map.btn_street": {"tr": "📍 Standart Harita", "en": "📍 Standard Map"},
        "map.btn_satellite": {"tr": "🌍 Google Earth / Uydu", "en": "🌍 Google Earth / Satellite"},
        "map.btn_hybrid": {"tr": "🗺️ Karma (Uydu + Etiket)", "en": "🗺️ Hybrid (Satellite + Labels)"},
        "map.btn_topo": {"tr": "⛰️ Topoğrafik", "en": "⛰️ Topographic"},
        "map.btn_reset": {"tr": "🇹🇷 Türkiye Tam Ekran", "en": "🇹🇷 Turkey Full Screen"},
        "map.btn_provinces": {"tr": "🗺️ İl Sınırları", "en": "🗺️ Province Borders"},
        "map.btn_settlements": {"tr": "🏘️ Yerleşim", "en": "🏘️ Settlements"},
        "map.btn_rivers": {"tr": "💧 Akarsu", "en": "💧 Rivers"},
        "map.popup_code": {"tr": "Kod", "en": "Code"},
        "map.popup_area": {"tr": "Yüzölçümü", "en": "Area"},
        "map.popup_elevation": {"tr": "Rakım", "en": "Elevation"},
        "map.popup_capacity": {"tr": "Otlatma Kapasitesi", "en": "Grazing Capacity"},
        "map.popup_vegetation": {"tr": "Vejetasyon Örtüsü", "en": "Vegetation Coverage"},
        "map.popup_status": {"tr": "Durum", "en": "Status"},
        "map.popup_inspect": {"tr": "🔍 Detayları İncele", "en": "🔍 Inspect Details"},
        "map.popup_hectare": {"tr": "Hektar", "en": "Hectares"},
        "map.province_popup": {"tr": "Türkiye İl Sınırı", "en": "Turkey Province Border"},

        # ---- Veri listesi ----
        "table.search_placeholder": {
            "tr": "🔍 Mera adı, kod, il, ilçe veya bitki ara...",
            "en": "🔍 Search by pasture name, code, city, district or plant...",
        },
        "table.city_all": {"tr": "İl: Tümü", "en": "City: All"},
        "table.region_all": {"tr": "Bölge: Tümü", "en": "Region: All"},
        "table.status_all": {"tr": "Durum: Tümü", "en": "Status: All"},
        "table.add_btn": {"tr": "➕ Yeni Mera Ekle", "en": "➕ Add New Pasture"},
        "table.export_csv": {"tr": "📊 CSV Aktar", "en": "📊 Export CSV"},
        "table.export_json": {"tr": "🧾 JSON Aktar", "en": "🧾 Export JSON"},
        "table.h_id": {"tr": "ID", "en": "ID"},
        "table.h_code": {"tr": "Kod", "en": "Code"},
        "table.h_name": {"tr": "Mera Adı", "en": "Pasture Name"},
        "table.h_city": {"tr": "İl", "en": "City"},
        "table.h_district": {"tr": "İlçe", "en": "District"},
        "table.h_region": {"tr": "Bölge", "en": "Region"},
        "table.h_area": {"tr": "Alan (Ha)", "en": "Area (Ha)"},
        "table.h_elevation": {"tr": "Rakım (m)", "en": "Elevation (m)"},
        "table.h_bbhb": {"tr": "BBHB Kapasite", "en": "BBHB Capacity"},
        "table.h_kbhb": {"tr": "KBHB Kapasite", "en": "KBHB Capacity"},
        "table.h_yield": {"tr": "Ot Verimi (kg/ha)", "en": "Hay Yield (kg/ha)"},
        "table.h_status": {"tr": "Durum", "en": "Status"},
        "table.count_fmt": {"tr": "Toplam Mera Sayısı: {n}", "en": "Total Pasture Count: {n}"},
        "table.area_fmt": {
            "tr": "Filtrelenen Toplam Alan: {n:,.0f} Ha",
            "en": "Filtered Total Area: {n:,.0f} Ha",
        },
        "table.dlg_csv": {"tr": "Mera Verilerini CSV Aktar", "en": "Export Pasture Data as CSV"},
        "table.dlg_json": {"tr": "Mera Verilerini JSON Aktar", "en": "Export Pasture Data as JSON"},
        "table.msg_success": {"tr": "Başarılı", "en": "Success"},
        "table.msg_exported": {
            "tr": "Veriler başarıyla dışa aktarıldı:\n{path}",
            "en": "Data exported successfully:\n{path}",
        },
        "table.msg_no_data": {
            "tr": "Dışa aktarılacak mera verisi bulunamadı.",
            "en": "No pasture data to export.",
        },

        # ---- Mera detay paneli ----
        "detail.title": {"tr": "Mera Detay Kartı", "en": "Pasture Detail Card"},
        "detail.no_pasture": {"tr": "Mera Seçilmedi", "en": "No Pasture Selected"},
        "detail.location": {"tr": "Konum Bilgisi", "en": "Location"},
        "detail.tab_general": {"tr": "📍 Genel", "en": "📍 General"},
        "detail.tab_veg": {"tr": "🌾 Vejetasyon", "en": "🌾 Vegetation"},
        "detail.tab_soil": {"tr": "💧 Toprak & Su", "en": "💧 Soil & Water"},
        "detail.tab_notes": {"tr": "📝 İdari & Not", "en": "📝 Admin & Notes"},
        "detail.btn_zoom": {"tr": "🎯 Haritada Odaklan", "en": "🎯 Focus on Map"},
        "detail.btn_edit": {"tr": "✏️ Düzenle", "en": "✏️ Edit"},
        "detail.btn_delete": {"tr": "🗑️ Sil", "en": "🗑️ Delete"},
        "detail.lbl_code": {"tr": "Mera Kodu", "en": "Pasture Code"},
        "detail.lbl_area": {"tr": "Yüzölçümü", "en": "Area"},
        "detail.lbl_elevation": {"tr": "Ortalama Rakım", "en": "Average Elevation"},
        "detail.lbl_coord": {"tr": "Coğrafi Koordinat", "en": "Geographic Coordinates"},
        "detail.lbl_season": {"tr": "Otlatma Sezonu", "en": "Grazing Season"},
        "detail.lbl_allocation": {"tr": "Tahsis Amacı", "en": "Allocation Purpose"},
        "detail.lbl_bbhb": {"tr": "Büyükbaş Kapasitesi (BBHB)", "en": "Cattle Capacity (BBHB)"},
        "detail.lbl_kbhb": {"tr": "Küçükbaş Kapasitesi (KBHB)", "en": "Sheep Capacity (KBHB)"},
        "detail.lbl_yield": {"tr": "Kuru Ot Verimi", "en": "Dry Hay Yield"},
        "detail.lbl_coverage": {
            "tr": "Vejetasyon Kaplama Oranı: %{pct}",
            "en": "Vegetation Coverage Rate: %{pct}",
        },
        "detail.lbl_plants": {"tr": "Dominant Yem Bitkileri", "en": "Dominant Forage Plants"},
        "detail.lbl_soil": {"tr": "Toprak Yapısı Tipi", "en": "Soil Type"},
        "detail.lbl_water": {"tr": "Su Kaynakları Durumu", "en": "Water Resources Status"},
        "detail.lbl_erosion": {"tr": "Erozyon Riski Derecesi", "en": "Erosion Risk Level"},
        "detail.lbl_management": {
            "tr": "Yönetim / İşletici Birlik",
            "en": "Management / Operating Union",
        },
        "detail.lbl_notes": {
            "tr": "Özel Notlar & Islah Bilgisi",
            "en": "Special Notes & Improvement Info",
        },
        "detail.no_notes": {"tr": "Kayıtlı not yok.", "en": "No notes recorded."},
        "detail.area_fmt": {
            "tr": "{area} Hektar ({dekar} Dekar)",
            "en": "{area} Hectares ({dekar} Decares)",
        },
        "detail.elev_fmt": {"tr": "{elev} metre", "en": "{elev} meters"},
        "detail.coord_fmt": {"tr": "{lat:.4f}° N, {lng:.4f}° E", "en": "{lat:.4f}° N, {lng:.4f}° E"},
        "detail.season_fmt": {
            "tr": "{start} ile {end} arası",
            "en": "between {start} and {end}",
        },
        "detail.count_fmt": {"tr": "{n} Adet", "en": "{n} pcs"},
        "detail.yield_fmt": {"tr": "{n} Kg / Hektar", "en": "{n} Kg / Hectare"},

        # ---- Hesaplayıcı ----
        "calc.title": {
            "tr": "🧮 Mera Otlatma Kapasitesi ve İhtiyaç Hesaplayıcısı",
            "en": "🧮 Pasture Grazing Capacity & Demand Calculator",
        },
        "calc.subtitle": {
            "tr": "Hayvan varlığı ve hedeflenen otlatma gün sayısına göre gerekli mera alanını ve yem dengesini hesaplayın.",
            "en": "Calculate the required pasture area and forage balance based on livestock and target grazing days.",
        },
        "calc.group_params": {"tr": "📋 Otlatma Parametreleri", "en": "📋 Grazing Parameters"},
        "calc.lbl_bbhb": {"tr": "🐂 Büyükbaş Hayvan Sayısı:", "en": "🐂 Cattle Count:"},
        "calc.lbl_kbhb": {"tr": "🐑 Küçükbaş Hayvan Sayısı:", "en": "🐑 Sheep Count:"},
        "calc.lbl_days": {"tr": "⏱️ Otlatma Süresi:", "en": "⏱️ Grazing Duration:"},
        "calc.lbl_yield": {"tr": "🌾 Ortalama Ot Verimi (Kg/Ha):", "en": "🌾 Average Hay Yield (Kg/Ha):"},
        "calc.lbl_area": {"tr": "🏞️ Mevcut Mera Alanı:", "en": "🏞️ Available Pasture Area:"},
        "calc.btn_calc": {"tr": "⚡ Hesaplamayı Yap", "en": "⚡ Calculate"},
        "calc.group_results": {
            "tr": "📊 Hesaplama Sonuçları ve Rapor",
            "en": "📊 Calculation Results & Report",
        },
        "calc.card_bbhb": {"tr": "Büyükbaş Hayvan Birimi (BBHB)", "en": "Cattle Unit (BBHB)"},
        "calc.card_feed": {"tr": "Toplam Ot İhtiyacı", "en": "Total Forage Demand"},
        "calc.card_area": {"tr": "Gerekli İdeal Mera Alanı", "en": "Required Ideal Pasture Area"},
        "calc.card_diff": {"tr": "Mevcut Alan / İhtiyaç Farkı", "en": "Available vs. Required Area"},
        "calc.card_status": {"tr": "Mera Verim Yeterliliği", "en": "Pasture Yield Sufficiency"},
        "calc.suffix_unit": {"tr": " Adet", "en": " pcs"},
        "calc.suffix_days": {"tr": " Gün", "en": " days"},
        "calc.area_tip": {
            "tr": "İşletmenizde otlatmaya ayrılan mevcut mera alanı",
            "en": "Pasture area currently allocated for grazing on your farm",
        },
        "calc.val_bbhb": {"tr": "{n:.1f} BBHB ({k:.0f} KBHB eşdeğeri)", "en": "{n:.1f} BBHB ({k:.0f} KBHB equivalent)"},
        "calc.val_feed": {"tr": "{n:,.1f} Ton Kuru Ot ({kg:,.0f} Kg)", "en": "{n:,.1f} Tons Dry Hay ({kg:,.0f} Kg)"},
        "calc.val_area": {"tr": "{n:,.1f} Hektar ({d:,.0f} Dekar)", "en": "{n:,.1f} Hectares ({d:,.0f} Decares)"},
        "calc.val_surplus": {"tr": "➕ {n:,.1f} Ha fazla alan", "en": "➕ {n:,.1f} Ha surplus area"},
        "calc.val_shortfall": {"tr": "➖ {n:,.1f} Ha alan eksik", "en": "➖ {n:,.1f} Ha area shortfall"},
        "calc.status_ok": {"tr": "✅ Mevcut Mera Alanı Yeterli", "en": "✅ Available Pasture Area is Sufficient"},
        "calc.status_warn": {
            "tr": "⚠️ Sınırda - Rotasyonlu Otlatma Önerilir",
            "en": "⚠️ Borderline - Rotation Grazing Recommended",
        },
        "calc.status_bad": {
            "tr": "🚨 Alan Yetersiz - Ek Yem Desteği Şart",
            "en": "🚨 Insufficient Area - Supplementary Feeding Required",
        },

        # ---- Analiz ----
        "analytics.title": {
            "tr": "📊 Türkiye Mera Varlığı İstatistik ve Analiz Paneli",
            "en": "📊 Turkey Pasture Assets Statistics & Analysis Panel",
        },
        "analytics.kpi_area": {"tr": "🌾 Toplam Mera Alanı", "en": "🌾 Total Pasture Area"},
        "analytics.kpi_area_sub": {"tr": "Yaklaşık {n:,} Dekar", "en": "Approximately {n:,} Decares"},
        "analytics.kpi_count": {"tr": "📍 Kayıtlı Mera Sayısı", "en": "📍 Registered Pasture Count"},
        "analytics.kpi_count_sub": {"tr": "Türkiye Geneli", "en": "Across Turkey"},
        "analytics.kpi_bbhb": {"tr": "🐂 Büyükbaş Kapasitesi", "en": "🐂 Cattle Capacity"},
        "analytics.kpi_bbhb_sub": {"tr": "Yıllık İdeal Otlatma", "en": "Annual Ideal Grazing"},
        "analytics.kpi_kbhb": {"tr": "🐑 Küçükbaş Kapasitesi", "en": "🐑 Sheep Capacity"},
        "analytics.kpi_kbhb_sub": {"tr": "Küçükbaş Hayvan Birimi", "en": "Sheep Animal Unit"},
        "analytics.chart_region": {
            "tr": "Coğrafi Bölgelere Göre Mera Alanı (Hektar)",
            "en": "Pasture Area by Geographic Region (Hectares)",
        },
        "analytics.chart_status": {"tr": "Mera Durumu Dağılımı", "en": "Pasture Status Distribution"},
        "analytics.chart_city": {
            "tr": "Mera Varlığı En Yüksek İller (Hektar)",
            "en": "Provinces with Highest Pasture Assets (Hectares)",
        },
        "analytics.chart_elev": {
            "tr": "Rakım (m) ile Ot Verimi (kg/ha) İlişkisi",
            "en": "Relationship between Elevation (m) and Hay Yield (kg/ha)",
        },
        "analytics.axis_elev": {"tr": "Rakım (m)", "en": "Elevation (m)"},
        "analytics.axis_yield": {"tr": "Verim (kg/ha)", "en": "Yield (kg/ha)"},

        # ---- Rotasyon ----
        "rotation.title": {
            "tr": "🔄 Rotasyonlu Otlatma Planı ve Takvimi",
            "en": "🔄 Rotation Grazing Plan & Calendar",
        },
        "rotation.desc": {
            "tr": "Mera, eşit büyüklükte bölmelere ayrılır; her bölme kısa süre otlatılıp "
                 "uzun süre dinlendirilir. Takvimde her gün hangi bölmede hayvan otlatılacağı renkli gösterilir.",
            "en": "The pasture is divided into paddocks of equal size; each paddock is grazed "
                 "briefly then rested for a long period. The calendar shows which paddock is grazed each day in color.",
        },
        "rotation.group_params": {"tr": "📋 Plan Parametreleri", "en": "📋 Plan Parameters"},
        "rotation.lbl_pasture": {"tr": "Mera:", "en": "Pasture:"},
        "rotation.lbl_paddocks": {"tr": "Bölme Sayısı:", "en": "Paddock Count:"},
        "rotation.lbl_rest": {"tr": "Dinlenme Süresi:", "en": "Rest Period:"},
        "rotation.lbl_bbhb": {"tr": "🐂 Büyükbaş (BBHB):", "en": "🐂 Cattle (BBHB):"},
        "rotation.lbl_kbhb": {"tr": "🐑 Küçükbaş (KBHB):", "en": "🐑 Sheep (KBHB):"},
        "rotation.lbl_yield": {"tr": "🌾 Ot Verimi:", "en": "🌾 Hay Yield:"},
        "rotation.btn_generate": {"tr": "📅 Planı Oluştur", "en": "📅 Generate Plan"},
        "rotation.suffix_paddock": {"tr": " Bölme", "en": " paddocks"},
        "rotation.suffix_days": {"tr": " Gün", "en": " days"},
        "rotation.paddock_tip": {"tr": "Mera kaç eşit bölmeye ayrılacak", "en": "How many equal paddocks the pasture is divided into"},
        "rotation.rest_tip": {
            "tr": "Her bölme otlatma sonrası en az bu kadar dinlendirilir",
            "en": "Each paddock is rested at least this long after grazing",
        },
        "rotation.season_info": {"tr": "Sezon: -", "en": "Season: -"},
        "rotation.season_fmt": {
            "tr": "Sezon: {s} - {e} • Alan: {a:,.0f} Ha",
            "en": "Season: {s} - {e} • Area: {a:,.0f} Ha",
        },
        "rotation.tab_calendar": {"tr": "📅 Takvim", "en": "📅 Calendar"},
        "rotation.tab_detail": {"tr": "📋 Plan Detayı", "en": "📋 Plan Details"},
        "rotation.h_paddock": {"tr": "Bölme", "en": "Paddock"},
        "rotation.h_area": {"tr": "Alan (Ha)", "en": "Area (Ha)"},
        "rotation.h_graze_days": {"tr": "Toplam Otlatma Günü", "en": "Total Grazing Days"},
        "rotation.h_graze_iv": {"tr": "Otlatma Aralıkları", "en": "Grazing Intervals"},
        "rotation.h_rest_iv": {"tr": "Dinlenme Aralıkları", "en": "Rest Intervals"},
        "rotation.cal_no_plan": {
            "tr": "Yukarıdan bir mera seçin ve '📅 Planı Oluştur' deyin.",
            "en": "Select a pasture above and click '📅 Generate Plan'.",
        },
        "rotation.legend_paddock": {"tr": "Bölme {p}", "en": "Paddock {p}"},
        "rotation.legend_cycle": {
            "tr": "• {g} gün otlatma + {r} gün dinlenme döngüsü",
            "en": "• {g} days grazing + {r} days rest cycle",
        },
        "rotation.sum_season": {"tr": "🗓️ Sezon Süresi", "en": "🗓️ Season Length"},
        "rotation.sum_paddocks": {"tr": "🧩 Bölme Sayısı", "en": "🧩 Paddock Count"},
        "rotation.sum_ratio": {"tr": "🌿 Otlatma / Dinlenme", "en": "🌿 Grazing / Rest"},
        "rotation.sum_cycle": {"tr": "🔁 Döngü Süresi", "en": "🔁 Cycle Length"},
        "rotation.sum_herd": {"tr": "🐄 Sürü (BBHB)", "en": "🐄 Herd (BBHB)"},
        "rotation.sum_area": {"tr": "🌾 Bölme Alanı", "en": "🌾 Paddock Area"},
        "rotation.day_unit": {"tr": " Gün", "en": " days"},
        "rotation.grazed_fmt": {"tr": "{g} gün (%{u:.0f})", "en": "{g} days (%{u:.0f})"},
        "rotation.paddock_fmt": {"tr": "Bölme {p}", "en": "Paddock {p}"},

        # ---- Yedekleme ----
        "backup.title": {
            "tr": "💾 Veritabanı Yedekleme ve Geri Yükleme",
            "en": "💾 Database Backup & Restore",
        },
        "backup.desc": {
            "tr": "Veritabanını tek tıkla yedekleyin veya daha önce alınmış bir yedekten geri yükleyin. "
                 "Geri yükleme, mevcut veritabanını yedekteki haliyle değiştirir.",
            "en": "Back up the database with one click or restore from a previous backup. "
                 "Restoring replaces the current database with the backup's contents.",
        },
        "backup.btn_backup": {"tr": "💾 Yedek Al", "en": "💾 Take Backup"},
        "backup.btn_restore_file": {"tr": "📂 Dosyadan Geri Yükle", "en": "📂 Restore from File"},
        "backup.btn_refresh": {"tr": "🔄 Yenile", "en": "🔄 Refresh"},
        "backup.backup_tip": {
            "tr": "Veritabanının anlık görüntüsünü yedek klasörüne kaydeder",
            "en": "Saves a snapshot of the database to the backup folder",
        },
        "backup.info_fmt": {
            "tr": "Veritabanı: {path}\nKayıtlı Mera: {count}  •  Boyut: {size}  •  "
                 "Son Değişiklik: {mtime}\nKural Sürümü: {ver}",
            "en": "Database: {path}\nRegistered Pastures: {count}  •  Size: {size}  •  "
                 "Last Modified: {mtime}\nRule Version: {ver}",
        },
        "backup.dir_fmt": {"tr": "Yedek Klasörü: {dir}", "en": "Backup Folder: {dir}"},
        "backup.list_title": {"tr": "📁 Yedek Listesi", "en": "📁 Backup List"},
        "backup.h_name": {"tr": "Dosya Adı", "en": "File Name"},
        "backup.h_size": {"tr": "Boyut", "en": "Size"},
        "backup.h_date": {"tr": "Tarih", "en": "Date"},
        "backup.h_action": {"tr": "İşlem", "en": "Action"},
        "backup.btn_restore": {"tr": "↩️ Geri Yükle", "en": "↩️ Restore"},
        "backup.btn_delete": {"tr": "🗑️ Sil", "en": "🗑️ Delete"},
        "backup.status_migrated": {
            "tr": "🔄 Bekleyen kural göçü uygulandı; sürüm güncellendi.",
            "en": "🔄 Pending rule migration applied; version updated.",
        },
        "backup.status_version_mismatch": {
            "tr": "❌ Kural sürümü uyumsuz (beklenen {expected}, mevcut {rule}); yedek alınamadı.",
            "en": "❌ Rule version mismatch (expected {expected}, found {rule}); backup not taken.",
        },
        "backup.status_ok": {"tr": "✅ Yedek alındı: {name}", "en": "✅ Backup taken: {name}"},
        "backup.status_fail": {"tr": "❌ Yedek alınamadı: {exc}", "en": "❌ Backup failed: {exc}"},
        "backup.dlg_pick": {"tr": "Yedek Dosyasını Seç", "en": "Select Backup File"},
        "backup.confirm_title": {"tr": "Geri Yükleme Onayı", "en": "Restore Confirmation"},
        "backup.confirm_text": {
            "tr": "'{name}' dosyasından geri yüklenecek.\n"
                 "Mevcut tüm veriler yedekteki haliyle değiştirilecek.\n\nDevam edilsin mi?",
            "en": "Restore from '{name}'?\n"
                 "All current data will be replaced with the backup's contents.\n\nContinue?",
        },
        "backup.status_restored": {
            "tr": "✅ Geri yükleme başarılı. Tüm görünümler güncellendi.",
            "en": "✅ Restore successful. All views have been updated.",
        },
        "backup.status_restore_fail": {
            "tr": "❌ Geri yükleme başarısız: {exc}",
            "en": "❌ Restore failed: {exc}",
        },
        "backup.delete_confirm_title": {"tr": "Silme Onayı", "en": "Delete Confirmation"},
        "backup.delete_confirm": {
            "tr": "'{name}' yedeği kalıcı olarak silinsin mi?",
            "en": "Permanently delete the backup '{name}'?",
        },
        "backup.status_deleted": {"tr": "🗑️ Yedek silindi: {name}", "en": "🗑️ Backup deleted: {name}"},
        "backup.status_delete_fail": {"tr": "❌ Silinemedi: {exc}", "en": "❌ Could not delete: {exc}"},

        # ---- Denetim ----
        "audit.title": {
            "tr": "🔎 Veri Denetimi ve Tutarlılık Raporu",
            "en": "🔎 Data Audit & Consistency Report",
        },
        "audit.desc": {
            "tr": "Tüm kayıtları kural setine göre denetler: kod biçimi/çakışması, boş zorunlu alanlar, "
                 "aynı ilde aynı ad ve normalleştirilmemiş kodlar. Sorunlu kodları tek tıkla düzeltebilirsiniz.",
            "en": "Audits all records against the rule set: code format/duplicates, empty required fields, "
                 "same name in the same province, and non-normalized codes. Fix problem codes with one click.",
        },
        "audit.btn_audit": {"tr": "🔍 Denetle", "en": "🔍 Audit"},
        "audit.btn_fix_all": {"tr": "✨ Kodları Normalleştir", "en": "✨ Normalize Codes"},
        "audit.mig_title": {
            "tr": "🔄 Kural Sürümü ve Veri Göçü",
            "en": "🔄 Rule Version & Data Migration",
        },
        "audit.table_title": {"tr": "📋 Sorunlu Kayıtlar", "en": "📋 Problem Records"},
        "audit.poly_title": {
            "tr": "📐 Poligon–Kayıtlı Alan Uyumu",
            "en": "📐 Polygon–Recorded Area Consistency",
        },
        "audit.poly_fmt": {
            "tr": "{c} poligon denetlendi · {ph} yer tutucu atlandı · {mp} poligon yok · {n} uyumsuzluk (eşik >%{t})",
            "en": "{c} polygons checked · {ph} placeholders skipped · {mp} missing · {n} deviations (threshold >{t}%)",
        },
        "audit.poly_item": {
            "tr": "• {code}: %{pct} sapma — hesaplanan {c} ha ↔ kayıtlı {r} ha",
            "en": "• {code}: {pct}% deviation — calculated {c} ha ↔ recorded {r} ha",
        },
        "audit.poly_item_noarea": {
            "tr": "• {code}: kayıtlı alan eksik — hesaplanan {c} ha",
            "en": "• {code}: recorded area missing — calculated {c} ha",
        },
        "audit.poly_more": {
            "tr": "… ve {n} kayıt daha",
            "en": "… and {n} more",
        },
        "audit.log_title": {
            "tr": "🧾 Ölçüm Denetim İzi (son 50)",
            "en": "🧾 Measurement Audit Trail (last 50)",
        },
        "audit.log_h_time": {"tr": "Zaman", "en": "Time"},
        "audit.log_h_action": {"tr": "İşlem", "en": "Action"},
        "audit.log_h_pasture": {"tr": "Mera", "en": "Pasture"},
        "audit.log_h_source": {"tr": "Kaynak", "en": "Source"},
        "audit.log_h_changes": {"tr": "Değişen Alanlar", "en": "Changed Fields"},
        "audit.log_source_label": {"tr": "Kaynak:", "en": "Source:"},
        "audit.log_src_all": {"tr": "Tümü", "en": "All"},
        "audit.log_src_map": {"tr": "Harita", "en": "Map"},
        "audit.log_src_menu": {"tr": "Menü", "en": "Menu"},
        "audit.log_src_form": {"tr": "Form", "en": "Form"},
        "audit.log_from": {"tr": "Başlangıç:", "en": "From:"},
        "audit.log_to": {"tr": "Bitiş:", "en": "To:"},
        "audit.log_btn_export": {"tr": "📥 CSV Aktar", "en": "📥 Export CSV"},
        "audit.log_dlg_export": {
            "tr": "Denetim İzini CSV Aktar", "en": "Export Audit Trail as CSV"},
        "audit.log_no_data": {
            "tr": "Seçili filtrelerde denetim izi kaydı bulunamadı.",
            "en": "No audit trail records match the selected filters."},
        "audit.log_export_ok": {
            "tr": "Denetim izi kaydedildi:\n{path}",
            "en": "Audit trail saved to:\n{path}"},
        "audit.log_export_fail": {
            "tr": "CSV dosyası yazılamadı:\n{exc}",
            "en": "Could not write CSV file:\n{exc}"},
        "audit.h_id": {"tr": "ID", "en": "ID"},
        "audit.h_code": {"tr": "Kod", "en": "Code"},
        "audit.h_name": {"tr": "Mera Adı", "en": "Pasture Name"},
        "audit.h_city": {"tr": "İl", "en": "City"},
        "audit.h_problems": {"tr": "Sorunlar", "en": "Problems"},
        "audit.h_action": {"tr": "İşlem", "en": "Action"},
        "audit.btn_fix": {"tr": "✨ Düzelt", "en": "✨ Fix"},
        "audit.sum_total": {"tr": "📦 Toplam Kayıt", "en": "📦 Total Records"},
        "audit.sum_issues": {"tr": "❌ Sorunlu", "en": "❌ With Issues"},
        "audit.sum_ok": {"tr": "✅ Sorunsuz", "en": "✅ Clean"},
        "audit.sum_rule": {"tr": "🏷️ Kural Sürümü", "en": "🏷️ Rule Version"},
        "audit.status_ok": {"tr": "✅ {n} kayıt denetlendi — sorun yok", "en": "✅ {n} records audited — no issues"},
        "audit.status_warn": {
            "tr": "⚠️ {n} kayıtta {e} hata, {i} bilgi düzeyinde sorun",
            "en": "⚠️ {n} records with {e} errors, {i} info-level issues",
        },
        "audit.mig_none": {
            "tr": "Kural sürümü: {v}. Henüz kayıtlı bir göç raporu yok.",
            "en": "Rule version: {v}. No migration report recorded yet.",
        },
        "audit.mig_conflict": {
            "tr": "  •  ⚠️ Göçte çakışan kayıtlar (kod değiştirilemedi): kayıt #{ids}",
            "en": "  •  ⚠️ Conflicting records in migration (code not changed): record #{ids}",
        },
        "audit.mig_fmt": {
            "tr": "Kural sürümü: {v}  •  Son göç: {d}  •  Uygulanan adımlar: {s}  •  Değişen kayıt: {c}",
            "en": "Rule version: {v}  •  Last migration: {d}  •  Applied steps: {s}  •  Records changed: {c}",
        },
        "audit.msg_title": {"tr": "Veri Denetimi", "en": "Data Audit"},
        "audit.fix_no_record": {
            "tr": "Kayıt bulunamadı; liste tazeleniyor.",
            "en": "Record not found; refreshing the list.",
        },
        "audit.fix_conflict": {
            "tr": "'{code}' kodu başka bir kayıtta kullanılıyor; "
                 "çakışma elle çözülmeli (kaydı düzenleyip farklı kod girin).",
            "en": "The code '{code}' is used by another record; "
                 "the conflict must be resolved manually (edit the record and enter a different code).",
        },
        "audit.fix_failed": {"tr": "Düzeltilemedi: {exc}", "en": "Could not fix: {exc}"},
        "audit.status_no_fixable": {
            "tr": "✅ Normalleştirilecek kayıt yok",
            "en": "✅ No records to normalize",
        },
        "audit.status_fixed": {"tr": "✨ {n} kod düzeltildi", "en": "✨ {n} codes fixed"},
        "audit.status_skipped": {"tr": ", {n} atlandı (çakışma)", "en": ", {n} skipped (conflict)"},
        "audit.audit_failed": {
            "tr": "❌ Denetim çalıştırılamadı: {exc}",
            "en": "❌ Audit could not run: {exc}",
        },

        # ---- Mera diyaloğu ----
        "dialog.title_add": {"tr": "Yeni Mera Ekle", "en": "Add New Pasture"},
        "dialog.title_edit": {"tr": "Düzenle: {name}", "en": "Edit: {name}"},
        "dialog.header_add": {"tr": "➕ Yeni Mera Kaydı Oluştur", "en": "➕ Create New Pasture Record"},
        "dialog.header_edit": {"tr": "✏️ Mera Bilgilerini Düzenle", "en": "✏️ Edit Pasture Details"},
        "dialog.group": {
            "tr": "Genel & Coğrafi Bilgiler",
            "en": "General & Geographic Information",
        },
        "dialog.btn_random": {"tr": "🎲 Rastgele Kod", "en": "🎲 Random Code"},
        "dialog.btn_random_tip": {
            "tr": "Otomatik, benzersiz rastgele bir kod üretir",
            "en": "Generates a unique random code",
        },
        "dialog.lbl_code": {"tr": "Mera Kodu:", "en": "Pasture Code:"},
        "dialog.lbl_name": {"tr": "Mera Adı:", "en": "Pasture Name:"},
        "dialog.lbl_region": {"tr": "Bölge:", "en": "Region:"},
        "dialog.lbl_city": {"tr": "İl:", "en": "City:"},
        "dialog.lbl_district": {"tr": "İlçe:", "en": "District:"},
        "dialog.lbl_village": {"tr": "Köy:", "en": "Village:"},
        "dialog.lbl_area": {"tr": "Yüzölçümü (Ha):", "en": "Area (Ha):"},
        "dialog.lbl_elevation": {"tr": "Rakım (m):", "en": "Elevation (m):"},
        "dialog.lbl_lat": {"tr": "Enlem (Lat):", "en": "Latitude (Lat):"},
        "dialog.lbl_lng": {"tr": "Boylam (Lng):", "en": "Longitude (Lng):"},
        "dialog.lbl_status": {"tr": "Durum:", "en": "Status:"},
        "dialog.lbl_bbhb": {"tr": "BBHB Kapasite:", "en": "BBHB Capacity:"},
        "dialog.lbl_kbhb": {"tr": "KBHB Kapasite:", "en": "KBHB Capacity:"},
        "dialog.lbl_yield": {"tr": "Kuru Ot Verimi:", "en": "Dry Hay Yield:"},
        "dialog.lbl_cov": {"tr": "Vejetasyon Örtüsü:", "en": "Vegetation Coverage:"},
        "dialog.lbl_plants": {"tr": "Dominant Bitkiler:", "en": "Dominant Plants:"},
        "dialog.lbl_water": {"tr": "Su Kaynakları:", "en": "Water Sources:"},
        "dialog.lbl_soil": {"tr": "Toprak Yapısı:", "en": "Soil Type:"},
        "dialog.lbl_season_start": {
            "tr": "Otlatma Sezonu Başlangıcı:",
            "en": "Grazing Season Start:",
        },
        "dialog.lbl_season_end": {"tr": "Otlatma Sezonu Bitişi:", "en": "Grazing Season End:"},
        "dialog.lbl_notes": {"tr": "Notlar:", "en": "Notes:"},
        "dialog.btn_save": {"tr": "💾 Kaydet", "en": "💾 Save"},
        "dialog.btn_cancel": {"tr": "İptal", "en": "Cancel"},
        "dialog.msg_warn_title": {"tr": "Uyarı", "en": "Warning"},

        # ---- Hakkında ----
        "about.title": {"tr": "Hakkında - MERA-BİS PRO", "en": "About - MERA-BIS PRO"},
        "about.desc": {
            "tr": "Türkiye 81 İl Mera ve Otlatma Alanları Bilgi Sistemi",
            "en": "Turkey 81 Provinces Pasture and Grazing Areas Information System",
        },
        "about.role": {"tr": "Kaldırım Mühendisi", "en": "Sidewalk Engineer"},
        "about.copyright": {
            "tr": "Copyright © 2026 - Her Hakkı Saklıdır!  D :D :D",
            "en": "Copyright © 2026 - All Rights Reserved!  D :D :D",
        },
        "about.btn_close": {"tr": "Kapat", "en": "Close"},
        "about.version": {"tr": "Sürüm {v}", "en": "Version {v}"},
        "about.build": {"tr": "  •  Derleme: {d}", "en": "  •  Build: {d}"},
        "about.version_copy_hint": {
            "tr": "Sağ tıkla → sürümü kopyala",
            "en": "Right-click → copy version",
        },
        "about.copied": {"tr": "✓ Kopyalandı", "en": "✓ Copied"},

        # ---- Menü / kısayol / durum çubuğu ----
        "menu.file": {"tr": "&Dosya", "en": "&File"},
        "menu.tools": {"tr": "&Araçlar", "en": "&Tools"},
        "menu.help": {"tr": "&Yardım", "en": "&Help"},
        "menu.exit": {"tr": "Çıkış", "en": "Exit"},
        "menu.check_updates": {"tr": "Güncellemeleri Denetle...", "en": "Check for Updates..."},
        "menu.data_audit": {"tr": "Veri Denetimi", "en": "Data Audit"},
        "menu.backup": {"tr": "Yedekleme", "en": "Backup"},
        "menu.about": {"tr": "Hakkında", "en": "About"},
        "menu.f1": {"tr": "F1", "en": "F1"},
        "menu.ctrl_u": {"tr": "Ctrl+U", "en": "Ctrl+U"},
        "menu.ctrl_q": {"tr": "Ctrl+Q", "en": "Ctrl+Q"},
        "status.ready": {"tr": "Hazır — {n} mera kayıtlı", "en": "Ready — {n} pastures registered"},
        "status.rules_v": {"tr": "Kural sürümü: {v}", "en": "Rule version: {v}"},
        "status.update_available": {
            "tr": "⬇️ Yeni sürüm {v} var — güncellemeleri denetleyin",
            "en": "⬇️ New version {v} available — check for updates",
        },
        # ---- İmza denetimi (imzasız paket uyarısı) ----
        "signature.title": {"tr": "Güvenlik Uyarısı", "en": "Security Warning"},
        "signature.warn.not_signed": {
            "tr": "⚠️ Bu uygulama paketi dijital olarak İMZALANMAMIŞ.\n\n"
                 "Yazılımın kaynağı doğrulanamıyor; kötü amaçlı yazılım gizlenmiş olabilir. "
                 "Yalnızca resmî dağıtım kanalından (GitHub Releases veya kurum içi paylaşım) "
                 "aldığınız paketlere güvenin.\n\n"
                 "Dosya: {detail}",
            "en": "⚠️ This application package is NOT digitally SIGNED.\n\n"
                 "The software origin cannot be verified; malware could be hiding inside. "
                 "Only trust packages from the official distribution channel "
                 "(GitHub Releases or corporate share).\n\nFile: {detail}",
        },
        "signature.warn.hash_mismatch": {
            "tr": "🛑 Bu uygulama dosyası DİJİTAL İMZASIYLA EŞLEŞMİYOR — dosya değiştirilmiş olabilir!\n\n"
                 "Uygulamayı kapatın, dosyayı silin ve resmî kanaldan yeniden indirin.\n\nDosya: {detail}",
            "en": "🛑 This application file does NOT MATCH its digital signature — it may have been tampered with!\n\n"
                 "Close the application, delete the file and re-download from the official channel.\n\nFile: {detail}",
        },
        "signature.warn.unknown_platform": {
            "tr": "⚠️ Uygulama paketinin dijital imzası DOĞRULANAMADI.\n\n"
                 "Yazılımın kaynağı doğrulanamıyor. Yalnızca resmî dağıtım kanalından aldığınız "
                 "paketlere güvenin.\n\nDosya: {detail}",
            "en": "⚠️ The digital signature of the application package could NOT BE VERIFIED.\n\n"
                 "The software origin cannot be verified. Only trust packages from the "
                 "official distribution channel.\n\nFile: {detail}",
        },
        "signature.warn.generic": {
            "tr": "⚠️ Dijital imza denetimi tamamlanamadı; paket doğrulanamıyor.\n\nDosya: {detail}",
            "en": "⚠️ Digital signature check could not be completed; the package cannot be verified.\n\nFile: {detail}",
        },
        "signature.continue_btn": {"tr": "Yine de Çalıştır", "en": "Run Anyway"},
        "signature.exit_btn": {"tr": "Çıkış", "en": "Exit"},
        "signature.remember_no": {
            "tr": "Bu oturum için bir daha gösterme",
            "en": "Don't show again for this session",
        },

        # ---- Hızlı ölçüm girişi ----
        "menu.add_measurement": {
            "tr": "Ölçüm Ekle...",
            "en": "Add Measurement...",
        },

        # ---- Veri taşıma sihirbazı ----
        "menu.migrate_data": {
            "tr": "Eski Kurulumdan Veri Taşı...",
            "en": "Migrate Data from Old Installation...",
        },
        "mig.startup.title": {"tr": "Eski Veriler Bulundu", "en": "Old Data Found"},
        "mig.startup.question": {
            "tr": "Eski bir MERA-BİS PRO kurulumuna ait veri tabanı bulundu:\n\n{path}\n\nBu kurulumdan {pastures} mera ve {measurements} ölçüm kaydı taşınabilir. "
                 "Veri taşıma sihirbazını şimdi açmak ister misiniz?",
            "en": "A database from an old MERA-BIS PRO installation was found:\n\n{path}\n\n{pastures} pastures and {measurements} measurement records can be migrated. "
                 "Open the data migration wizard now?",
        },
        "mig.wizard.title": {
            "tr": "Veri Taşıma Sihirbazı",
            "en": "Data Migration Wizard",
        },
        "mig.btn.next": {"tr": "İleri >", "en": "Next >"},
        "mig.btn.back": {"tr": "< Geri", "en": "< Back"},
        "mig.btn.cancel": {"tr": "İptal", "en": "Cancel"},
        "mig.btn.finish": {"tr": "Tamamla", "en": "Finish"},
        "mig.page.source.title": {
            "tr": "Kaynak Veritabanı",
            "en": "Source Database",
        },
        "mig.page.source.subtitle": {
            "tr": "Eski kurulumun veritabanını seçin.",
            "en": "Select the old installation's database.",
        },
        "mig.page.source.scanning": {
            "tr": "Bilinen konumlar taranıyor...",
            "en": "Scanning known locations...",
        },
        "mig.page.source.found": {
            "tr": "{n} kaynak bulundu — birini seçin.",
            "en": "{n} source(s) found — choose one.",
        },
        "mig.page.source.none": {
            "tr": "Bilinen konumlarda veritabanı bulunamadı. Elle seçim yapabilirsiniz.",
            "en": "No database found in known locations. You can pick a file manually.",
        },
        "mig.page.source.scan_error": {
            "tr": "Tarama başarısız: {err}",
            "en": "Scan failed: {err}",
        },
        "mig.page.source.rescan": {"tr": "Yeniden Tara", "en": "Rescan"},
        "mig.page.source.browse": {"tr": "Elle Seç...", "en": "Browse..."},
        "mig.page.source.browse_title": {
            "tr": "Eski veritabanını seçin (mera_otomasyonu.db)",
            "en": "Select the old database (mera_otomasyonu.db)",
        },
        "mig.page.source.hint": {
            "tr": "İpucu: Eski kurulumun verisi genellikle %APPDATA% altında "
                 "(MeraBisPro, MeraBIS, Mera Bis Pro) klasörlerinde bulunur.",
            "en": "Tip: Old installation data usually lives under %APPDATA% "
                  "in folders like MeraBisPro, MeraBIS or Mera Bis Pro.",
        },
        "mig.page.source.item": {
            "tr": "{path}\n    {pastures} mera · {measurements} ölçüm · değişiklik: {modified} · {size}",
            "en": "{path}\n    {pastures} pastures · {measurements} measurements · modified: {modified} · {size}",
        },
        "mig.page.source.item_seed": {
            "tr": "{path}\n    {pastures} mera (yalnızca örnek veri) · değişiklik: {modified} · {size}",
            "en": "{path}\n    {pastures} pastures (sample data only) · modified: {modified} · {size}",
        },
        "mig.msg.invalid_source": {
            "tr": "Seçilen dosya geçerli bir MERA-BİS veritabanı değil: {err}",
            "en": "The selected file is not a valid MERA-BIS database: {err}",
        },
        "mig.page.preview.title": {
            "tr": "Önizleme ve Taşıma Modu",
            "en": "Preview and Migration Mode",
        },
        "mig.page.preview.subtitle": {
            "tr": "Taşınacak veriyi gözden geçirin ve modu seçin.",
            "en": "Review the data to migrate and choose a mode.",
        },
        "mig.page.preview.mode_lbl": {"tr": "Taşıma modu:", "en": "Migration mode:"},
        "mig.page.preview.mode_merge": {
            "tr": "Birleştir (önerilen) — mevcut veriye ekle",
            "en": "Merge (recommended) — add to current data",
        },
        "mig.page.preview.mode_merge_note": {
            "tr": "Aynı kod + aynı içerik atlanır; aynı kod + farklı içerik "
                 "-T2 ekiyle eklenir. Ölçüm kayıtları tarih bazlı yinelenmez.",
            "en": "Same code + same content is skipped; same code + different "
                  "content is added with a -T2 suffix. Measurements never duplicate by date.",
        },
        "mig.page.preview.mode_replace": {
            "tr": "Değiştir — mevcut kayıtlar silinip kaynak alınır",
            "en": "Replace — current records are cleared and the source is imported",
        },
        "mig.page.preview.mode_replace_note": {
            "tr": "Mevcut tüm mera ve ölçüm kayıtları kaldırılır.",
            "en": "All current pasture and measurement records will be removed.",
        },
        "mig.page.preview.warn_replace": {
            "tr": "⚠ Değiştirme modu mevcut veriyi kaldırır; taşıma öncesi otomatik "
                 "yedek alınır (pre_migration_*.db) ve geri alınabilir.",
            "en": "⚠ Replace mode removes current data; an automatic backup "
                  "(pre_migration_*.db) is taken before migrating and can be restored.",
        },
        "mig.page.preview.src_none": {
            "tr": "Kaynak seçilmedi.",
            "en": "No source selected.",
        },
        "mig.page.preview.src_invalid": {
            "tr": "Kaynak geçersiz: {err}",
            "en": "Source is invalid: {err}",
        },
        "mig.page.preview.src_summary": {
            "tr": "Kaynak: {path}\nMera sayısı: {pastures}\nÖlçüm kaydı: {measurements}\nSon değişiklik: {modified}\nBoyut: {size}",
            "en": "Source: {path}\nPastures: {pastures}\nMeasurements: {measurements}\nLast modified: {modified}\nSize: {size}",
        },
        "mig.page.progress.title": {"tr": "Taşıma Yapılıyor", "en": "Migrating"},
        "mig.page.progress.subtitle": {
            "tr": "Veriler güvenli biçimde aktarılıyor — lütfen bekleyin.",
            "en": "Data is being transferred safely — please wait.",
        },
        "mig.page.progress.running": {
            "tr": "Yedek alınıyor, kaynak anlık görüntüye alınıyor ve kayıtlar aktarılıyor...",
            "en": "Taking backup, snapshotting the source and transferring records...",
        },
        "mig.page.progress.done": {
            "tr": "✓ Taşıma tamamlandı. Özet için İleri'ye tıklayın.",
            "en": "✓ Migration completed. Click Next for the summary.",
        },
        "mig.page.progress.failed": {
            "tr": "✗ Taşıma başarısız: {err}\nMevcut veri değişmedi (otomatik yedek geri yüklenebilir: yedek klasöründeki pre_migration_*.db).",
            "en": "✗ Migration failed: {err}\nCurrent data is unchanged (an automatic backup can be restored: pre_migration_*.db in the backups folder).",
        },
        "mig.page.summary.title": {"tr": "Taşıma Sonucu", "en": "Migration Result"},
        "mig.page.summary.subtitle": {
            "tr": "Taşıma raporu.",
            "en": "Migration report.",
        },
        "mig.page.summary.text": {
            "tr": "Taşıma tamamlandı ({mode}).\n\n"
                 "Eklenen mera: {imported}\n"
                 "Atlanan özdeş mera: {skipped_identical}\n"
                 "Kod çakışması (-T2 eklenen): {conflicts_renamed}\n"
                 "Eklenen ölçüm: {imported_measurements}\n"
                 "Atlanan ölçüm: {skipped_measurements}\n\n"
                 "Toplam mera: {pastures_after} · Toplam ölçüm: {measurements_after}\n"
                 "Güvenlik yedeği: {backup}",
            "en": "Migration completed ({mode}).\n\n"
                  "Pastures added: {imported}\n"
                  "Identical pastures skipped: {skipped_identical}\n"
                  "Code conflicts (renamed -T2): {conflicts_renamed}\n"
                  "Measurements added: {imported_measurements}\n"
                  "Measurements skipped: {skipped_measurements}\n\n"
                  "Total pastures: {pastures_after} · Total measurements: {measurements_after}\n"
                  "Safety backup: {backup}",
        },
        "mig.page.summary.nochanges": {
            "tr": "Taşıma tamamlanamadı; hiçbir değişiklik yapılmadı.",
            "en": "Migration did not complete; no changes were made.",
        },
        "msg.quit_title": {"tr": "Çıkış", "en": "Exit"},
        "msg.quit_confirm": {
            "tr": "Uygulamadan çıkmak istediğinize emin misiniz?",
            "en": "Are you sure you want to exit the application?",
        },

        # ---- Güncelleme diyaloğu ----
        "upd.title": {"tr": "Güncellemeler", "en": "Updates"},
        "upd.desc": {
            "tr": "Uygulama sürümünü denetleyin; yeni paketi doğrular, yedekler ve güvenle yükler. "
                 "Kaynak olarak yerel klasör veya ağ paylaşımı (UNC) kullanılabilir.",
            "en": "Check the application version; the new package is verified, backed up and installed "
                  "safely. A local folder or network share (UNC) can be used as source.",
        },
        "upd.btn_check": {"tr": "🔄 Denetle", "en": "🔄 Check"},
        "upd.btn_install": {"tr": "⬇️ Güncellemeyi Yükle", "en": "⬇️ Install Update"},
        "upd.btn_rollback": {"tr": "↩️ Geri Al", "en": "↩️ Rollback"},
        "upd.btn_close": {"tr": "Kapat", "en": "Close"},
        "upd.btn_browse": {"tr": "Seç...", "en": "Browse..."},
        "upd.source_label": {"tr": "Kaynak:", "en": "Source:"},
        "upd.source_placeholder": {
            "tr": "Klasör veya \\\\sunucu\\paylasim (boş = uygulama yanı)",
            "en": "Folder or \\\\server\\share (empty = next to app)",
        },
        "upd.source_pick_title": {"tr": "Güncelleme Kaynağını Seç", "en": "Select Update Source"},
        "upd.checking": {"tr": "Denetleniyor...", "en": "Checking..."},
        "upd.available": {
            "tr": "⬇️ Yeni sürüm {v} hazır (mevcut: {cur})",
            "en": "⬇️ New version {v} available (current: {cur})",
        },
        "upd.up_to_date": {"tr": "✅ Uygulama güncel", "en": "✅ Application is up to date"},
        "upd.no_source": {
            "tr": "⚠️ Güncelleme kaynağı bulunamadı.",
            "en": "⚠️ No update source found.",
        },
        "upd.source_mode_hint": {
            "tr": "Not: Kaynak modda yükleme kapalıdır; yalnızca paketli derlemede çalışır.",
            "en": "Note: Installation is disabled in source mode; it works only in packaged builds.",
        },
        "upd.stage_verify": {"tr": "Paket doğrulanıyor...", "en": "Verifying package..."},
        "upd.stage_backup": {"tr": "Mevcut uygulama yedekleniyor...", "en": "Backing up current app..."},
        "upd.stage_apply": {"tr": "Güncelleme uygulanıyor...", "en": "Applying update..."},
        "upd.confirm_title": {"tr": "Güncelleme Onayı", "en": "Update Confirmation"},
        "upd.confirm_text": {
            "tr": "Güncelleme yüklenecek.\nUygulama kapatılıp yeni sürüm otomatik başlatılacak.\n\nDevam edilsin mi?",
            "en": "The update will be installed.\nThe app will close and the new version will start automatically.\n\nContinue?",
        },
        "upd.install_done": {
            "tr": "✅ Güncelleme yüklendi (v{v}).\nUygulama birkaç saniye içinde yeniden başlayacak.",
            "en": "✅ Update installed (v{v}).\nThe application will restart in a few seconds.",
        },
        "upd.install_fail": {"tr": "❌ İşlem başarısız:\n{exc}", "en": "❌ Operation failed:\n{exc}"},
        "upd.rollback_title": {"tr": "Geri Alma Onayı", "en": "Rollback Confirmation"},
        "upd.rollback_confirm": {
            "tr": "Son güncelleme geri alınacak ve uygulama önceki sürümüne dönecek.\nDevam edilsin mi?",
            "en": "The last update will be rolled back to the previous version.\nContinue?",
        },
        "upd.rollback_done": {
            "tr": "✅ Güncelleme geri alındı ({n} dosya). Uygulamayı yeniden başlatın.",
            "en": "✅ Update rolled back ({n} files). Restart the application.",
        },

        # ---- Vejetasyon ölçüm/gözlem kayıtları ----
        "nav.measurements": {"tr": "🌱 Vejetasyon Ölçümleri", "en": "🌱 Vegetation Measurements"},
        "meas.title": {
            "tr": "🌱 Vejetasyon Ölçüm ve Gözlem Kayıtları",
            "en": "🌱 Vegetation Measurement & Observation Records",
        },
        "meas.desc": {
            "tr": "Mera başına dönemsel ölçüm kaydedin: kuru ot verimi, örtü yüzdesi, ortalama boy, "
                 "dominant bitkiler, gözlemci ve yöntem. Trend grafiği mevsimsel gelişimi gösterir.",
            "en": "Record seasonal measurements per pasture: dry hay yield, coverage, average height, "
                  "dominant plants, observer and method. The trend chart shows seasonal development.",
        },
        "meas.group_new": {"tr": "📋 Yeni Ölçüm / Düzenleme", "en": "📋 New Measurement / Edit"},
        "meas.lbl_pasture": {"tr": "Mera:", "en": "Pasture:"},
        "meas.lbl_date": {"tr": "Ölçüm Tarihi:", "en": "Measurement Date:"},
        "meas.lbl_yield": {"tr": "Kuru Ot Verimi:", "en": "Dry Hay Yield:"},
        "meas.lbl_cover": {"tr": "Örtü Yüzdesi:", "en": "Coverage:"},
        "meas.lbl_height": {"tr": "Ortalama Boy:", "en": "Average Height:"},
        "meas.lbl_plants": {"tr": "Dominant Bitkiler:", "en": "Dominant Plants:"},
        "meas.lbl_observer": {"tr": "Gözlemci:", "en": "Observer:"},
        "meas.lbl_method": {"tr": "Ölçüm Yöntemi:", "en": "Method:"},
        "meas.lbl_notes": {"tr": "Notlar:", "en": "Notes:"},
        "meas.btn_save": {"tr": "💾 Kaydet", "en": "💾 Save"},
        "meas.btn_add": {"tr": "➕ Ekle", "en": "➕ Add"},
        "meas.btn_edit": {"tr": "✏️ Düzenle", "en": "✏️ Edit"},
        "meas.btn_delete": {"tr": "🗑️ Sil", "en": "🗑️ Delete"},
        "meas.btn_export": {"tr": "📊 CSV Aktar", "en": "📊 Export CSV"},
        "meas.h_date": {"tr": "Tarih", "en": "Date"},
        "meas.h_yield": {"tr": "Verim (kg/ha)", "en": "Yield (kg/ha)"},
        "meas.h_cover": {"tr": "Örtü (%)", "en": "Coverage (%)"},
        "meas.h_height": {"tr": "Boy (cm)", "en": "Height (cm)"},
        "meas.h_plants": {"tr": "Dominant Bitkiler", "en": "Dominant Plants"},
        "meas.h_observer": {"tr": "Gözlemci", "en": "Observer"},
        "meas.h_method": {"tr": "Yöntem", "en": "Method"},
        "meas.count_fmt": {"tr": "{n} ölçüm kaydı", "en": "{n} measurement records"},
        "meas.chart_title": {"tr": "Trend: {name}", "en": "Trend: {name}"},
        "meas.chart_yield": {"tr": "Kuru ot verimi (kg/ha)", "en": "Dry hay yield (kg/ha)"},
        "meas.chart_cover": {"tr": "Örtü (%)", "en": "Coverage (%)"},
        "meas.msg_title": {"tr": "Vejetasyon Ölçümleri", "en": "Vegetation Measurements"},
        "meas.warn_no_pasture": {
            "tr": "Ölçüm kaydetmek için bir mera seçin.",
            "en": "Select a pasture to save a measurement.",
        },
        "meas.save_fail": {"tr": "Kayıt başarısız:\n{exc}", "en": "Save failed:\n{exc}"},
        "meas.delete_title": {"tr": "Silme Onayı", "en": "Delete Confirmation"},
        "meas.delete_confirm": {
            "tr": "Seçili ölçüm kaydı silinsin mi?",
            "en": "Delete the selected measurement record?",
        },
        "meas.delete_fail": {"tr": "Silinemedi:\n{exc}", "en": "Delete failed:\n{exc}"},
        "meas.no_data": {
            "tr": "Dışa aktarılacak ölçüm kaydı yok.",
            "en": "No measurement records to export.",
        },
        "meas.dlg_export": {"tr": "Ölçümleri CSV Aktar", "en": "Export Measurements as CSV"},
        "meas.export_ok": {
            "tr": "Ölçümler dışa aktarıldı:\n{path}",
            "en": "Measurements exported:\n{path}",
        },
    }

    # Liste tipindeki çeviriler (ay ve hafta günü adları)
    _lists = {
        "months": {
            "tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                   "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
            "en": ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"],
        },
        "months_short": {
            "tr": ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
                   "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
            "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        },
        "weekdays": {
            "tr": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
            "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        },
    }

    @classmethod
    def set_language(cls, lang):
        """Aktif dili değiştirir; doğrulama kataloğunu da senkronize eder."""
        cls._lang = "en" if lang == "en" else "tr"
        MessageCatalog.set_language(cls._lang)

    @classmethod
    def get_language(cls):
        return cls._lang

    @classmethod
    def get(cls, key, **kwargs):
        """Aktif dildeki metni döndürür; bilinmeyen anahtar kendi adını döndürür."""
        entry = cls._strings.get(key)
        if entry is None:
            return key
        text = entry.get(cls._lang) or entry.get("tr") or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    @classmethod
    def get_list(cls, key):
        """Aktif dildeki liste (örn. 'months', 'weekdays')."""
        entry = cls._lists.get(key)
        if entry is None:
            return []
        return entry.get(cls._lang) or entry.get("tr") or []


# Tekil nesne — görünümler bunu kullanır
T = Translator
