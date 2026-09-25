"""
Vejetasyon Ölçüm ve Gözlem Kayıtları modülü.

Veri girişi tek doğruluk kaynağı olan MeasurementDialog üzerinden yapılır:
"➕ Ekle" her zaman boş form, "✏️ Düzenle" seçili satırı diyaloğa taşır.
Görünüm listeleme + trend grafikleri + CSV dışa aktarma odaklıdır.
"""
import csv
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from i18n import T
from gui.measurement_dialog import MeasurementDialog

LOG = logging.getLogger("merabis.measurements")


class MeasurementsView(QWidget):
    """Mera ölçüm kayıtları: araç çubuğu + liste + trend grafikleri + CSV."""

    measurementSaved = pyqtSignal(int)  # pasture_id

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_pasture = None
        self._init_ui()
        self.refresh_pastures()

    # ---------------------------------------------------------------- UI
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        self.title_label = QLabel(T.get("meas.title"))
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #558B2F;")
        main_layout.addWidget(self.title_label)

        self.desc_label = QLabel(T.get("meas.desc"))
        main_layout.addWidget(self.desc_label)

        # ---- Üst: mera seçimi + eylem düğmeleri ----
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.pasture_combo = QComboBox()
        self.pasture_combo.currentIndexChanged.connect(self._on_pasture_changed)
        self.pasture_combo.setMinimumWidth(300)
        top_row.addWidget(self.pasture_combo, stretch=1)

        self.add_btn = QPushButton(T.get("meas.btn_add"))
        self.add_btn.setStyleSheet(
            "QPushButton { background-color:#7CB342; color:#FFF; font-weight:bold;"
            " border-radius:8px; padding:9px 18px; }"
            " QPushButton:hover { background-color:#9CCC65; }")
        self.add_btn.clicked.connect(self._add_via_dialog)

        self.edit_btn = QPushButton(T.get("meas.btn_edit"))
        self.edit_btn.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#3D5245; border:1px solid #C6DBC1;"
            " border-radius:8px; padding:9px 16px; }"
            " QPushButton:hover { border-color:#7CB342; color:#558B2F; }")
        self.edit_btn.clicked.connect(self._edit_via_dialog)
        self.edit_btn.setEnabled(False)

        self.delete_btn = QPushButton(T.get("meas.btn_delete"))
        self.delete_btn.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#C62828; border:1px solid #EF9A9A;"
            " border-radius:8px; padding:9px 14px; }"
            " QPushButton:hover { background:#E53935; color:#FFF; }")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setEnabled(False)

        top_row.addWidget(self.add_btn)
        top_row.addWidget(self.edit_btn)
        top_row.addWidget(self.delete_btn)
        main_layout.addLayout(top_row)

        # ---- Liste üstü satır ----
        list_row = QHBoxLayout()
        self.export_btn = QPushButton(T.get("meas.btn_export"))
        self.export_btn.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#3D5245; border:1px solid #C6DBC1;"
            " border-radius:6px; padding:8px 14px; }"
            " QPushButton:hover { border-color:#7CB342; color:#558B2F; }")
        self.export_btn.clicked.connect(self.export_csv)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #5C7164; font-weight: bold;")
        list_row.addWidget(self.count_label)
        list_row.addStretch()
        list_row.addWidget(self.export_btn)
        main_layout.addLayout(list_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([T.get(k) for k in (
            "meas.h_date", "meas.h_yield", "meas.h_cover", "meas.h_height",
            "meas.h_plants", "meas.h_observer", "meas.h_method")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.setMinimumHeight(200)
        main_layout.addWidget(self.table, stretch=1)

        # Trend grafikleri (verim + örtü)
        self.fig = Figure(figsize=(6, 2.8), facecolor='#FFFFFF')
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(200)
        main_layout.addWidget(self.canvas)

    # ---------------------------------------------------------------- veri
    def refresh_pastures(self, keep=None):
        """Mera açılır listesini tazeler; keep=id seçimi korur."""
        keep_id = keep if keep is not None else (
            self.current_pasture["id"] if self.current_pasture else None)
        pastures = self.db.get_all_pastures()
        self.pasture_combo.blockSignals(True)
        self.pasture_combo.clear()
        for p in pastures:
            self.pasture_combo.addItem(f"{p['code']} - {p['name']} ({p['city']})", p["id"])
        self.pasture_combo.blockSignals(False)
        if keep_id is not None:
            idx = self.pasture_combo.findData(keep_id)
            if idx >= 0:
                self.pasture_combo.setCurrentIndex(idx)
                return
        self._on_pasture_changed()

    def _on_pasture_changed(self):
        pid = self.pasture_combo.currentData()
        self.current_pasture = self.db.get_pasture_by_id(pid) if pid is not None else None
        self.refresh_table()
        self.refresh_chart()

    def _editing_row(self):
        """Seçili satırın ölçüm id'si (düzenleme/silme için) veya None."""
        sel = self.table.selectionModel()
        if sel is None or not sel.hasSelection():
            return None
        row = self.table.selectionModel().selectedRows()[0].row()
        item = self.table.item(row, 0)
        return int(item.data(32)) if item and item.data(32) is not None else None

    def refresh_table(self):
        rows = []
        if self.current_pasture:
            rows = self.db.get_measurements(self.current_pasture["id"], order="DESC")
        self.table.setRowCount(len(rows))
        for r, m in enumerate(rows):
            date_item = QTableWidgetItem(m["m_date"])
            date_item.setData(32, m["id"])  # UserRole: satırın ölçüm id'si
            self.table.setItem(r, 0, date_item)
            self.table.setItem(r, 1, QTableWidgetItem(
                f"{m['dry_hay_yield_kg_per_ha'] or 0:,.1f}"))
            self.table.setItem(r, 2, QTableWidgetItem(
                f"%{m['vegetation_coverage_pct'] or 0:g}"))
            self.table.setItem(r, 3, QTableWidgetItem(
                f"{m['avg_height_cm'] or 0:g} cm"))
            self.table.setItem(r, 4, QTableWidgetItem(m.get("dominant_plants") or "-"))
            self.table.setItem(r, 5, QTableWidgetItem(m.get("observer") or "-"))
            self.table.setItem(r, 6, QTableWidgetItem(m.get("method") or "-"))
            # Örtü yüzdesine göre renk tonu (hızlı görsel okuma)
            cov = m["vegetation_coverage_pct"] or 0
            if cov >= 70:
                color = QColor("#E7F1E2")
            elif cov >= 40:
                color = QColor("#FFF7E0")
            else:
                color = QColor("#FDECEA")
            for c in range(7):
                it = self.table.item(r, c)
                if it:
                    it.setBackground(color)
        self.count_label.setText(T.get("meas.count_fmt", n=len(rows)))
        self.delete_btn.setEnabled(bool(rows))
        self.edit_btn.setEnabled(self._editing_row() is not None)

    def refresh_chart(self):
        """Seçili meranın verim + örtü trend grafiğini çizer."""
        self.fig.clear()
        ax1 = self.fig.add_subplot(111)
        rows = []
        if self.current_pasture:
            rows = self.db.get_measurements(self.current_pasture["id"], order="ASC")
        dates = [m["m_date"] for m in rows]
        yields = [m["dry_hay_yield_kg_per_ha"] or 0 for m in rows]
        covers = [m["vegetation_coverage_pct"] or 0 for m in rows]
        ax1.plot(dates, yields, marker="o", color="#7CB342", label=T.get("meas.chart_yield"))
        ax1.set_ylabel(T.get("meas.chart_yield"), color="#558B2F")
        ax1.tick_params(axis="x", rotation=30, labelsize=7)
        if rows:
            ax2 = ax1.twinx()
            ax2.plot(dates, covers, marker="s", color="#F59E0B",
                     label=T.get("meas.chart_cover"))
            ax2.set_ylabel(T.get("meas.chart_cover"), color="#B45309")
            ax2.set_ylim(0, 100)
        ax1.set_title(
            T.get("meas.chart_title",
                  name=self.current_pasture["name"] if self.current_pasture else "-"),
            color="#558B2F", fontsize=10, fontweight="bold")
        self.fig.tight_layout()
        self.canvas.draw()

    # ---------------------------------------------------------------- işlemler
    def _on_row_selected(self):
        """Satır seçilince düzenle düğmesini günceller."""
        self.edit_btn.setEnabled(self._editing_row() is not None)

    def _add_via_dialog(self):
        """➕ Ekle: seçili mera için boş diyalo açar (kaynak 'form')."""
        if not self.current_pasture:
            QMessageBox.warning(self, T.get("meas.msg_title"),
                                T.get("meas.warn_no_pasture"))
            return
        dialog = MeasurementDialog(self, self.db, self.current_pasture["id"],
                                   source="form")
        dialog.exec()
        if dialog.result() == MeasurementDialog.DialogCode.Accepted:
            self.refresh_table()
            self.refresh_chart()
            self.measurementSaved.emit(self.current_pasture["id"])

    def _edit_via_dialog(self):
        """✏️ Düzenle: seçili satırı diyaloğa taşır (kaynak 'form')."""
        mid = self._editing_row()
        if mid is None or not self.current_pasture:
            return
        dialog = MeasurementDialog(self, self.db, self.current_pasture["id"],
                                   measurement_id=mid, source="form")
        dialog.exec()
        if dialog.result() == MeasurementDialog.DialogCode.Accepted:
            self.refresh_table()
            self.refresh_chart()
            self.measurementSaved.emit(self.current_pasture["id"])

    def delete_selected(self):
        mid = self._editing_row()
        if mid is None:
            return
        reply = QMessageBox.question(
            self, T.get("meas.delete_title"), T.get("meas.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_measurement(mid)
        except Exception as exc:
            QMessageBox.critical(self, T.get("meas.msg_title"),
                                 T.get("meas.delete_fail", exc=exc))
            return
        self.refresh_table()
        self.refresh_chart()

    def export_csv(self):
        """Tüm ölçümleri mera koduyla birleştirip CSV olarak kaydeder."""
        rows = self.db.measurements_export_rows()
        if not rows:
            QMessageBox.warning(self, T.get("meas.msg_title"), T.get("meas.no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, T.get("meas.dlg_export"), "vejetasyon_olcumleri.csv", "CSV (*.csv)")
        if not path:
            return
        headers = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        QMessageBox.information(self, T.get("meas.msg_title"),
                                T.get("meas.export_ok", path=path))

    # ---------------------------------------------------------------- dil
    def retranslate(self):
        self.title_label.setText(T.get("meas.title"))
        self.desc_label.setText(T.get("meas.desc"))
        self.add_btn.setText(T.get("meas.btn_add"))
        self.edit_btn.setText(T.get("meas.btn_edit"))
        self.delete_btn.setText(T.get("meas.btn_delete"))
        self.export_btn.setText(T.get("meas.btn_export"))
        self.table.setHorizontalHeaderLabels([T.get(k) for k in (
            "meas.h_date", "meas.h_yield", "meas.h_cover", "meas.h_height",
            "meas.h_plants", "meas.h_observer", "meas.h_method")])
        self.refresh_table()
        self.refresh_chart()
