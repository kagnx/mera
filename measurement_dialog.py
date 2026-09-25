"""Ölçüm ekleme/düzenleme diyaloğu.

gui/measurements_view.py içindeki gömülü form ile aynı veri modelini ve
doğrulama mesajlarını paylaşır; harita popup'ındaki "Ölçüm Ekle" düğmesi ve
menü kısayolu bu diyaloğu açar. Kayıttan sonra measurementSaved sinyali
yayımlanır (harita/popup yenilemesi bununla tetiklenir).
"""
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QComboBox, QDateEdit,
    QDoubleSpinBox, QPushButton, QHBoxLayout, QMessageBox,
)
from PyQt6.QtCore import QDate

from i18n import T

LOG = logging.getLogger("merabis.measurements_dialog")

METHODS = ["Kadro (Quadrat)", "Dirsek-height (Merkez hat)", "Tahmini / Gözlemsel", "İHA / Drone"]


class MeasurementDialog(QDialog):
    """Tek mera için ölçüm giriş/düzenleme diyaloğu.

    pasture_id zorunlu; measurement_id verilirse mevcut kayıt düzenlenir.
    exec() Accepted dönerse kayıt yapılmıştır (saved_pasture_id ile mera alınır).
    """

    def __init__(self, parent, db_manager, pasture_id, measurement_id=None,
                 source="form"):
        super().__init__(parent)
        self.db = db_manager
        self.source = source
        self.pasture = db_manager.get_pasture_by_id(pasture_id)
        if self.pasture is None:
            raise ValueError(f"Mera bulunamadı: id={pasture_id}")

        self.setWindowTitle(T.get("meas.group_new"))
        self.setMinimumWidth(430)
        form = QFormLayout(self)

        pasture = self.pasture
        head = QLabel(f"<b>{pasture['code']} — {pasture['name']}</b><br/>"
                      f"{pasture['city']} / {pasture['district']}")
        head.setStyleSheet("font-size: 13px; color: #2F6B33; padding-bottom: 4px;")

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setCalendarPopup(True)

        self.yield_spin = QDoubleSpinBox()
        self.yield_spin.setRange(0.0, 20000.0)
        self.yield_spin.setDecimals(1)
        self.yield_spin.setSuffix(" kg/ha")

        self.cover_spin = QDoubleSpinBox()
        self.cover_spin.setRange(0.0, 100.0)
        self.cover_spin.setDecimals(1)
        self.cover_spin.setSuffix(" %")

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.0, 500.0)
        self.height_spin.setDecimals(1)
        self.height_spin.setSuffix(" cm")

        self.plants_input = QComboBox()
        self.plants_input.setEditable(True)
        self.plants_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.observer_input = QComboBox()
        self.observer_input.setEditable(True)
        self.observer_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.method_combo = QComboBox()
        self.method_combo.addItems(METHODS)

        self.notes_input = QComboBox()
        self.notes_input.setEditable(True)
        self.notes_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        save_btn = QPushButton(T.get("dialog.btn_save"))
        cancel_btn = QPushButton(T.get("dialog.btn_cancel"))
        save_btn.setStyleSheet(
            "QPushButton { background-color:#7CB342; color:#FFF; font-weight:bold;"
            " border-radius:8px; padding:9px 18px; }"
            " QPushButton:hover { background-color:#9CCC65; }")
        cancel_btn.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#5C7164; border:1px solid #CBDEC6;"
            " border-radius:8px; padding:9px 14px; }"
            " QPushButton:hover { background:#EEF4EC; }")

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        form.addRow(head)
        form.addRow(T.get("meas.lbl_date"), self.date_edit)
        form.addRow(T.get("meas.lbl_yield"), self.yield_spin)
        form.addRow(T.get("meas.lbl_cover"), self.cover_spin)
        form.addRow(T.get("meas.lbl_height"), self.height_spin)
        form.addRow(T.get("meas.lbl_plants"), self.plants_input)
        form.addRow(T.get("meas.lbl_observer"), self.observer_input)
        form.addRow(T.get("meas.lbl_method"), self.method_combo)
        form.addRow(T.get("meas.lbl_notes"), self.notes_input)
        form.addRow(buttons)

        # Düzenleme modu: mevcut değerleri doldur
        if measurement_id is not None:
            self._measurement_id = measurement_id
            rows = self.db.get_measurements(pasture_id)
            row = next((r for r in rows if r["id"] == measurement_id), None)
            if row:
                y, m, d = str(row["m_date"]).split("-")
                self.date_edit.setDate(QDate(int(y), int(m), int(d)))
                if row["dry_hay_yield_kg_per_ha"] is not None:
                    self.yield_spin.setValue(float(row["dry_hay_yield_kg_per_ha"]))
                if row["vegetation_coverage_pct"] is not None:
                    self.cover_spin.setValue(float(row["vegetation_coverage_pct"]))
                if row["avg_height_cm"] is not None:
                    self.height_spin.setValue(float(row["avg_height_cm"]))
                self.plants_input.setCurrentText(row["dominant_plants"] or "")
                self.observer_input.setCurrentText(row["observer"] or "")
                if row["method"]:
                    idx = self.method_combo.findText(row["method"])
                    if idx >= 0:
                        self.method_combo.setCurrentIndex(idx)
                self.notes_input.setCurrentText(row["notes"] or "")
        else:
            self._measurement_id = None

        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)

    def _on_save(self):
        data = {
            "pasture_id": self.pasture["id"],
            "m_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "dry_hay_yield_kg_per_ha": self.yield_spin.value(),
            "vegetation_coverage_pct": round(self.cover_spin.value()),
            "avg_height_cm": self.height_spin.value(),
            "dominant_plants": self.plants_input.currentText().strip(),
            "observer": self.observer_input.currentText().strip(),
            "method": self.method_combo.currentText(),
            "notes": self.notes_input.currentText().strip(),
        }
        try:
            if self._measurement_id is not None:
                self.db.update_measurement(self._measurement_id, data,
                                           source=self.source)
            else:
                self.db.add_measurement(data, source=self.source)
        except Exception as exc:
            LOG.exception("Ölçüm kaydedilemedi")
            QMessageBox.critical(self, T.get("meas.msg_title"),
                                 T.get("meas.save_fail", exc=exc))
            return
        self.accept()

    def saved_pasture_id(self):
        """Kayıt sonrası mera id'si (harita yenilemesi için)."""
        return self.pasture["id"]
