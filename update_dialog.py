"""
Güncelleme diyaloğu — yeni sürüm bildirimi, indirme/yükleme ve yeniden başlatma.

Kaynak modda yükleme devre dışıdır (yalnızca bilgilendirme); paketli derlemede
paket doğrulanır, uygulama yedeklenir ve güncelleme uygulanır.
"""
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QFileDialog, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core import update_checker as uc
from i18n import T


class ApplyUpdateWorker(QThread):
    """Güncelleme işlemini arka planda yürütür (arayüz donmasın diye)."""
    progress = pyqtSignal(str, int)   # stage, pct
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, package_path, manifest, db_manager=None, parent=None):
        super().__init__(parent)
        self.package_path = package_path
        self.manifest = manifest
        self.db_manager = db_manager

    def run(self):
        try:
            result = uc.apply_update(
                self.package_path,
                expected_sha256=self.manifest.get("sha256", ""),
                expected_size=self.manifest.get("size", 0),
                progress_cb=lambda stage, pct: self.progress.emit(stage, pct),
                db_manager=self.db_manager,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # yükleme hataları kullanıcıya bildirilir
            self.failed.emit(str(exc))


class UpdateDialog(QDialog):
    """Sürüm denetimi + yükleme diyaloğu."""

    STAGE_KEYS = {"verify": "upd.stage_verify", "backup": "upd.stage_backup", "apply": "upd.stage_apply"}

    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db = db_manager
        self.result_info = None      # check_for_updates çıktısı
        self.worker = None
        self._init_ui()
        self.retranslate()
        self._run_check()

    # ---- UI ----
    def _init_ui(self):
        self.setMinimumSize(560, 380)
        self.setStyleSheet("""
            QDialog { background-color: #EDF4EA; color: #23332A; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title = QLabel("")
        self.title.setStyleSheet("font-size: 18px; font-weight: bold; color: #558B2F;")
        layout.addWidget(self.title)

        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: #5C7164; font-size: 12px;")
        layout.addWidget(self.desc)

        # Bilgi kartı
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: 1px solid #C6DBC1; border-radius: 10px; }
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(6)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #23332A;")
        card_lay.addWidget(self.status_label)

        self.notes_label = QLabel("")
        self.notes_label.setWordWrap(True)
        self.notes_label.setStyleSheet("color: #3D5245; font-size: 12px;")
        card_lay.addWidget(self.notes_label)

        layout.addWidget(card)

        # Kaynak satırı
        src_row = QHBoxLayout()
        self.src_input = QLineEdit()
        self.src_input.setPlaceholderText(T.get("upd.source_placeholder"))
        self.src_pick_btn = QPushButton(T.get("upd.btn_browse"))
        self.src_pick_btn.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#3D5245; border:1px solid #C6DBC1;"
            " border-radius:6px; padding:7px 12px; }"
            "QPushButton:hover { border-color:#7CB342; color:#558B2F; }")
        self.src_pick_btn.clicked.connect(self._pick_source)
        src_row.addWidget(QLabel(T.get("upd.source_label")))
        src_row.addWidget(self.src_input, stretch=1)
        src_row.addWidget(self.src_pick_btn)
        layout.addLayout(src_row)

        # İlerleme çubuğu
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #C6DBC1; border-radius: 6px; text-align: center;
                           background: #FBFDFA; height: 20px; color: #23332A; }
            QProgressBar::chunk { background-color: #7CB342; border-radius: 5px; }
        """)
        self.stage_label = QLabel("")
        self.stage_label.setStyleSheet("color: #5C7164; font-size: 11px;")
        layout.addWidget(self.stage_label)
        layout.addWidget(self.progress)

        # Butonlar
        btn_row = QHBoxLayout()
        self.check_btn = QPushButton(T.get("upd.btn_check"))
        self.check_btn.setStyleSheet(
            "QPushButton { background-color:#7CB342; color:#FFF; font-weight:bold;"
            " border-radius:8px; padding:10px 18px; } QPushButton:hover { background-color:#9CCC65; }")
        self.check_btn.clicked.connect(self._run_check)

        self.install_btn = QPushButton(T.get("upd.btn_install"))
        self.install_btn.setEnabled(False)
        self.install_btn.setStyleSheet(
            "QPushButton { background-color:#689F38; color:#FFF; font-weight:bold;"
            " border-radius:8px; padding:10px 18px; } QPushButton:hover { background-color:#7CB342; }"
            "QPushButton:disabled { background-color:#C6DBC1; color:#8A9D8E; }")
        self.install_btn.clicked.connect(self._on_install)

        self.rollback_btn = QPushButton(T.get("upd.btn_rollback"))
        self.rollback_btn.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#C62828; border:1px solid #EF9A9A;"
            " border-radius:8px; padding:10px 14px; } QPushButton:hover { background:#E53935; color:#FFF; }")
        self.rollback_btn.clicked.connect(self._on_rollback)

        self.close_btn = QPushButton(T.get("upd.btn_close"))
        self.close_btn.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#3D5245; border:1px solid #C6DBC1;"
            " border-radius:8px; padding:10px 18px; } QPushButton:hover { border-color:#7CB342; color:#558B2F; }")
        self.close_btn.clicked.connect(self.reject)

        btn_row.addWidget(self.check_btn)
        btn_row.addWidget(self.install_btn)
        btn_row.addWidget(self.rollback_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

    def retranslate(self):
        self.setWindowTitle(T.get("upd.title"))
        self.title.setText(T.get("upd.title"))
        self.desc.setText(T.get("upd.desc"))
        self.check_btn.setText(T.get("upd.btn_check"))
        self.install_btn.setText(T.get("upd.btn_install"))
        self.rollback_btn.setText(T.get("upd.btn_rollback"))
        self.close_btn.setText(T.get("upd.btn_close"))
        self.src_pick_btn.setText(T.get("upd.btn_browse"))

    # ---- Kaynak seçimi ----
    def _pick_source(self):
        path = QFileDialog.getExistingDirectory(self, T.get("upd.source_pick_title"), self.src_input.text())
        if path:
            self.src_input.setText(path)
            uc.set_local_source(path)
            self._run_check()

    # ---- Denetim ----
    def _run_check(self):
        self.progress.setValue(0)
        self.stage_label.setText("")
        self.install_btn.setEnabled(False)
        self.status_label.setText(T.get("upd.checking"))
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #3D5245;")
        self.notes_label.setText("")

        source = self.src_input.text().strip()
        if source:
            uc.set_local_source(source)
        else:
            self.src_input.setText(uc.get_local_source())

        info = uc.check_for_updates()
        self.result_info = info
        status = info.get("status")

        if status == "update_available":
            m = info["manifest"]
            self.status_label.setText(T.get(
                "upd.available", v=m["version"], cur=uc.read_version_safe()))
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #558B2F;")
            notes = m.get("notes") or ""
            date_txt = f" • {m['date']}" if m.get("date") else ""
            self.notes_label.setText((notes + date_txt).strip())
            self.install_btn.setEnabled(uc.is_frozen())
            if not uc.is_frozen():
                self.notes_label.setText(
                    self.notes_label.text() + "\n" + T.get("upd.source_mode_hint"))
        elif status == "up_to_date":
            self.status_label.setText(T.get("upd.up_to_date"))
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #558B2F;")
        else:
            self.status_label.setText(T.get("upd.no_source"))
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #B45309;")

    # ---- Yükleme ----
    def _on_install(self):
        if not (self.result_info and self.result_info.get("status") == "update_available"):
            return
        if not uc.is_frozen():
            QMessageBox.information(self, T.get("upd.title"), T.get("upd.source_mode_hint"))
            return
        reply = QMessageBox.question(
            self, T.get("upd.confirm_title"), T.get("upd.confirm_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        pkg = self.result_info["package_path"]
        manifest = self.result_info["manifest"]
        self.check_btn.setEnabled(False)
        self.install_btn.setEnabled(False)

        self.worker = ApplyUpdateWorker(pkg, manifest, db_manager=self.db, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_install_ok)
        self.worker.failed.connect(self._on_install_fail)
        self.worker.start()

    def _on_progress(self, stage, pct):
        self.stage_label.setText(T.get(self.STAGE_KEYS.get(stage, "upd.stage_apply")))
        self.progress.setValue(pct)

    def _on_install_ok(self, result):
        self.progress.setValue(100)
        self.stage_label.setText("")
        m = self.result_info["manifest"]
        QMessageBox.information(self, T.get("upd.title"), T.get(
            "upd.install_done", v=result.get("installed_version") or m.get("version", "")))
        uc.launch_restarter()
        self.parentWidget().close()  # restarter yeni sürümü başlatır

    def _on_install_fail(self, message):
        self.check_btn.setEnabled(True)
        self.install_btn.setEnabled(True)
        QMessageBox.critical(self, T.get("upd.title"), T.get("upd.install_fail", exc=message))

    # ---- Geri alma ----
    def _on_rollback(self):
        reply = QMessageBox.question(
            self, T.get("upd.rollback_title"), T.get("upd.rollback_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            n = uc.rollback_last_update()
            QMessageBox.information(self, T.get("upd.title"), T.get("upd.rollback_done", n=n))
        except Exception as exc:
            QMessageBox.critical(self, T.get("upd.title"), T.get("upd.install_fail", exc=exc))
