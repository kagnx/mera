from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

from gui.turkey_data import PROVINCE_NAMES
from i18n import T

REGIONS = ["Doğu Anadolu", "İç Anadolu", "Güneydoğu Anadolu", "Ege", "Karadeniz", "Akdeniz", "Marmara"]
STATUSES = ["Aktif Otlatma", "Dinlendirmede / Islah", "Koruma Altında"]

TABLE_HEADER_KEYS = [
    "table.h_id", "table.h_code", "table.h_name", "table.h_city",
    "table.h_district", "table.h_region", "table.h_area", "table.h_elevation",
    "table.h_bbhb", "table.h_kbhb", "table.h_yield", "table.h_status",
]


class NumericItem(QTableWidgetItem):
    """Sayısal değere göre sıralanan, biçimli metin gösteren tablo öğesi."""

    def __init__(self, value, text=None):
        super().__init__(text if text is not None else str(value))
        self._value = value

    def __lt__(self, other):
        try:
            return self._value < other._value
        except AttributeError:
            return super().__lt__(other)

class PastureTableView(QWidget):
    pastureSelected = pyqtSignal(dict)
    addRequested = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._init_ui()
        self.refresh_table()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Top Control Bar
        top_bar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T.get("table.search_placeholder"))
        self.search_input.textChanged.connect(self.refresh_table)

        self.city_combo = QComboBox()
        self.city_combo.currentIndexChanged.connect(self.refresh_table)

        self.region_combo = QComboBox()
        self.region_combo.currentIndexChanged.connect(self.refresh_table)

        self.status_combo = QComboBox()
        self.status_combo.currentIndexChanged.connect(self.refresh_table)

        self._fill_combos()

        self.add_btn = QPushButton(T.get("table.add_btn"))
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #7CB342; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 8px 14px;
            }
            QPushButton:hover { background-color: #9CCC65; }
        """)
        self.add_btn.clicked.connect(self.addRequested.emit)

        self.export_csv_btn = QPushButton(T.get("table.export_csv"))
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #3D5245; border: 1px solid #C6DBC1; border-radius: 6px; padding: 8px 12px;
            }
            QPushButton:hover { border-color: #7CB342; color: #558B2F; }
        """)
        self.export_csv_btn.clicked.connect(self._export_csv)

        self.export_json_btn = QPushButton(T.get("table.export_json"))
        self.export_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #3D5245; border: 1px solid #C6DBC1; border-radius: 6px; padding: 8px 12px;
            }
            QPushButton:hover { border-color: #7CB342; color: #558B2F; }
        """)
        self.export_json_btn.clicked.connect(self._export_json)

        top_bar.addWidget(self.search_input, stretch=2)
        top_bar.addWidget(self.city_combo)
        top_bar.addWidget(self.region_combo)
        top_bar.addWidget(self.status_combo)
        top_bar.addWidget(self.add_btn)
        top_bar.addWidget(self.export_csv_btn)
        top_bar.addWidget(self.export_json_btn)

        main_layout.addLayout(top_bar)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self._set_table_headers()

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col, width in enumerate((50, 100, 260, 110, 130, 140, 90, 90, 90, 90, 100, 160)):
            self.table.setColumnWidth(col, width)
        self.table.setSortingEnabled(True)
        # Sayısal sütunlarda metinsel değil sayısal sıralama yapılır
        for row_item_col in (0, 6, 7, 8, 9, 10):
            pass  # veri yazımında sayısal item olarak eklenir (aşağıda)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        self.table.doubleClicked.connect(self._on_row_double_clicked)
        main_layout.addWidget(self.table)

        # Bottom Bar info
        bottom_bar = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #5C7164; font-weight: bold;")
        self.area_label = QLabel("")
        self.area_label.setStyleSheet("color: #558B2F; font-weight: bold;")
        bottom_bar.addWidget(self.count_label)
        bottom_bar.addSpacing(20)
        bottom_bar.addWidget(self.area_label)
        bottom_bar.addStretch()

        main_layout.addLayout(bottom_bar)

    def _fill_combos(self):
        """İl/Bölge/Durum filtre listelerini doldurur (dil duyarlı 'Tümü' öğeleri)."""
        self.city_combo.blockSignals(True)
        self.region_combo.blockSignals(True)
        self.status_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItem(T.get("table.city_all"), "")
        self.city_combo.addItems(PROVINCE_NAMES)
        self.region_combo.clear()
        self.region_combo.addItem(T.get("table.region_all"), "")
        for r in REGIONS:
            self.region_combo.addItem(r, r)
        self.status_combo.clear()
        self.status_combo.addItem(T.get("table.status_all"), "")
        for s in STATUSES:
            self.status_combo.addItem(s, s)
        self.city_combo.blockSignals(False)
        self.region_combo.blockSignals(False)
        self.status_combo.blockSignals(False)

    def _set_table_headers(self):
        self.table.setHorizontalHeaderLabels([T.get(k) for k in TABLE_HEADER_KEYS])

    def retranslate(self):
        """Dil değişince filtreler, butonlar ve tablo başlıklarını günceller."""
        self.search_input.setPlaceholderText(T.get("table.search_placeholder"))
        self._fill_combos()
        self.add_btn.setText(T.get("table.add_btn"))
        self.export_csv_btn.setText(T.get("table.export_csv"))
        self.export_json_btn.setText(T.get("table.export_json"))
        self._set_table_headers()
        self.refresh_table()

    def refresh_table(self):
        city = self.city_combo.currentData() or ""
        region = self.region_combo.currentData() or ""
        status = self.status_combo.currentData() or ""
        search_text = self.search_input.text().strip()

        filters = {
            "city": city,
            "region": region,
            "status": status,
            "search": search_text
        }

        pastures = self.db.get_all_pastures(filters)
        self._current_rows = pastures  # dışa aktarma filtrelenmiş veriyi kullanır
        self.table.setSortingEnabled(False)  # doldurma sırasında sıralamayı kapat
        self.table.setRowCount(len(pastures))

        total_area = 0.0
        for row_idx, p in enumerate(pastures):
            total_area += float(p["area_hectares"] or 0)
            self.table.setItem(row_idx, 0, NumericItem(int(p["id"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(p["code"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(p["name"]))
            self.table.setItem(row_idx, 3, QTableWidgetItem(p["city"]))
            self.table.setItem(row_idx, 4, QTableWidgetItem(p["district"]))
            self.table.setItem(row_idx, 5, QTableWidgetItem(p["region"]))
            self.table.setItem(row_idx, 6, NumericItem(float(p["area_hectares"] or 0), f"{p['area_hectares']:,.0f}"))
            self.table.setItem(row_idx, 7, NumericItem(int(p["elevation_m"] or 0), f"{p['elevation_m']} m"))
            self.table.setItem(row_idx, 8, NumericItem(int(p["bbhb_capacity"] or 0), f"{p['bbhb_capacity']:,}"))
            self.table.setItem(row_idx, 9, NumericItem(int(p["kbhb_capacity"] or 0), f"{p['kbhb_capacity']:,}"))
            self.table.setItem(row_idx, 10, NumericItem(float(p["dry_hay_yield_kg_per_ha"] or 0), f"{p['dry_hay_yield_kg_per_ha']:,}"))

            status_item = QTableWidgetItem(p["status"])
            # Beyaz/çok açık zeminde okunabilirlik: sarı yerine koyu kehribar,
            # kırmızı yerine daha koyu ton kullanılır.
            if "Aktif" in p["status"]:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif "Dinlendir" in p["status"]:
                status_item.setForeground(QColor("#B45309"))
            else:
                status_item.setForeground(QColor("#B91C1C"))
            self.table.setItem(row_idx, 11, status_item)

        self.count_label.setText(T.get("table.count_fmt", n=len(pastures)))
        self.area_label.setText(T.get("table.area_fmt", n=total_area))
        self.table.setSortingEnabled(True)

    def _on_row_double_clicked(self, index):
        row = index.row()
        pasture_id_item = self.table.item(row, 0)
        if pasture_id_item:
            pasture_id = int(pasture_id_item.text())
            pasture = self.db.get_pasture_by_id(pasture_id)
            if pasture:
                self.pastureSelected.emit(pasture)

    def _export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, T.get("table.dlg_csv"), "turkiye_81_il_mera_listesi.csv", "CSV Files (*.csv)"
        )
        if file_path:
            if self._export_filtered(file_path, "csv"):
                QMessageBox.information(
                    self, T.get("table.msg_success"),
                    T.get("table.msg_exported", path=file_path)
                )
            else:
                QMessageBox.warning(
                    self, T.get("msg.error_title"), T.get("table.msg_no_data")
                )

    def _export_json(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, T.get("table.dlg_json"), "turkiye_81_il_mera_listesi.json", "JSON Files (*.json)"
        )
        if file_path:
            if self._export_filtered(file_path, "json"):
                QMessageBox.information(
                    self, T.get("table.msg_success"),
                    T.get("table.msg_exported", path=file_path)
                )
            else:
                QMessageBox.warning(
                    self, T.get("msg.error_title"), T.get("table.msg_no_data")
                )

    def _export_filtered(self, file_path, fmt):
        """Dışa aktarmayı ekrandaki filtrelenmiş veriyle sınırlar (beklenen davranış)."""
        import csv as _csv
        import json as _json
        rows = getattr(self, "_current_rows", None)
        if rows is None:
            rows = self.db.get_all_pastures()
        if not rows:
            return False
        if fmt == "csv":
            headers = rows[0].keys()
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = _csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                _json.dump(rows, f, ensure_ascii=False, indent=2)
        return True
