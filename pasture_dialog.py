import json
import random
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QPushButton, QFormLayout, QGroupBox, QMessageBox,
    QDateEdit, QCompleter
)
from PyQt6.QtCore import QDate, Qt, QStringListModel

from gui.turkey_data import PROVINCE_NAMES, get_districts
from database.validation import (
    MessageCatalog,
    normalize_code as _norm_code,
    code_status_message,
    name_city_status_message,
)
from i18n import T


def _parse_season(value, default="05-01"):
    """'MM-DD' biçimindeki metni QDate'e çevirir, geçersizse varsayılanı kullanır."""
    if value:
        d = QDate.fromString(str(value), "MM-dd")
        if d.isValid():
            return d
    return QDate.fromString(default, "MM-dd")

class PastureDialog(QDialog):
    def __init__(self, parent=None, pasture_data=None, default_code=None, db=None):
        super().__init__(parent)
        self.pasture_data = pasture_data or {}
        self.is_edit = bool(pasture_data)
        self.default_code = default_code or self.pasture_data.get("code", "MRA-01-01")
        self.db = db
        # Düzenlemede kendi kaydının kodu çakışma olarak sayılmaz
        self.exclude_id = self.pasture_data.get("id") if self.is_edit else None
        self._init_ui()

    def _init_ui(self):
        if self.is_edit:
            self.setWindowTitle(T.get("dialog.title_edit", name=self.pasture_data.get("name", "")))
        else:
            self.setWindowTitle(T.get("dialog.title_add"))
        self.resize(550, 650)
        self.setStyleSheet("""
            QDialog { background-color: #EDF4EA; color: #23332A; }
            QLabel { color: #5C7164; font-weight: bold; }
        """)

        main_layout = QVBoxLayout(self)

        title_lbl = QLabel(T.get("dialog.header_edit") if self.is_edit else T.get("dialog.header_add"))
        title_lbl.setStyleSheet("font-size: 18px; color: #558B2F; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_lbl)

        form_box = QGroupBox(T.get("dialog.group"))
        form = QFormLayout(form_box)

        self.code_input = QLineEdit(self.default_code)
        self.code_input.textChanged.connect(self._refresh_form_state)

        # Autocomplete: yazarken mevcut kodların önek eşleşmelerini öner
        self._completer_model = QStringListModel(self)
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.code_input.setCompleter(self._completer)
        self.code_input.textChanged.connect(self._refresh_code_suggestions)

        self.random_code_btn = QPushButton(T.get("dialog.btn_random"))
        self.random_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #3D5245; border: 1px solid #C6DBC1;
                border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { border-color: #7CB342; color: #558B2F; }
        """)
        self.random_code_btn.setToolTip(T.get("dialog.btn_random_tip"))
        self.random_code_btn.clicked.connect(self._on_random_code)
        self.code_status = QLabel("")
        self.code_status.setWordWrap(True)
        self.name_input = QLineEdit(self.pasture_data.get("name", ""))
        self.name_input.textChanged.connect(self._refresh_form_state)

        self.region_combo = QComboBox()
        self.region_combo.addItems(["Doğu Anadolu", "İç Anadolu", "Güneydoğu Anadolu", "Ege", "Karadeniz", "Akdeniz", "Marmara"])
        if self.pasture_data.get("region"):
            self.region_combo.setCurrentText(self.pasture_data["region"])

        self.city_combo = QComboBox()
        self.city_combo.addItem(MessageCatalog.get("select_city"), "placeholder")
        self.city_combo.addItems(PROVINCE_NAMES)
        self.city_combo.currentTextChanged.connect(self._on_city_changed)

        self.district_combo = QComboBox()
        self.district_combo.addItem(MessageCatalog.get("select_district"), "placeholder")
        self.district_combo.currentTextChanged.connect(self._refresh_form_state)

        self.village_input = QLineEdit(self.pasture_data.get("village", ""))

        self.area_spin = QDoubleSpinBox()
        self.area_spin.setRange(1.0, 1000000.0)
        self.area_spin.setValue(float(self.pasture_data.get("area_hectares", 1000.0)))
        self.area_spin.setSuffix(" Ha")

        self.elevation_spin = QSpinBox()
        self.elevation_spin.setRange(0, 5000)
        self.elevation_spin.setValue(int(self.pasture_data.get("elevation_m", 1200)))
        self.elevation_spin.setSuffix(" m")

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(35.0, 43.0)
        self.lat_spin.setDecimals(4)
        self.lat_spin.setValue(float(self.pasture_data.get("lat", 39.0)))

        self.lng_spin = QDoubleSpinBox()
        self.lng_spin.setRange(25.0, 45.0)
        self.lng_spin.setDecimals(4)
        self.lng_spin.setValue(float(self.pasture_data.get("lng", 35.0)))

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Aktif Otlatma", "Dinlendirmede / Islah", "Koruma Altında"])
        if self.pasture_data.get("status"):
            self.status_combo.setCurrentText(self.pasture_data["status"])

        self.bbhb_spin = QSpinBox()
        self.bbhb_spin.setRange(0, 100000)
        self.bbhb_spin.setValue(int(self.pasture_data.get("bbhb_capacity", 1500)))

        self.kbhb_spin = QSpinBox()
        self.kbhb_spin.setRange(0, 500000)
        self.kbhb_spin.setValue(int(self.pasture_data.get("kbhb_capacity", 10000)))

        self.yield_spin = QDoubleSpinBox()
        self.yield_spin.setRange(0.0, 10000.0)
        self.yield_spin.setValue(float(self.pasture_data.get("dry_hay_yield_kg_per_ha", 1500.0)))
        self.yield_spin.setSuffix(" kg/ha")

        self.cov_spin = QSpinBox()
        self.cov_spin.setRange(0, 100)
        self.cov_spin.setValue(int(self.pasture_data.get("vegetation_coverage_pct", 75)))
        self.cov_spin.setSuffix(" %")

        self.plants_input = QLineEdit(self.pasture_data.get("dominant_plants", "Yonca, Korunga, Çayır Otları"))
        self.water_input = QLineEdit(self.pasture_data.get("water_source", "Gölet, Dere, 2 Çeşme"))
        self.soil_input = QLineEdit(self.pasture_data.get("soil_type", "Killi-Tınlı Toprak"))

        self.season_start = QDateEdit(_parse_season(self.pasture_data.get("grazing_season_start"), "05-01"))
        self.season_start.setDisplayFormat("MM-dd")
        self.season_end = QDateEdit(_parse_season(self.pasture_data.get("grazing_season_end"), "10-01"))
        self.season_end.setDisplayFormat("MM-dd")

        self.notes_input = QTextEdit()
        self.notes_input.setPlainText(self.pasture_data.get("notes", ""))
        self.notes_input.setMaximumHeight(70)

        code_row_widget = QWidget()
        code_row = QHBoxLayout(code_row_widget)
        code_row.setContentsMargins(0, 0, 0, 0)
        code_row.setSpacing(8)
        code_row.addWidget(self.code_input, stretch=1)
        code_row.addWidget(self.random_code_btn)
        form.addRow(T.get("dialog.lbl_code"), code_row_widget)
        form.addRow("", self.code_status)
        form.addRow(T.get("dialog.lbl_name"), self.name_input)
        form.addRow(T.get("dialog.lbl_region"), self.region_combo)
        form.addRow(T.get("dialog.lbl_city"), self.city_combo)
        form.addRow(T.get("dialog.lbl_district"), self.district_combo)
        form.addRow(T.get("dialog.lbl_village"), self.village_input)
        form.addRow(T.get("dialog.lbl_area"), self.area_spin)
        form.addRow(T.get("dialog.lbl_elevation"), self.elevation_spin)
        form.addRow(T.get("dialog.lbl_lat"), self.lat_spin)
        form.addRow(T.get("dialog.lbl_lng"), self.lng_spin)
        form.addRow(T.get("dialog.lbl_status"), self.status_combo)
        form.addRow(T.get("dialog.lbl_bbhb"), self.bbhb_spin)
        form.addRow(T.get("dialog.lbl_kbhb"), self.kbhb_spin)
        form.addRow(T.get("dialog.lbl_yield"), self.yield_spin)
        form.addRow(T.get("dialog.lbl_cov"), self.cov_spin)
        form.addRow(T.get("dialog.lbl_plants"), self.plants_input)
        form.addRow(T.get("dialog.lbl_water"), self.water_input)
        form.addRow(T.get("dialog.lbl_soil"), self.soil_input)
        form.addRow(T.get("dialog.lbl_season_start"), self.season_start)
        form.addRow(T.get("dialog.lbl_season_end"), self.season_end)
        form.addRow(T.get("dialog.lbl_notes"), self.notes_input)

        main_layout.addWidget(form_box)

        # Form geneli geçerlilik göstergesi
        self.form_status = QLabel("")
        self.form_status.setWordWrap(True)
        self.form_status.setStyleSheet("font-size: 13px; font-weight: bold; padding: 6px;")
        main_layout.addWidget(self.form_status)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(T.get("dialog.btn_save"))
        self.save_btn.setStyleSheet("background-color: #7CB342; color: #FFFFFF; font-weight: bold; padding: 10px; border-radius: 6px;")
        self.save_btn.clicked.connect(self._on_save)

        cancel_btn = QPushButton(T.get("dialog.btn_cancel"))
        cancel_btn.setStyleSheet("background-color: #FFFFFF; color: #3D5245; border: 1px solid #C6DBC1; padding: 10px; border-radius: 6px;")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

        # Düzenlemede mevcut il/ilçe değerlerini yükle (tüm widget'lar hazır olduktan sonra;
        # veride olmayan il/ilçe adları listeye eklenerek korunur)
        self._editing_district = self.pasture_data.get("district", "")
        city = self.pasture_data.get("city", "")
        if city and city in PROVINCE_NAMES:
            self.city_combo.setCurrentText(city)
        elif city:
            self.city_combo.addItem(city)
            self.city_combo.setCurrentText(city)
        self._on_city_changed()

        # Açılışta tüm formu doğrula (örn. düzenlemede başka kayıt aynı kodu almış olabilir)
        self._refresh_form_state()

    def _normalized_code(self):
        """Girilen kodu normalleştirir (ortak doğrulama servisi)."""
        return _norm_code(self.code_input.text())

    def _refresh_code_suggestions(self):
        """Autocomplete önerilerini girilen öneke göre günceller."""
        if not self.db:
            self._completer_model.setStringList([])
            return
        self._completer_model.setStringList(self.db.search_codes(self.code_input.text()))

    def _validate_code(self):
        """Kodu ortak doğrulama servisiyle denetler: biçim + veritabanındaki çakışma.
        Girilen kod normalleştirmeden farklıysa otomatik düzeltmeyi anlık gösterir."""
        raw = self.code_input.text()
        code = self._normalized_code()
        taken = self.db.get_taken_codes(self.exclude_id) if self.db else None
        ok, message = code_status_message(code, taken_codes=taken)

        if ok:
            border = "QLineEdit { border: 1px solid #7CB342; }"
            rendered = MessageCatalog.get("mark_ok") + " " + message
            if raw != code:
                # Normalleştirme girişi değiştirdiyse kullanıcıya bildir (alan yeniden yazılmaz)
                rendered += " • " + MessageCatalog.get("auto_fix", code=code)
        else:
            border = "QLineEdit { border: 1px solid #EF4444; }"
            rendered = MessageCatalog.get("mark_warn") + " " + message

        self.code_status.setText(rendered)
        self.code_status.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {'#558B2F' if ok else '#DC2626'};"
        )
        self.code_input.setStyleSheet(border)
        return ok

    def _validate_required(self):
        """Zorunlu alanları (Mera Adı, İl, İlçe) doğrular; eksik alanların listesini döndürür."""
        missing = []
        if not self.name_input.text().strip():
            missing.append(MessageCatalog.get("field_name"))
        if self.city_combo.currentData() == "placeholder":
            missing.append(MessageCatalog.get("field_city"))
        if self.district_combo.currentData() == "placeholder":
            missing.append(MessageCatalog.get("field_district"))

        field_name = MessageCatalog.get("field_name")
        field_city = MessageCatalog.get("field_city")
        field_district = MessageCatalog.get("field_district")
        self.name_input.setStyleSheet(
            "QLineEdit { border: 1px solid #EF4444; }" if field_name in missing
            else "QLineEdit { border: 1px solid #7CB342; }"
        )
        self.city_combo.setStyleSheet(
            "QComboBox { border: 1px solid #EF4444; }" if field_city in missing
            else "QComboBox { border: 1px solid #7CB342; }"
        )
        self.district_combo.setStyleSheet(
            "QComboBox { border: 1px solid #EF4444; }" if field_district in missing
            else "QComboBox { border: 1px solid #7CB342; }"
        )
        return missing

    def _on_city_changed(self):
        """İl seçilince ilçe listesini doldurur; mevcut ilçeyi korur."""
        city = self.city_combo.currentText()
        self.district_combo.blockSignals(True)
        self.district_combo.clear()
        self.district_combo.addItem(MessageCatalog.get("select_district"), "placeholder")
        districts = get_districts(city)
        self.district_combo.addItems(districts)

        current_district = self._editing_district
        if current_district and current_district != MessageCatalog.get("select_district"):
            if current_district in districts:
                self.district_combo.setCurrentText(current_district)
            else:
                # Veride olmayan ilçe (örn. 'Merkez') düzenlemede korunur
                self.district_combo.addItem(current_district)
                self.district_combo.setCurrentText(current_district)
        self.district_combo.blockSignals(False)
        self._refresh_form_state()

    def _check_name_duplicate(self):
        """Aynı ilde aynı adla başka mera var mı? Ortak servis kuralıyla (uyarı metni veya boş)."""
        if not self.db:
            return ""
        name = self.name_input.text().strip()
        if not name or self.city_combo.currentData() == "placeholder":
            return ""
        city = self.city_combo.currentText()
        taken = self.db.get_taken_name_city_pairs(self.exclude_id)
        ok, message = name_city_status_message(name, city, taken_pairs=taken)
        return "" if ok else message

    def _refresh_form_state(self):
        """Form geneli geçerliliği günceller: alan uyarıları, gösterge ve kaydet butonu."""
        code_ok = self._validate_code()
        missing = self._validate_required()
        name_dup = self._check_name_duplicate()

        self.name_input.setStyleSheet(
            "QLineEdit { border: 1px solid #EF4444; }" if name_dup
            else ("QLineEdit { border: 1px solid #EF4444; }"
                  if MessageCatalog.get("field_name") in missing
                  else "QLineEdit { border: 1px solid #7CB342; }")
        )

        if code_ok and not missing and not name_dup:
            self.form_status.setText(
                MessageCatalog.get("mark_ok") + " " + MessageCatalog.get("form_valid")
            )
            self.form_status.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #558B2F; background-color: #E7F1E2; "
                "border: 1px solid #C6DBC1; border-radius: 6px; padding: 6px;"
            )
            self.save_btn.setEnabled(True)
        else:
            problems = []
            if missing:
                problems.append(MessageCatalog.get("missing_prefix") + ", ".join(missing))
            if name_dup:
                problems.append(MessageCatalog.get("problem_name") + name_dup)
            if not code_ok:
                problems.append(MessageCatalog.get("problem_code") + self.code_status.text())
            self.form_status.setText(
                MessageCatalog.get("mark_warn") + " " + " • ".join(problems)
            )
            self.form_status.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #DC2626; background-color: #FDECEA; "
                "border: 1px solid #F5C6C2; border-radius: 6px; padding: 6px;"
            )
            self.save_btn.setEnabled(False)

    def _on_random_code(self):
        """Kod alanını benzersiz rastgele bir kodla değiştirir."""
        if self.db:
            self.code_input.setText(self.db.get_random_code(exclude_id=self.exclude_id))
        else:
            self.code_input.setText(f"MRA-{random.randint(1, 999):02d}-{random.randint(1, 99):02d}")

    def _on_save(self):
        self._refresh_form_state()
        if not self.save_btn.isEnabled():
            QMessageBox.warning(self, T.get("dialog.msg_warn_title"), self.form_status.text())
            return
        self.accept()

    def get_data(self):
        # Poligon, her zaman güncel enlem/boylam değerlerinden üretilir;
        # böylece düzenlemede koordinat değişince haritadaki alan da taşınır.
        lat = self.lat_spin.value()
        lng = self.lng_spin.value()
        polygon = json.dumps([
            [round(lat + 0.01, 4), round(lng - 0.01, 4)],
            [round(lat + 0.01, 4), round(lng + 0.01, 4)],
            [round(lat - 0.01, 4), round(lng + 0.01, 4)],
            [round(lat - 0.01, 4), round(lng - 0.01, 4)]
        ])
        return {
            "code": self._normalized_code(),
            "name": self.name_input.text().strip(),
            "region": self.region_combo.currentText(),
            "city": self.city_combo.currentText(),
            "district": self.district_combo.currentText(),
            "village": self.village_input.text().strip(),
            "area_hectares": self.area_spin.value(),
            "elevation_m": self.elevation_spin.value(),
            "lat": lat,
            "lng": lng,
            "status": self.status_combo.currentText(),
            "bbhb_capacity": self.bbhb_spin.value(),
            "kbhb_capacity": self.kbhb_spin.value(),
            "dry_hay_yield_kg_per_ha": self.yield_spin.value(),
            "vegetation_coverage_pct": self.cov_spin.value(),
            "dominant_plants": self.plants_input.text().strip(),
            "water_source": self.water_input.text().strip(),
            "soil_type": self.soil_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
            "polygon_coords_json": polygon,
            # Dialogda düzenlenmeyen alanlar: düzenlemede mevcut değerleri KORUNUR
            # (boş string ile üzerine yazılıp veri kaybı yaşanmaz), yeni kayıtta
            # anlamlı varsayılan değerler kullanılır.
            "erosion_risk": self.pasture_data.get("erosion_risk", "Düşük - Orta"),
            "allocation_purpose": self.pasture_data.get("allocation_purpose", "Büyükbaş ve Küçükbaş Hayvancılık Otlatması"),
            "management_entity": self.pasture_data.get("management_entity", ""),
            "grazing_season_start": self.season_start.date().toString("MM-dd"),
            "grazing_season_end": self.season_end.date().toString("MM-dd"),
        }
