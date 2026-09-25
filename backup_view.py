"""
Veritabanı Yedekleme ve Geri Yükleme yönetim ekranı.

Tek tıkla yedek alır, yedek klasöründeki dosyaları listeler ve
satır başına Geri Yükle / Sil işlemleri sunar.
"""
import os
import sqlite3
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

from i18n import T


class BackupView(QWidget):
    restored = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        self.title = QLabel(T.get("backup.title"))
        self.title.setStyleSheet("font-size: 20px; font-weight: bold; color: #558B2F;")
        main_layout.addWidget(self.title)

        self.desc_label = QLabel(T.get("backup.desc"))
        self.desc_label.setStyleSheet("color: #5C7164; font-size: 13px;")
        self.desc_label.setWordWrap(True)
        main_layout.addWidget(self.desc_label)

        # Bilgi kartı
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #C6DBC1;
                border-radius: 10px; padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(4)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #23332A; font-size: 13px;")
        self.info_label.setWordWrap(True)
        self.backup_dir_label = QLabel("")
        self.backup_dir_label.setStyleSheet("color: #3E8E63; font-size: 12px;")
        self.backup_dir_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        info_layout.addWidget(self.backup_dir_label)
        main_layout.addWidget(info_card)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.backup_btn = QPushButton(T.get("backup.btn_backup"))
        self.backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #7CB342; color: #FFFFFF; font-weight: bold;
                border-radius: 8px; padding: 10px 20px; font-size: 14px;
            }
            QPushButton:hover { background-color: #9CCC65; }
        """)
        self.backup_btn.setToolTip(T.get("backup.backup_tip"))
        self.backup_btn.clicked.connect(self._on_backup_clicked)

        self.restore_btn = QPushButton(T.get("backup.btn_restore_file"))
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #3D5245;
                border: 1px solid #C6DBC1; border-radius: 8px; padding: 10px 18px;
            }
            QPushButton:hover { border-color: #7CB342; color: #558B2F; }
        """)
        self.restore_btn.clicked.connect(self._on_restore_file_clicked)

        self.refresh_btn = QPushButton(T.get("backup.btn_refresh"))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #3D5245;
                border: 1px solid #C6DBC1; border-radius: 8px; padding: 10px 16px;
            }
            QPushButton:hover { border-color: #7CB342; color: #558B2F; }
        """)
        self.refresh_btn.clicked.connect(self.refresh)

        btn_row.addWidget(self.backup_btn)
        btn_row.addWidget(self.restore_btn)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        # Yedek listesi
        self.list_title = QLabel(T.get("backup.list_title"))
        self.list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #5C7164;")
        main_layout.addWidget(self.list_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            T.get("backup.h_name"), T.get("backup.h_size"),
            T.get("backup.h_date"), T.get("backup.h_action"),
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table, stretch=1)

        # Durum satırı
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

    def retranslate(self):
        """Dil değişince statik metinleri ve listeyi günceller."""
        self.title.setText(T.get("backup.title"))
        self.desc_label.setText(T.get("backup.desc"))
        self.backup_btn.setText(T.get("backup.btn_backup"))
        self.backup_btn.setToolTip(T.get("backup.backup_tip"))
        self.restore_btn.setText(T.get("backup.btn_restore_file"))
        self.refresh_btn.setText(T.get("backup.btn_refresh"))
        self.list_title.setText(T.get("backup.list_title"))
        self.table.setHorizontalHeaderLabels([
            T.get("backup.h_name"), T.get("backup.h_size"),
            T.get("backup.h_date"), T.get("backup.h_action"),
        ])
        self.refresh()

    # ---- Veri / Yenileme ----
    def refresh(self):
        info = self.db.get_db_info()
        mtime_str = datetime.fromtimestamp(info["modified"]).strftime("%d.%m.%Y %H:%M:%S")
        self.info_label.setText(T.get(
            "backup.info_fmt",
            path=info['path'],
            count=info['count'],
            size=self._fmt_size(info['size']),
            mtime=mtime_str,
            ver=self.db.get_rule_version(),
        ))
        backup_dir, entries = self.db.list_backups()
        self.backup_dir_label.setText(T.get("backup.dir_fmt", dir=backup_dir))

        self.table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            name_item = QTableWidgetItem(e["name"])
            name_item.setToolTip(e["path"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(self._fmt_size(e["size"])))
            self.table.setItem(row, 2, QTableWidgetItem(
                datetime.fromtimestamp(e["modified"]).strftime("%d.%m.%Y %H:%M:%S")
            ))
            self.table.setCellWidget(row, 3, self._create_action_widget(e["path"]))

    # ---- İşlemler ----
    def _on_backup_clicked(self):
        try:
            # Bakım ön-kontrolü: bekleyen kural göçünü otomatik çalıştır, sürümü doğrula
            check = self.db.pre_backup_check()
            if check["migrated"]:
                self._set_status(T.get("backup.status_migrated"), ok=True)
                self.refresh()
            if not check["ok"]:
                self._set_status(T.get(
                    "backup.status_version_mismatch",
                    expected=check['expected_version'], rule=check['rule_version'],
                ), ok=False)
                return
            backup_dir = self.db.get_backup_dir()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(backup_dir, f"mera_yedek_{stamp}.db")
            self.db.backup_to(path)
            self.refresh()
            self._set_status(
                T.get("backup.status_ok", name=os.path.basename(path)), ok=True
            )
        except Exception as exc:
            self._set_status(T.get("backup.status_fail", exc=exc), ok=False)

    def _on_restore_file_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, T.get("backup.dlg_pick"), self.db.get_backup_dir(),
            "Veritabanı Yedekleri (*.db *.sqlite *.sqlite3)"
        )
        if file_path:
            self._restore(file_path)

    def _restore(self, file_path, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, T.get("backup.confirm_title"),
                T.get("backup.confirm_text", name=os.path.basename(file_path)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            self.db.restore_from(file_path)
            self.refresh()
            self.restored.emit()
            self._set_status(T.get("backup.status_restored"), ok=True)
        except (ValueError, OSError, sqlite3.DatabaseError) as exc:
            self._set_status(T.get("backup.status_restore_fail", exc=exc), ok=False)

    def _delete_backup(self, file_path, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, T.get("backup.delete_confirm_title"),
                T.get("backup.delete_confirm", name=os.path.basename(file_path)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            os.remove(file_path)
            self.refresh()
            self._set_status(
                T.get("backup.status_deleted", name=os.path.basename(file_path)), ok=True
            )
        except OSError as exc:
            self._set_status(T.get("backup.status_delete_fail", exc=exc), ok=False)

    # ---- Yardımcılar ----
    def _create_action_widget(self, path):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        restore_btn = QPushButton(T.get("backup.btn_restore"))
        restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #689F38; color: #FFFFFF; border: none;
                border-radius: 5px; padding: 5px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7CB342; }
        """)
        restore_btn.clicked.connect(lambda checked=False, p=path: self._restore(p))

        del_btn = QPushButton(T.get("backup.btn_delete"))
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #C62828; border: 1px solid #EF9A9A;
                border-radius: 5px; padding: 5px 10px; font-size: 11px;
            }
            QPushButton:hover { background-color: #E53935; color: white; }
        """)
        del_btn.clicked.connect(lambda checked=False, p=path: self._delete_backup(p))

        lay.addWidget(restore_btn)
        lay.addWidget(del_btn)
        return w

    def _set_status(self, text, ok=True):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {'#558B2F' if ok else '#DC2626'}; font-weight: bold; font-size: 13px;"
        )

    @staticmethod
    def _fmt_size(size):
        if size >= 1024 * 1024:
            return f"{size / 1024 / 1024:.1f} MB"
        return f"{size / 1024:.0f} KB"
