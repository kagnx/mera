"""
Veri Denetimi ve Tutarlılık ekranı.

DatabaseManager.audit_consistency() raporunu ve kural göçü bilgisini gösterir;
normalleştirilebilir kodları tek tıkla düzelterek kullanıcının sorunları
elle çözmesine olanak tanır (örn. göç raporundaki çakışan kodlar).

Ölçüm denetim izi bölümü kaynak + tarih aralığı filtresi ve CSV dışa aktarma
içerir (utf-8-sig — Excel uyumlu, ölçüm ekranındaki konvansiyonla aynı).
"""
import csv
import logging
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QDateEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from database.validation import normalize_code
from i18n import T

LOG = logging.getLogger("merabis.audit")

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'assets', filename)

# Sorun türü → kullanıcıya gösterilen öncelik sırası ve renk etiketi
SEVERITY_COLORS = {
    "error": "#DC2626",
    "info": "#3E8E63",
}


class AuditView(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        self.title = QLabel(T.get("audit.title"))
        self.title.setStyleSheet("font-size: 20px; font-weight: bold; color: #558B2F;")
        main_layout.addWidget(self.title)

        self.desc_label = QLabel(T.get("audit.desc"))
        self.desc_label.setStyleSheet("color: #5C7164; font-size: 13px;")
        self.desc_label.setWordWrap(True)
        main_layout.addWidget(self.desc_label)

        # ---- İşlem satırı ----
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.audit_btn = QPushButton(T.get("audit.btn_audit"))
        self.audit_btn.setStyleSheet("""
            QPushButton {
                background-color: #7CB342; color: #FFFFFF; font-weight: bold;
                border-radius: 8px; padding: 10px 20px; font-size: 14px;
            }
            QPushButton:hover { background-color: #9CCC65; }
        """)
        self.audit_btn.clicked.connect(self.refresh)

        self.fix_all_btn = QPushButton(T.get("audit.btn_fix_all"))
        self.fix_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #3D5245;
                border: 1px solid #C6DBC1; border-radius: 8px; padding: 10px 18px;
            }
            QPushButton:hover { border-color: #7CB342; color: #558B2F; }
        """)
        self.fix_all_btn.clicked.connect(self._fix_all_normalizable)

        action_row.addWidget(self.audit_btn)
        action_row.addWidget(self.fix_all_btn)
        action_row.addStretch()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #558B2F; font-weight: bold; font-size: 13px;")
        action_row.addWidget(self.status_label)
        main_layout.addLayout(action_row)

        # ---- Özet kartları ----
        self.summary_layout = QHBoxLayout()
        self.summary_layout.setSpacing(10)
        main_layout.addLayout(self.summary_layout)

        # ---- Göç bilgisi kartı ----
        migration_card = QFrame()
        migration_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #C6DBC1;
                border-radius: 10px; padding: 10px 12px;
            }
        """)
        mig_layout = QVBoxLayout(migration_card)
        mig_layout.setSpacing(4)
        self.mig_title = QLabel(T.get("audit.mig_title"))
        self.mig_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #558B2F;")
        mig_title = self.mig_title
        self.migration_label = QLabel("")
        self.migration_label.setStyleSheet("color: #23332A; font-size: 12px;")
        self.migration_label.setWordWrap(True)
        mig_layout.addWidget(mig_title)
        mig_layout.addWidget(self.migration_label)
        main_layout.addWidget(migration_card)

        # ---- Poligon tutarlılık kartı (kayıtlı alan ↔ geometri sapması) ----
        self.poly_card = QFrame()
        self.poly_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #C6DBC1;
                border-radius: 10px; padding: 10px 12px;
            }
        """)
        poly_lay = QVBoxLayout(self.poly_card)
        poly_lay.setSpacing(4)
        self.poly_title = QLabel(T.get("audit.poly_title"))
        self.poly_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #558B2F;")
        self.poly_summary = QLabel("")
        self.poly_summary.setStyleSheet("color: #23332A; font-size: 12px;")
        self.poly_summary.setWordWrap(True)
        self.poly_detail = QLabel("")
        self.poly_detail.setStyleSheet("color: #5C7164; font-size: 11.5px;")
        self.poly_detail.setWordWrap(True)
        self.poly_detail.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        poly_lay.addWidget(self.poly_title)
        poly_lay.addWidget(self.poly_summary)
        poly_lay.addWidget(self.poly_detail)
        main_layout.addWidget(self.poly_card)

        # ---- Sorunlu kayıtlar tablosu ----
        self.table_title = QLabel(T.get("audit.table_title"))
        self.table_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #5C7164;")
        main_layout.addWidget(self.table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            T.get("audit.h_id"), T.get("audit.h_code"), T.get("audit.h_name"),
            T.get("audit.h_city"), T.get("audit.h_problems"), T.get("audit.h_action"),
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table, stretch=1)

        # ---- Ölçüm denetim izi (son N kayıt + filtre + CSV) ----
        self.log_title = QLabel(T.get("audit.log_title"))
        self.log_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #5C7164;")
        main_layout.addWidget(self.log_title)

        # Filtre satırı: kaynak + tarih aralığı + dışa aktarma
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self.log_source_label = QLabel(T.get("audit.log_source_label"))
        self.log_source_combo = QComboBox()
        for _key, _label in (
            ("audit.log_src_all", T.get("audit.log_src_all")),
            ("audit.log_src_map", T.get("audit.log_src_map")),
            ("audit.log_src_menu", T.get("audit.log_src_menu")),
            ("audit.log_src_form", T.get("audit.log_src_form")),
        ):
            self.log_source_combo.addItem(_label, _key)
        self.log_from_label = QLabel(T.get("audit.log_from"))
        self.log_from_date = QDateEdit()
        self.log_from_date.setCalendarPopup(True)
        self.log_from_date.setDisplayFormat("yyyy-MM-dd")
        self.log_from_date.setDate(QDate.currentDate().addMonths(-1))
        self.log_to_label = QLabel(T.get("audit.log_to"))
        self.log_to_date = QDateEdit()
        self.log_to_date.setCalendarPopup(True)
        self.log_to_date.setDisplayFormat("yyyy-MM-dd")
        self.log_to_date.setDate(QDate.currentDate())
        self.log_export_btn = QPushButton(T.get("audit.log_btn_export"))
        self.log_export_btn.clicked.connect(self._export_log_csv)
        for w in (self.log_source_label, self.log_source_combo,
                  self.log_from_label, self.log_from_date,
                  self.log_to_label, self.log_to_date):
            filter_row.addWidget(w)
        filter_row.addStretch(1)
        filter_row.addWidget(self.log_export_btn)
        main_layout.addLayout(filter_row)
        self.log_source_combo.currentIndexChanged.connect(self._fill_log_table)
        self.log_from_date.dateChanged.connect(self._fill_log_table)
        self.log_to_date.dateChanged.connect(self._fill_log_table)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(5)
        self.log_table.setHorizontalHeaderLabels([
            T.get("audit.log_h_time"), T.get("audit.log_h_action"),
            T.get("audit.log_h_pasture"), T.get("audit.log_h_source"),
            T.get("audit.log_h_changes"),
        ])
        log_header = self.log_table.horizontalHeader()
        log_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        log_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        log_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        log_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        log_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.log_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.log_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.log_table, stretch=1)

    def retranslate(self):
        """Dil değişince statik metinleri ve raporu günceller."""
        self.title.setText(T.get("audit.title"))
        self.desc_label.setText(T.get("audit.desc"))
        self.audit_btn.setText(T.get("audit.btn_audit"))
        self.fix_all_btn.setText(T.get("audit.btn_fix_all"))
        self.mig_title.setText(T.get("audit.mig_title"))
        self.poly_title.setText(T.get("audit.poly_title"))
        self.table_title.setText(T.get("audit.table_title"))
        self.log_title.setText(T.get("audit.log_title"))
        self.log_source_label.setText(T.get("audit.log_source_label"))
        for i in range(self.log_source_combo.count()):
            self.log_source_combo.setItemText(
                i, T.get(self.log_source_combo.itemData(i)))
        self.log_from_label.setText(T.get("audit.log_from"))
        self.log_to_label.setText(T.get("audit.log_to"))
        self.log_export_btn.setText(T.get("audit.log_btn_export"))
        self.log_table.setHorizontalHeaderLabels([
            T.get("audit.log_h_time"), T.get("audit.log_h_action"),
            T.get("audit.log_h_pasture"), T.get("audit.log_h_source"),
            T.get("audit.log_h_changes"),
        ])
        self.table.setHorizontalHeaderLabels([
            T.get("audit.h_id"), T.get("audit.h_code"), T.get("audit.h_name"),
            T.get("audit.h_city"), T.get("audit.h_problems"), T.get("audit.h_action"),
        ])
        self.refresh()

    # ---- Veri / Yenileme ----
    def refresh(self):
        try:
            report = self.db.audit_consistency()
        except Exception as exc:
            self._set_status(T.get("audit.audit_failed", exc=exc), ok=False)
            return
        rule_version = self.db.get_rule_version()
        migration = self.db.get_last_migration_info()

        self._fill_summary(report, rule_version)
        self._fill_migration(migration, rule_version)
        self._fill_polygon_card()
        self._fill_table(report)
        self._fill_log_table()

        if report["with_issues"] == 0:
            self._set_status(
                T.get("audit.status_ok", n=report['total']), ok=True
            )
        else:
            self._set_status(T.get(
                "audit.status_warn",
                n=report['with_issues'],
                e=report['severity']['error'],
                i=report['severity']['info'],
            ), ok=False)

    def _fill_summary(self, report, rule_version):
        self._clear_layout(self.summary_layout)
        cards = [
            (T.get("audit.sum_total"), str(report["total"])),
            (T.get("audit.sum_issues"), str(report["with_issues"])),
            (T.get("audit.sum_ok"), str(report["ok"])),
            (T.get("audit.sum_rule"), str(rule_version)),
        ]
        for title, value in cards:
            self.summary_layout.addWidget(self._create_summary_card(title, value))

    def _fill_migration(self, migration, rule_version):
        if not migration:
            self.migration_label.setText(T.get("audit.mig_none", v=rule_version))
            return
        steps = ", ".join(str(s) for s in migration.get("applied_steps", [])) or "-"
        conflicts = migration.get("conflicts", [])
        conflict_text = ""
        if conflicts:
            ids = ", ".join(str(c.get("id")) for c in conflicts)
            conflict_text = T.get("audit.mig_conflict", ids=ids)
        self.migration_label.setText(T.get(
            "audit.mig_fmt",
            v=rule_version,
            d=migration.get('date', '-'),
            s=steps,
            c=migration.get('changed', 0),
        ) + conflict_text)

    def _fill_polygon_card(self):
        """Poligon–kayıtlı alan uyum kartını doldurur (hata sessizce atlanır)."""
        try:
            ps = self.db.audit_polygon_consistency()
        except Exception as exc:
            LOG.warning("Poligon denetimi alınamadı: %s", exc)
            self.poly_summary.setText("")
            self.poly_detail.setText("")
            return
        devs = ps.get("deviations", [])
        title_color = "#B3541E" if devs else "#558B2F"
        self.poly_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {title_color};")
        self.poly_summary.setText(T.get(
            "audit.poly_fmt",
            c=ps.get("checked", 0),
            ph=ps.get("placeholder", 0),
            mp=ps.get("missing_polygon", 0),
            n=len(devs),
            t=int(ps.get("threshold", 0.25) * 100),
        ))
        if not devs:
            self.poly_detail.setText("")
            self.poly_detail.setStyleSheet("color: #3E8E63; font-size: 11.5px;")
            return
        self.poly_detail.setStyleSheet("color: #B3541E; font-size: 11.5px;")
        lines = []
        for d in devs[:10]:
            if d.get("reason") == "missing_area":
                lines.append(T.get("audit.poly_item_noarea",
                                   code=d.get("code"), c=d.get("calc_ha")))
            else:
                lines.append(T.get(
                    "audit.poly_item",
                    code=d.get("code"),
                    pct=d.get("deviation_pct"),
                    c=d.get("calc_ha"), r=d.get("recorded_ha"),
                ))
        if len(devs) > 10:
            lines.append(T.get("audit.poly_more", n=len(devs) - 10))
        self.poly_detail.setText("\n".join(lines))

    def _log_filters(self):
        """Filtre widget'larından get_measurement_audit_log parametrelerini üretir."""
        source_key = self.log_source_combo.currentData()
        source = {"audit.log_src_map": "map",
                  "audit.log_src_menu": "menu",
                  "audit.log_src_form": "form"}.get(source_key)
        return {
            "source": source,
            "date_from": self.log_from_date.date().toString("yyyy-MM-dd"),
            "date_to": self.log_to_date.date().toString("yyyy-MM-dd"),
        }

    def _fill_log_table(self):
        """Ölçüm denetim izini filtrelerle tabloya doldurur (hata sessizce atlanır)."""
        try:
            f = self._log_filters()
            entries = self.db.get_measurement_audit_log(
                limit=50, source=f["source"],
                date_from=f["date_from"], date_to=f["date_to"])
        except Exception as exc:
            LOG.warning("Denetim izi okunamadı: %s", exc)
            self.log_table.setRowCount(0)
            return
        action_colors = {"add": "#2F7D46", "update": "#B26A00", "delete": "#C62828"}
        self.log_table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            self.log_table.setItem(row, 0, QTableWidgetItem(str(e.get("timestamp", ""))))
            act = QTableWidgetItem(str(e.get("action", "")))
            act.setForeground(QColor(action_colors.get(e.get("action"), "#5C7164")))
            self.log_table.setItem(row, 1, act)
            self.log_table.setItem(
                row, 2,
                QTableWidgetItem(f"{e.get('pasture_code', '')} — {e.get('pasture_name', '')}"))
            self.log_table.setItem(
                row, 3, QTableWidgetItem(str(e.get("source", ""))))
            changes = e.get("changed_fields") or []
            ch = QTableWidgetItem("; ".join(changes) if changes else "—")
            if changes:
                ch.setToolTip("\n".join(changes))
            self.log_table.setItem(row, 4, ch)

    def _export_log_csv(self):
        """Filtrelenmiş denetim izini CSV olarak kaydeder (utf-8-sig)."""
        try:
            f = self._log_filters()
            rows = self.db.get_measurement_audit_log(
                limit=5000, source=f["source"],
                date_from=f["date_from"], date_to=f["date_to"])
        except Exception as exc:
            LOG.warning("Denetim izi CSV için okunamadı: %s", exc)
            rows = []
        if not rows:
            QMessageBox.warning(self, T.get("audit.msg_title"),
                                T.get("audit.log_no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, T.get("audit.log_dlg_export"),
            "olcum_denetim_izi.csv", "CSV (*.csv)")
        if not path:
            return
        headers = ["timestamp", "action", "pasture_code", "pasture_name",
                   "source", "changed_fields", "measurement_id", "pasture_id"]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerow(headers)
                for e in rows:
                    changes = e.get("changed_fields") or []
                    writer.writerow([
                        e.get("timestamp", ""), e.get("action", ""),
                        e.get("pasture_code", ""), e.get("pasture_name", ""),
                        e.get("source", ""),
                        "; ".join(changes) if changes else "",
                        e.get("measurement_id", ""), e.get("pasture_id", ""),
                    ])
        except OSError as exc:
            QMessageBox.critical(self, T.get("audit.msg_title"),
                                 T.get("audit.log_export_fail", exc=exc))
            return
        QMessageBox.information(self, T.get("audit.msg_title"),
                                T.get("audit.log_export_ok", path=path))

    def _fill_table(self, report):
        issues = report.get("issues", [])
        self.table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            self.table.setItem(row, 0, QTableWidgetItem(str(issue.get("id", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(issue.get("code", "")))
            self.table.setItem(row, 2, QTableWidgetItem(issue.get("name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(issue.get("city", "")))

            problems = issue.get("problems", [])
            lines = []
            for p in problems:
                color = SEVERITY_COLORS.get(p.get("severity"), "#5C7164")
                lines.append(f"<span style='color:{color};'>• {p.get('message', '')}</span>")
            problem_item = QTableWidgetItem()
            problem_item.setText(" | ".join(p.get("message", "") for p in problems))
            problem_item.setToolTip("\n".join(p.get("message", "") for p in problems))
            self.table.setItem(row, 4, problem_item)

            # İşlem sütunu: normalleştirilebilir kod varsa 'Düzelt' butonu
            can_fix = any(p["key"] == "code_normalize" for p in problems)
            if can_fix:
                fix_btn = QPushButton(T.get("audit.btn_fix"))
                fix_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #689F38; color: #FFFFFF; border: none;
                        border-radius: 5px; padding: 5px 12px; font-size: 11px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #7CB342; }
                """)
                fix_btn.clicked.connect(
                    lambda checked=False, pid=issue.get("id"): self._fix_code(pid)
                )
                self.table.setCellWidget(row, 5, fix_btn)
            else:
                self.table.setItem(row, 5, QTableWidgetItem("—"))

    # ---- Düzeltme işlemleri ----
    def _fix_code(self, pasture_id):
        """Tek kaydın kodunu normalleştirir (çakışma varsa atlar)."""
        pasture = self.db.get_pasture_by_id(pasture_id)
        if not pasture:
            QMessageBox.warning(self, T.get("audit.msg_title"), T.get("audit.fix_no_record"))
            self.refresh()
            return
        new_code = normalize_code(pasture.get("code", ""))
        if new_code == pasture.get("code"):
            self.refresh()
            return
        if self.db.code_exists(new_code, exclude_id=pasture_id):
            QMessageBox.warning(
                self, T.get("audit.msg_title"),
                T.get("audit.fix_conflict", code=new_code)
            )
            self.refresh()
            return
        data = dict(pasture)
        data["code"] = new_code
        try:
            self.db.update_pasture(pasture_id, data)
        except Exception as exc:
            QMessageBox.critical(
                self, T.get("audit.msg_title"), T.get("audit.fix_failed", exc=exc)
            )
            return
        self.refresh()

    def _fix_all_normalizable(self):
        report = self.db.audit_consistency()
        fixable = [
            i for i in report.get("issues", [])
            if any(p["key"] == "code_normalize" for p in i.get("problems", []))
        ]
        if not fixable:
            self._set_status(T.get("audit.status_no_fixable"), ok=True)
            return
        fixed = 0
        skipped = 0
        for issue in fixable:
            pasture = self.db.get_pasture_by_id(issue["id"])
            if not pasture:
                continue
            new_code = normalize_code(pasture.get("code", ""))
            if self.db.code_exists(new_code, exclude_id=issue["id"]):
                skipped += 1
                continue
            data = dict(pasture)
            data["code"] = new_code
            try:
                self.db.update_pasture(issue["id"], data)
                fixed += 1
            except Exception:
                skipped += 1
        text = T.get("audit.status_fixed", n=fixed)
        if skipped:
            text += T.get("audit.status_skipped", n=skipped)
        self._set_status(text, ok=True)
        self.refresh()

    # ---- Yardımcılar ----
    def _create_summary_card(self, title, value):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #C6DBC1;
                border-radius: 8px; padding: 8px 14px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet("font-size: 11px; color: #5C7164; font-weight: bold;")
        v = QLabel(value)
        v.setStyleSheet("font-size: 20px; color: #558B2F; font-weight: bold;")
        layout.addWidget(t)
        layout.addWidget(v)
        return card

    def _set_status(self, text, ok=True):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {'#558B2F' if ok else '#DC2626'}; font-weight: bold; font-size: 13px;"
        )

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
