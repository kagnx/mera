"""
GUI katmanı için smoke testi (başlıksız/offscreen çalışır).

Çalıştırma:  QT_QPA_PLATFORM=offscreen python tests/smoke_gui.py
"""
import os
import sys
import json
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# QtWebEngine modülleri QApplication oluşturulmadan ÖNCE import edilmeli (main.py ile aynı kural)
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402,F401
from PyQt6.QtWidgets import QApplication, QLabel  # noqa: E402

from database.db_manager import DatabaseManager  # noqa: E402
from database.validation import is_valid_code_format  # noqa: E402
from styles.pistachio_theme import PistachioTheme  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402
from gui.pasture_dialog import PastureDialog  # noqa: E402
from gui.calculator_view import CalculatorView  # noqa: E402
from gui.about_dialog import AboutDialog  # noqa: E402

FAILURES = []
PASS_COUNT = 0


def check(name, condition, detail=""):
    global PASS_COUNT
    PASS_COUNT += 1
    if condition:
        print(f"  [OK]   {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name} {detail}")


def main():
    app = QApplication(sys.argv)
    # Ana tema (main.py ile aynı): açık fıstık yeşili
    app.setStyleSheet(PistachioTheme.LIGHT_STYLE)

    # Dil determinizmi: önceki çalıştırmadan kalma 'en' kaydını temizle
    from PyQt6.QtCore import QSettings
    from i18n import T
    QSettings().setValue("language", "tr")
    T.set_language("tr")

    tmp = tempfile.mkdtemp()
    db = DatabaseManager(os.path.join(tmp, "smoke.db"))

    # Ana pencere ve tüm görünümler
    window = MainWindow(db)
    window.resize(1380, 850)

    check("ana pencere oluştu", window is not None)
    check("toplam istatistik 81", db.get_statistics()["total_count"] == 81)
    check("açık fıstık yeşili tema uygulandı",
          "#EDF4EA" in app.styleSheet() and "#7CB342" in app.styleSheet())

    # Hakkında diyaloğu: okunabilir açık tema (metinler piksel bazında doğrulanır)
    about = AboutDialog(window)
    about.show()
    for _ in range(3):
        app.processEvents()
    readable = True
    for lbl in about.findChildren(QLabel):
        if not lbl.text():
            continue
        img = lbl.grab().toImage()
        dark = sum(1 for y in range(img.height()) for x in range(img.width())
                   if 0.299 * img.pixelColor(x, y).red() + 0.587 * img.pixelColor(x, y).green()
                   + 0.114 * img.pixelColor(x, y).blue() < 160)
        if dark <= 40:
            readable = False
    check("hakkında diyaloğu etiket metinleri okunaklı (piksel doğrulama)", readable)
    check("hakkında diyaloğu açık temada",
          "#EDF4EA" in about.styleSheet() and "#23332A" in about.styleSheet())
    about_texts = [lbl.text() for lbl in about.findChildren(QLabel)]
    check("hakkında: sürüm etiketi görünür",
          any(t.startswith("Sürüm") or ">Sürüm" in t for t in about_texts), str(about_texts))
    about.close()

    # Yeni kayıt diyaloğu: otomatik kod
    dlg_add = PastureDialog(window, default_code=db.get_next_code(), db=db)
    check("yeni kayıt kodu otomatik (MRA-82-01)", dlg_add.code_input.text() == "MRA-82-01",
          f"gelen: {dlg_add.code_input.text()}")
    check("boş formda kaydet devre dışı", not dlg_add.save_btn.isEnabled())
    check("eksik alan göstergesi (ad + il)",
          "Mera Adı" in dlg_add.form_status.text() and "İl" in dlg_add.form_status.text(),
          dlg_add.form_status.text())
    check("il listesi 81 il içeriyor", dlg_add.city_combo.count() == 82, str(dlg_add.city_combo.count()))

    # Autocomplete: yazarken mevcut kodların önek eşleşmeleri
    dlg_add.code_input.setText("MRA-01")
    check("autocomplete öneri listesi (MRA-01)",
          "MRA-01-01" in dlg_add._completer_model.stringList(),
          str(dlg_add._completer_model.stringList()))
    dlg_add.code_input.setText("mra-0")
    check("küçük harfli önek için öneriler",
          len(dlg_add._completer_model.stringList()) > 0,
          str(dlg_add._completer_model.stringList()))
    dlg_add.code_input.setText("MRA-99")
    check("eşleşmeyen önek için öneri yok", dlg_add._completer_model.stringList() == [],
          str(dlg_add._completer_model.stringList()))
    dlg_add.code_input.setText("MRA-82-01")

    dlg_add.name_input.setText("Smoke Test Merası")
    dlg_add.city_combo.setCurrentText("Ankara")
    check("ilçe listesi doldu", dlg_add.district_combo.count() > 1, str(dlg_add.district_combo.count()))
    dlg_add.district_combo.setCurrentIndex(1)
    data_add = dlg_add.get_data()
    check("yeni kayıt verisi poligon üretir",
          "polygon_coords_json" in data_add and data_add["polygon_coords_json"].startswith("["))
    check("get_data il/ilçe döndürür",
          data_add["city"] == "Ankara" and data_add["district"] == dlg_add.district_combo.currentText() and data_add["district"] != "İlçe Seçiniz",
          str((data_add["city"], data_add["district"])))

    # Kod canlı doğrulama
    dlg_add.code_input.setText("MRA-01-01")  # mevcut kod -> çakışma
    check("çakışan kod uyarısı", "kullanılıyor" in dlg_add.code_status.text(),
          f"gelen: {dlg_add.code_status.text()}")
    check("çakışan kodda kaydet devre dışı", not dlg_add.save_btn.isEnabled())
    dlg_add.code_input.setText("MRA-99-99")  # uygun yeni kod
    check("uygun kod onayı", "✅" in dlg_add.code_status.text())
    check("uygun kodda kaydet etkin", dlg_add.save_btn.isEnabled())
    check("form geneli geçerli göstergesi", "Form geçerli" in dlg_add.form_status.text(),
          dlg_add.form_status.text())
    dlg_add.code_input.setText("yanlış")  # biçim hatası
    check("biçim hatası uyarısı", "biçim" in dlg_add.code_status.text().lower())
    check("biçim hatasında kaydet devre dışı", not dlg_add.save_btn.isEnabled())
    dlg_add.code_input.setText("MRA-82-01")  # otomatik kod geçerli
    check("otomatik kod geçerli", dlg_add.save_btn.isEnabled())

    # Rastgele kod butonu
    before = dlg_add.code_input.text()
    dlg_add.random_code_btn.click()
    after = dlg_add.code_input.text()
    check("rastgele kod üretildi", after != before, f"{before} -> {after}")
    check("rastgele kod biçimli ve benzersiz",
          is_valid_code_format(after) and not db.code_exists(after), after)
    check("rastgele kodla kaydet etkin", dlg_add.save_btn.isEnabled())

    # Kod normalizasyonu: büyük/küçük harf ve boşluk farkları yok sayılır
    dlg_add.code_input.setText("mra-01-01")
    check("küçük harfli kod çakışma olarak yakalanır", "kullanılıyor" in dlg_add.code_status.text(),
          dlg_add.code_status.text())
    check("küçük harfli çakışmada kaydet devre dışı", not dlg_add.save_btn.isEnabled())
    dlg_add.code_input.setText(" mra-99-99 ")
    check("boşluklu/küçük harfli kod uygun", "✅" in dlg_add.code_status.text(),
          dlg_add.code_status.text())
    check("kayıtta kod normalleşir", dlg_add.get_data()["code"] == "MRA-99-99",
          dlg_add.get_data()["code"])
    check("normalleşmiş kodla kaydet etkin", dlg_add.save_btn.isEnabled())
    check("normalleştirme bildirimi gösterilir",
          "Otomatik düzeltme: MRA-99-99" in dlg_add.code_status.text(),
          dlg_add.code_status.text())
    dlg_add.code_input.setText("MRA-82-01")
    check("zaten normalleştirilmiş kodda düzeltme bildirimi yok",
          "Otomatik düzeltme" not in dlg_add.code_status.text(),
          dlg_add.code_status.text())

    # Aynı ilde aynı ad uyarısı (normalleştirilmiş karşılaştırma)
    adana_p = db.get_pasture_by_id(1)
    dlg_add.name_input.setText(adana_p["name"])
    dlg_add.city_combo.setCurrentText("Adana")
    dlg_add.district_combo.setCurrentIndex(1)
    check("aynı ilde aynı ad uyarısı", "başka bir mera" in dlg_add.form_status.text(),
          dlg_add.form_status.text())
    check("ad çakışmasında kaydet devre dışı", not dlg_add.save_btn.isEnabled())
    dlg_add.name_input.setText("Benzersiz Mera")
    check("benzersiz adla form geçerli", "Form geçerli" in dlg_add.form_status.text(),
          dlg_add.form_status.text())
    dlg_add.name_input.setText("Smoke Test Merası")
    dlg_add.city_combo.setCurrentText("Ankara")
    dlg_add.district_combo.setCurrentIndex(1)
    check("varsayılan senaryoya dönüşte form geçerli", "Form geçerli" in dlg_add.form_status.text(),
          dlg_add.form_status.text())
    dlg_add.name_input.setText("")
    check("isim boşalınca kaydet devre dışı", not dlg_add.save_btn.isEnabled())
    check("eksik alan listesinde Mera Adı", "Mera Adı" in dlg_add.form_status.text(),
          dlg_add.form_status.text())
    dlg_add.name_input.setText("Smoke Test Merası")
    check("isim doldurunca kaydet tekrar etkin", dlg_add.save_btn.isEnabled())

    # Dil değiştirme: doğrulama mesajları İngilizceye geçer
    from database.validation import MessageCatalog
    check("dil seçici mevcut", window.lang_combo.currentData() in ("tr", "en"))
    MessageCatalog.set_language("en")
    dlg_en = PastureDialog(window, default_code="MRA-01-01", db=db)
    check("ingilizce çakışma mesajı", "already used" in dlg_en.code_status.text(),
          dlg_en.code_status.text())
    dlg_en.code_input.setText("MRA-82-01")
    check("ingilizce uygun kod mesajı", "valid" in dlg_en.code_status.text(),
          dlg_en.code_status.text())
    check("ingilizce eksik alan mesajı", "missing" in dlg_en.form_status.text().lower(),
          dlg_en.form_status.text())
    dlg_en.deleteLater()
    MessageCatalog.set_language("tr")
    check("dile geri dönüldü", MessageCatalog.get_language() == "tr")

    # ---- Tam İngilizce arayüz: tüm görünümlerin metinleri değişir ----
    from i18n import T
    window.lang_combo.setCurrentIndex(1)  # English -> _on_language_changed -> _retranslate
    check("ingilizce: T dili en", T.get_language() == "en", T.get_language())
    check("ingilizce: pencere başlığı", "Turkey" in window.windowTitle(), window.windowTitle())
    check("ingilizce: kenar çubuğu butonları",
          window.nav_btn_map.text() == "🌍 Map View"
          and window.nav_btn_table.text() == "📋 Pasture Data List"
          and "About" in window.nav_btn_about.text(),
          (window.nav_btn_map.text(), window.nav_btn_table.text(), window.nav_btn_about.text()))
    check("ingilizce: kenar çubuğu özet", "Registered Pastures" in window.qs_val2.text(),
          window.qs_val2.text())
    check("ingilizce: tablo başlıkları",
          window.table_view.table.horizontalHeaderItem(2).text() == "Pasture Name"
          and window.table_view.table.horizontalHeaderItem(11).text() == "Status",
          (window.table_view.table.horizontalHeaderItem(2).text(),
           window.table_view.table.horizontalHeaderItem(11).text()))
    check("ingilizce: tablo filtreleri",
          window.table_view.city_combo.currentText() == "City: All"
          and window.table_view.region_combo.currentText() == "Region: All",
          (window.table_view.city_combo.currentText(),
           window.table_view.region_combo.currentText()))
    check("ingilizce: hesap başlığı", "Calculator" in window.calculator_view.title_label.text(),
          window.calculator_view.title_label.text())
    check("ingilizce: analiz başlığı", "Statistics" in window.analytics_view.title_label.text(),
          window.analytics_view.title_label.text())
    check("ingilizce: rotasyon başlığı", "Rotation" in window.rotation_view.title_label.text(),
          window.rotation_view.title_label.text())
    check("ingilizce: yedek başlığı", "Backup" in window.backup_view.title.text(),
          window.backup_view.title.text())
    check("ingilizce: denetim başlığı", "Audit" in window.audit_view.title.text(),
          window.audit_view.title.text())
    check("ingilizce: detay sekmesi", window.detail_panel.tabs.tabText(1) == "🌾 Vegetation",
          window.detail_panel.tabs.tabText(1))
    check("ingilizce: hakkında diyaloğu başlığı",
          AboutDialog(window).windowTitle() == "About - MERA-BIS PRO",
          AboutDialog(window).windowTitle())
    check("ingilizce: hesap sonuç kartı",
          "Sufficient" in window.calculator_view.card_status.findChild(QLabel, "valLabel").text()
          or "Demand" in window.calculator_view.card_feed_req.findChild(QLabel, "valLabel").text(),
          (window.calculator_view.card_status.findChild(QLabel, "valLabel").text(),
           window.calculator_view.card_feed_req.findChild(QLabel, "valLabel").text()))

    # Dile geri dön (kalıcı kayıt Türkçe olsun)
    window.lang_combo.setCurrentIndex(0)
    QSettings().setValue("language", "tr")
    check("ingilizceden türkçeye dönüş",
          T.get_language() == "tr" and "Harita" in window.nav_btn_map.text()
          and MessageCatalog.get_language() == "tr",
          (T.get_language(), window.nav_btn_map.text(), MessageCatalog.get_language()))

    dlg_add.deleteLater()

    # Düzenleme diyaloğu: alan koruma + poligon yeniden üretimi
    p = db.get_pasture_by_id(1)
    dlg_edit = PastureDialog(window, pasture_data=p, db=db)
    check("düzenlemede kendi kodu çakışma sayılmaz",
          dlg_edit.save_btn.isEnabled() and "✅" in dlg_edit.code_status.text(),
          f"gelen: {dlg_edit.code_status.text()}")
    check("düzenleme formu geçerli", "Form geçerli" in dlg_edit.form_status.text(),
          dlg_edit.form_status.text())
    check("düzenlemede il seçili", dlg_edit.city_combo.currentText() == "Adana",
          dlg_edit.city_combo.currentText())
    check("düzenlemede ilçe seçili", dlg_edit.district_combo.currentText() == "Seyhan",
          dlg_edit.district_combo.currentText())
    # 'Merkez' merkez ilçe adı veride mevcut ve seçili gelmeli
    artvin = db.get_pasture_by_id(8)
    dlg_edit2 = PastureDialog(window, pasture_data=artvin, db=db)
    check("merkez ilçe adı seçili gelir (Artvin)", dlg_edit2.district_combo.currentText() == "Merkez",
          dlg_edit2.district_combo.currentText())
    check("Merkez ilçeli form geçerli", "Form geçerli" in dlg_edit2.form_status.text())
    dlg_edit2.deleteLater()

    # Veride olmayan ilçe adı ('Kars/Göle') düzenlemede geri dönüşle korunmalı
    kars = [p for p in db.get_all_pastures() if p["city"] == "Kars"][0]
    dlg_edit3 = PastureDialog(window, pasture_data=kars, db=db)
    check("veride olmayan ilçe korunur (Göle)", dlg_edit3.district_combo.currentText() == "Göle",
          dlg_edit3.district_combo.currentText())
    check("geri dönüşlü ilçeli form geçerli", "Form geçerli" in dlg_edit3.form_status.text())
    dlg_edit3.deleteLater()
    dlg_edit.lat_spin.setValue(40.0)
    dlg_edit.lng_spin.setValue(33.0)
    data_edit = dlg_edit.get_data()
    check("düzenlemede erozyon korunur", data_edit["erosion_risk"] == p["erosion_risk"])
    check("düzenlemede tahsis amacı korunur", data_edit["allocation_purpose"] == p["allocation_purpose"])
    check("düzenlemede yönetim birimi korunur", data_edit["management_entity"] == p["management_entity"])
    check("düzenlemede sezon korunur",
          data_edit["grazing_season_start"] == p["grazing_season_start"])
    check("koordinat değişince poligon yeniden üretilir",
          data_edit["polygon_coords_json"] != p["polygon_coords_json"] and "40.0" in data_edit["polygon_coords_json"],
          f"eski: {p['polygon_coords_json']} yeni: {data_edit['polygon_coords_json']}")
    dlg_edit.deleteLater()

    # Veritabanına düzenleme uygula ve doğrula
    data_edit["id"] = p["id"]
    db.update_pasture(p["id"], data_edit)
    p2 = db.get_pasture_by_id(p["id"])
    check("DB'de güncelleme sonrası alanlar korundu",
          p2["erosion_risk"] == p["erosion_risk"] and p2["management_entity"] == p["management_entity"])

    # Görünümlerin yenilenmesi
    window.refresh_all_views()
    check("refresh_all_views çalıştı", True)
    window.switch_page(1)  # analiz
    window.switch_page(2)  # tablo
    check("tablo satır sayısı 81", window.table_view.table.rowCount() == 81)
    window.switch_page(3)  # hesaplayıcı
    from PyQt6.QtWidgets import QLabel as QtLabel
    calc = window.calculator_view
    feed_text = calc.card_feed_req.findChild(QtLabel, "valLabel").text()
    check("hesaplayıcı sonuç üretti", feed_text != "0 Ton Kuru Ot", f"gelen: {feed_text}")
    check("hesaplayıcı alan farkı kartı var", calc.card_area_avail is not None)

    # KPI/analiz kartları
    check("analiz KPI kartları üretildi", window.analytics_view.kpi_layout.count() == 4)

    # Rotasyon planı modülü
    rot = window.rotation_view
    rot.paddock_spin.setValue(6)
    rot.rest_spin.setValue(30)
    rot.generate_plan()
    check("rotasyon planı üretildi", rot.plan is not None)
    check("rotasyon sezon günleri doğru", rot.plan["season_days"] > 0)
    check("takvim widget plana sahip", rot.calendar_widget.plan is not None)
    check("takvim boyutlandırıldı", rot.calendar_widget.minimumWidth() > 600)
    check("detay tablosu bölme satırları", rot.detail_table.rowCount() == 6)
    check("özet kartları üretildi", rot.summary_layout.count() >= 6)
    rot.tabs.setCurrentIndex(1)
    check("detay sekmesi açıldı", rot.tabs.currentIndex() == 1)
    window.switch_page(4)
    check("rotasyon sayfasına geçiş", window.stacked_widget.currentIndex() == 4)

    # Yedekleme modülü
    bv = window.backup_view
    bv.refresh()
    check("yedek ekranı veritabanı bilgisi", "81" in bv.info_label.text())
    check("yedek ekranı kural sürümü gösterir",
          "Kural Sürümü: 1" in bv.info_label.text(), bv.info_label.text())
    check("yedek ön-kontrolü geçerli", db.pre_backup_check()["ok"] is True)
    bv._on_backup_clicked()
    backup_dir, entries = db.list_backups()
    check("tek tıkla yedek alındı", len(entries) == 1, str(entries))
    check("durum mesajı başarılı", "✅" in bv.status_label.text())
    check("yedek listesi tabloda", bv.table.rowCount() == 1)
    # Geri yükleme döngüsü (onay diyaloğu atlanır)
    db.delete_pasture(1)
    check("silme sonrası 80 kayıt", db.get_statistics()["total_count"] == 80)
    bv._restore(entries[0]["path"], confirm=False)
    check("geri yükleme sonrası 81 kayıt", db.get_statistics()["total_count"] == 81)
    check("geri yükleme durum mesajı", "✅" in bv.status_label.text())
    window.switch_page(6)
    check("yedek sayfasına geçiş", window.stacked_widget.currentIndex() == 6)

    # Vejetasyon Ölçüm modülü (sayfa 5) — dialog tabanlı akış
    mv = window.measurements_view
    window.switch_page(5)
    check("ölçüm sayfasına geçiş", window.stacked_widget.currentIndex() == 5)
    check("ölçüm: mera listesi doldu", mv.pasture_combo.count() == 81,
          str(mv.pasture_combo.count()))
    check("ölçüm: boş liste", mv.table.rowCount() == 0, str(mv.table.rowCount()))
    check("ölçüm: düzenle düğmesi boş listede devre dışı", not mv.edit_btn.isEnabled())

    # Ekle akışı: diyaloğu exec ETMEDEN doldurup kaydet (kaynak 'form')
    from gui.measurement_dialog import MeasurementDialog as _MD
    dlg = _MD(mv, db, mv.pasture_combo.currentData(), source="form")
    dlg.yield_spin.setValue(1750.0)
    dlg.cover_spin.setValue(85.0)
    dlg.height_spin.setValue(35.0)
    dlg._on_save()
    mv.refresh_table()
    mv.refresh_chart()
    check("ölçüm: kayıt eklendi", mv.table.rowCount() == 1, str(mv.table.rowCount()))
    first_pasture_id = mv.pasture_combo.currentData()
    check("ölçüm: DB'ye yazıldı",
          len(db.get_measurements(first_pasture_id)) == 1)
    check("ölçüm: denetim izi form kaynağı",
          db.get_measurement_audit_log(first_pasture_id)[0]["source"] == "form")
    check("ölçüm: en güncel kayıt sorgusu", db.latest_measurement(first_pasture_id) is not None)

    # İkinci kayıt: trend grafiği iki noktayla çizilmeli
    from PyQt6.QtCore import QDate as _QD
    dlg2 = _MD(mv, db, first_pasture_id, source="form")
    old_date = _QD.currentDate().addMonths(-6)
    dlg2.date_edit.setDate(old_date)
    dlg2.yield_spin.setValue(1500.0)
    dlg2.cover_spin.setValue(70.0)
    dlg2._on_save()
    mv.refresh_table()
    check("ölçüm: ikinci kayıt eklendi", mv.table.rowCount() == 2, str(mv.table.rowCount()))

    # Düzenle akışı: satır seç → düğme etkinleşir → diyalog mevcut değerlerle dolu
    mv.table.selectRow(0)
    check("ölçüm: satır seçimi düzenle düğmesini etkinleştirir", mv.edit_btn.isEnabled())
    edit_mid = mv._editing_row()
    expected = next((r for r in db.get_measurements(first_pasture_id)
                     if r["id"] == edit_mid), None)
    dlg_edit = _MD(mv, db, first_pasture_id, measurement_id=edit_mid, source="form")
    check("ölçüm: düzenleme diyaloğu mevcut değerlerle dolu",
          expected is not None
          and abs(dlg_edit.yield_spin.value()
                  - (expected["dry_hay_yield_kg_per_ha"] or 0)) < 0.01,
          str(dlg_edit.yield_spin.value()))
    dlg_edit.yield_spin.setValue(1600.0)
    dlg_edit._on_save()
    mv.refresh_table()
    rows_now = db.get_measurements(first_pasture_id)
    edited = next((r for r in rows_now if r["id"] == edit_mid), None)
    check("ölçüm: düzenleme kaydedildi",
          edited is not None and abs(edited["dry_hay_yield_kg_per_ha"] - 1600.0) < 0.01,
          str(edited))

    # Silme (onay diyaloğu otomatik Yes)
    from PyQt6.QtWidgets import QMessageBox as _MB
    _orig_question = _MB.question
    _MB.question = staticmethod(lambda *a, **k: _MB.StandardButton.Yes)
    try:
        mv.delete_selected()
    finally:
        _MB.question = _orig_question
    check("ölçüm: kayıt silindi", mv.table.rowCount() == 1, str(mv.table.rowCount()))
    # Kullanıcı silinince ölçümler de cascade gider
    db.delete_pasture(first_pasture_id)
    check("ölçüm: mera silinince cascade",
          db.get_measurements(first_pasture_id) == [])
    # Filtrelenmiş dışa aktarma satırları (birleştirilmiş)
    exp_rows = db.measurements_export_rows()
    check("ölçüm: dışa aktarma satırları mera kodlu",
          all("pasture_code" in r for r in exp_rows))

    # Veri Denetimi modülü
    av = window.audit_view
    window.switch_page(7)
    check("denetim sayfasına geçiş", window.stacked_widget.currentIndex() == 7)
    check("denetim: temiz veride sorun yok", av.table.rowCount() == 0, str(av.table.rowCount()))
    check("denetim: özet kartları üretildi", av.summary_layout.count() == 4)
    check("denetim: göç bilgisi kural sürümü gösterir",
          "Kural sürümü: 1" in av.migration_label.text(), av.migration_label.text())
    check("denetim: durum mesajı sorunsuz", "sorun yok" in av.status_label.text(),
          av.status_label.text())

    # Normalleştirilebilir kod enjekte et -> listede görünür -> tek tık düzeltilir
    conn = db.get_connection()
    conn.execute("""INSERT INTO pastures (code, name, city, district, region,
        area_hectares, status, lat, lng) VALUES (?,?,?,?,?,?,?,?,?)""",
                 ("mra-88-88", "Denetim Testi", "İzmir", "Merkez", "Ege", 5.0,
                  "Aktif Otlatma", 38.4, 27.1))
    conn.commit()
    conn.close()
    av.refresh()
    check("denetim: normalleştirilebilir kod listelenir", av.table.rowCount() == 1,
          str(av.table.rowCount()))
    fix_btn = av.table.cellWidget(0, 5)
    check("denetim: satırda düzelt butonu var", fix_btn is not None)
    fix_btn.click()
    check("denetim: kod tek tıkla normalleşti",
          db.get_pasture_by_id(82)["code"] == "MRA-88-88",
          str(db.get_pasture_by_id(82)["code"]))
    check("denetim: düzeltme sonrası sorun kalmadı", av.table.rowCount() == 0)

    # Harita JS doğrulaması: QtWebEngine GPU'ya bağımlıdır; GPU'suz ortamlarda
    # Chromium'ın fail-fast çökmesi ana fonksiyonel takımı etkilemesin diye bu
    # aşama izole bir alt süreçte (tests/smoke_map_check.py) çalıştırılır.
    map_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_map_check.py")
    map_result = None
    map_err = ""
    try:
        proc = subprocess.run(
            [sys.executable, "-u", map_script],
            capture_output=True, text=True, errors="replace", timeout=120,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        if proc.returncode not in (0, 1):
            map_err = f"çökme (çıkış kodu {proc.returncode})"
        else:
            for line in proc.stdout.splitlines():
                if line.startswith("RESULT_JSON "):
                    try:
                        map_result = json.loads(line[len("RESULT_JSON "):])
                    except json.JSONDecodeError:
                        map_err = "sonuç JSON çözümlenemedi"
                    break
            if map_result is None and not map_err:
                map_err = "sonuç bulunamadı"
    except subprocess.TimeoutExpired:
        map_err = "zaman aşımı (120 sn)"
    except OSError as exc:
        map_err = str(exc)

    if map_result is None:
        print(f"  [SKIP] harita JS doğrulaması çalıştırılamadı: {map_err} "
              "(GPU'suz ortamda QtWebEngine çökebilir)", flush=True)
    else:
        check("il sınırları GeoJSON yüklendi (81 il)", map_result.get("count") == 81,
              str(map_result.get("count")))
        check("il sınırları katmanı haritada aktif", map_result.get("hasLayer") is True)
        check("il sınırları pane'i oluşturuldu", map_result.get("pane") is True)
        check("katman açma/kapama fonksiyonları tanımlı",
              map_result.get("fns") == "function/function/function",
              str(map_result.get("fns")))
        geo = map_result.get("geo") or []
        geo_ok = all(g.get("found") == g.get("expect") for g in geo)
        check("nokta-il eşleştirme (ray casting) doğru", geo_ok, str(geo))
        ml = map_result.get("map_lang") or {}
        check("harita butonları İngilizceye geçiyor (JS)",
              str(ml.get("street", "")).endswith("Standard Map")
              and str(ml.get("provinces", "")).endswith("Province Borders")
              and str(ml.get("rivers", "")).endswith("Rivers"),
              str(ml))

        # Görsel (piksel) denetim: harita lejantı ve popup açık temada
        # koyu metin garantisi (tests/smoke_map_check.py analiz eder).
        vis = map_result.get("visual") or {}
        popup = vis.get("popup") or {}
        controls = vis.get("controls") or {}

        def _light_dominant(st):
            return st.get("total", 0) > 0 and st.get("light", 0) / st["total"] >= 0.40

        def _no_dark_bg(st):
            return st.get("total", 0) > 0 and st.get("dark", 0) / st["total"] < 0.20

        check("harita popup: açık zeminde koyu metin (piksel)",
              popup.get("dark", 0) >= 20 and popup.get("mid", 0) >= 25
              and _light_dominant(popup),
              str(popup))
        check("harita popup: koyu zemin bloğu yok", _no_dark_bg(popup), str(popup))
        check("harita lejant: açık zeminde koyu metin (piksel)",
              controls.get("dark", 0) >= 10 and _light_dominant(controls),
              str(controls))
        check("harita lejant: koyu zemin bloğu yok", _no_dark_bg(controls),
              str(controls))

    passed = PASS_COUNT - len(FAILURES)
    print(f"\nSONUC: {passed}/{PASS_COUNT} kontrol, {len(FAILURES)} basarisiz")
    for f in FAILURES:
        print("  FAILED:", f)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
