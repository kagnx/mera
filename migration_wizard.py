"""
Veritabanı taşıma sihirbazı — eski MERA-BİS PRO kurulumundan veri devralma.

`database/migration.py` servis katmanının üzerine oturan 4 sayfalık QWizard:

  1. Kaynak seçimi  — bilinen konumlar arka planda taranır (radio liste) veya
     elle SQLite dosyası seçilir; bekleyen işaret dosyası varsa ön seçilir
  2. Önizleme       — kaynak özeti + taşıma modu (birleştir / değiştir)
  3. Taşıma         — yedek + WAL-güvenli anlık görüntü + taşıma; ilerleme
     çubuğuyla gösterilir (bağlantı iş parçacığı bağlılığı nedeniyle taşıma
     GUI iş parçacığında koşar; iptal korumalıdır)
  4. Özet           — sonuç raporu (içe aktarılan / atlanan / çakışma / yedek);

Tamamlanınca `refresh_requested` yayılır; ana pencere görünümleri tazeler.
"""
import logging
import os

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QPushButton, QProgressBar, QFrame, QFileDialog, QButtonGroup, QSizePolicy,
)

from database import migration
from i18n import T

LOG = logging.getLogger("merabis.ui.migration")


def _fmt_size(num_bytes):
    """Bayt sayısını insan-okur MB metnine çevirir."""
    try:
        return "{:,.1f} MB".format(num_bytes / (1024 * 1024)).replace(",", ".")
    except (TypeError, ValueError):
        return "?"


class _ScanWorker(QThread):
    """Kaynak taramayı arka planda yürütür (geçersiz dosyalar listelenmez)."""

    scan_done = pyqtSignal(list)
    scan_failed = pyqtSignal(str)

    def __init__(self, exclude_path, parent=None):
        super().__init__(parent)
        self._exclude = exclude_path

    def run(self):
        try:
            results = migration.find_source_databases(exclude_paths=[self._exclude])
            self.scan_done.emit(results)
        except Exception as exc:  # tarama asla sihirbazı düşürmemeli
            LOG.warning("Kaynak taraması başarısız: %s", exc)
            self.scan_failed.emit(str(exc))


class SourcePage(QWizardPage):
    """Sayfa 1: eski veritabanını bul (otomatik tarama veya elle seçim)."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self._db = db_manager
        self._results = []
        self._worker = None
        self._manual_path = ""
        self._marker_source = ""

        self.setTitle(T.get("mig.page.source.title"))
        self.setSubTitle(T.get("mig.page.source.subtitle"))

        lay = QVBoxLayout(self)

        self.lbl_status = QLabel(T.get("mig.page.source.scanning"))
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)

        self.radio_lay = QVBoxLayout()
        self.radio_group = QButtonGroup(self)
        lay.addLayout(self.radio_lay)

        btn_row = QHBoxLayout()
        self.btn_rescan = QPushButton(T.get("mig.page.source.rescan"))
        self.btn_rescan.clicked.connect(self.rescan)
        btn_row.addWidget(self.btn_rescan)
        self.btn_browse = QPushButton(T.get("mig.page.source.browse"))
        self.btn_browse.clicked.connect(self._browse)
        btn_row.addWidget(self.btn_browse)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        self.lbl_hint = QLabel(T.get("mig.page.source.hint"))
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color: #5C7164;")
        lay.addWidget(self.lbl_hint)
        lay.addStretch(1)

        self.registerField("source_index", self, "bogus_property")
        self._refresh_radios()

    # --- seçim durumu ------------------------------------------------------

    def selected_path(self):
        """Seçili kaynak yolu (yoksa '')."""
        for btn in self.radio_group.buttons():
            if btn.isChecked():
                return btn.property("src_path") or ""
        return ""

    def isComplete(self):
        return bool(self.selected_path())

    # --- tarama -------------------------------------------------------------

    def initializePage(self):
        self._marker_source = migration.consume_marker() or ""
        self.rescan()

    def rescan(self):
        """Kaynak taramasını başlatır (var olan taramayı beklemeye almadan)."""
        if self._worker is not None and self._worker.isRunning():
            return
        self.lbl_status.setText(T.get("mig.page.source.scanning"))
        self._refresh_radios()
        self._worker = _ScanWorker(self._db.db_path, self)
        self._worker.scan_done.connect(self._on_scan_done)
        self._worker.scan_failed.connect(self._on_scan_failed)
        self._worker.start()

    def _on_scan_done(self, results):
        self._results = list(results)
        if self._marker_source:
            info = migration.inspect_database(self._marker_source)
            if info.get("valid"):
                if not any(
                    os.path.abspath(r["path"]) == os.path.abspath(self._marker_source)
                    for r in self._results
                ):
                    self._results.insert(0, info)
            else:
                self._marker_source = ""
                migration.clear_marker()
        self._refresh_radios()
        n = len(self._results)
        self.lbl_status.setText(
            T.get("mig.page.source.found", n=n) if n else T.get("mig.page.source.none")
        )

    def _on_scan_failed(self, err):
        self._results = []
        self._refresh_radios()
        self.lbl_status.setText(T.get("mig.page.source.scan_error", err=err))

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, T.get("mig.page.source.browse_title"), os.path.expanduser("~"),
            "SQLite DB (*.db *.sqlite *.sqlite3);;Tüm dosyalar (*.*)",
        )
        if not path:
            return
        info = migration.inspect_database(path)
        if not info.get("valid"):
            self.lbl_status.setText(
                T.get("mig.msg.invalid_source", err=info.get("error", "?")))
            return
        self._manual_path = path
        if not any(os.path.abspath(r["path"]) == os.path.abspath(path)
                   for r in self._results):
            self._results.insert(0, info)
        self._refresh_radios()
        for btn in self.radio_group.buttons():
            if os.path.abspath(btn.property("src_path") or "") == os.path.abspath(path):
                btn.setChecked(True)
        self.lbl_status.setText(T.get("mig.page.source.found", n=len(self._results)))
        self.completeChanged.emit()

    # --- radio listesi -------------------------------------------------------

    def _refresh_radios(self):
        for btn in self.radio_group.buttons():
            self.radio_group.removeButton(btn)
            btn.setParent(None)
            btn.deleteLater()
        while self.radio_lay.count():
            item = self.radio_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for idx, info in enumerate(self._results):
            if info.get("is_seed_only"):
                text = T.get(
                    "mig.page.source.item_seed",
                    path=info["path"], pastures=info["pastures"])
            else:
                text = T.get(
                    "mig.page.source.item",
                    path=info["path"], pastures=info["pastures"],
                    measurements=info["measurements"], modified=info["modified"],
                    size=_fmt_size(info["size"]),
                )
            rb = QRadioButton(text)
            rb.setProperty("src_path", info["path"])
            rb.setStyleSheet("QRadioButton { spacing: 6px; padding: 3px 0; }")
            self.radio_group.addButton(rb, idx)
            self.radio_lay.addWidget(rb)
            if os.path.abspath(info["path"]) == os.path.abspath(
                    self._manual_path or self._marker_source or ""):
                rb.setChecked(True)
        if not self.radio_group.buttons():
            empty = QLabel(T.get("mig.page.source.none"))
            empty.setStyleSheet("color: #8a8a8a; font-style: italic;")
            self.radio_lay.addWidget(empty)

    def retranslate(self):
        self.setTitle(T.get("mig.page.source.title"))
        self.setSubTitle(T.get("mig.page.source.subtitle"))
        self.btn_rescan.setText(T.get("mig.page.source.rescan"))
        self.btn_browse.setText(T.get("mig.page.source.browse"))
        self.lbl_hint.setText(T.get("mig.page.source.hint"))
        self._refresh_radios()
        n = len(self._results)
        self.lbl_status.setText(
            T.get("mig.page.source.found", n=n) if n else T.get("mig.page.source.none"))


class PreviewPage(QWizardPage):
    """Sayfa 2: kaynak özeti + taşıma modu seçimi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(T.get("mig.page.preview.title"))
        self.setSubTitle(T.get("mig.page.preview.subtitle"))

        lay = QVBoxLayout(self)

        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        box_lay = QVBoxLayout(box)
        self.lbl_summary = QLabel("")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box_lay.addWidget(self.lbl_summary)
        lay.addWidget(box)

        self.lbl_mode = QLabel(T.get("mig.page.preview.mode_lbl"))
        lay.addWidget(self.lbl_mode)

        self.rb_merge = QRadioButton(T.get("mig.page.preview.mode_merge"))
        self.rb_merge.setChecked(True)
        lay.addWidget(self.rb_merge)
        note = QLabel(T.get("mig.page.preview.mode_merge_note"))
        note.setWordWrap(True)
        note.setStyleSheet("color: #5C7164; margin-left: 22px;")
        lay.addWidget(note)

        self.rb_replace = QRadioButton(T.get("mig.page.preview.mode_replace"))
        lay.addWidget(self.rb_replace)
        note2 = QLabel(T.get("mig.page.preview.mode_replace_note"))
        note2.setWordWrap(True)
        note2.setStyleSheet("color: #5C7164; margin-left: 22px;")
        lay.addWidget(note2)

        self.lbl_warn = QLabel(T.get("mig.page.preview.warn_replace"))
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.setStyleSheet("color: #b3661a;")
        lay.addWidget(self.lbl_warn)
        lay.addStretch(1)

        for rb in (self.rb_merge, self.rb_replace):
            rb.toggled.connect(self.completeChanged)

    def isComplete(self):
        return self._source_valid()

    def _source_valid(self):
        info = self.wizard().source_info()
        return bool(info and info.get("valid"))

    def initializePage(self):
        self.rb_merge.setChecked(True)
        self._refresh_summary()

    def _refresh_summary(self):
        info = self.wizard().source_info()
        if not info:
            self.lbl_summary.setText(T.get("mig.page.preview.src_none"))
        elif not info.get("valid"):
            self.lbl_summary.setText(
                T.get("mig.page.preview.src_invalid", err=info.get("error", "?")))
        else:
            self.lbl_summary.setText(T.get(
                "mig.page.preview.src_summary",
                path=info["path"], pastures=info["pastures"],
                measurements=info["measurements"], modified=info["modified"],
                size=_fmt_size(info["size"]),
            ))

    def retranslate(self):
        self.setTitle(T.get("mig.page.preview.title"))
        self.setSubTitle(T.get("mig.page.preview.subtitle"))
        self.lbl_mode.setText(T.get("mig.page.preview.mode_lbl"))
        self.rb_merge.setText(T.get("mig.page.preview.mode_merge"))
        self.rb_replace.setText(T.get("mig.page.preview.mode_replace"))
        self.lbl_warn.setText(T.get("mig.page.preview.warn_replace"))
        self._refresh_summary()


class ProgressPage(QWizardPage):
    """Sayfa 3: taşımayı yürütür (yedek + anlık görüntü + aktarım)."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self._db = db_manager
        self._report = None
        self._error = ""
        self._finished = False
        self.setCommitPage(True)
        self.setTitle(T.get("mig.page.progress.title"))
        self.setSubTitle(T.get("mig.page.progress.subtitle"))

        lay = QVBoxLayout(self)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)  # belirsiz ilerleme (taşıma adımları atomiktir)
        self.bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay.addWidget(self.bar)
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)
        lay.addStretch(1)

    def isComplete(self):
        return self._finished and self._report is not None

    def nextId(self):
        return 3 if (self._finished and self._report is not None) else -1

    def initializePage(self):
        self._report = None
        self._error = ""
        self._finished = False
        self.bar.setRange(0, 0)
        self.lbl_status.setText(T.get("mig.page.progress.running"))
        wiz = self.wizard()
        wiz.button(QWizard.WizardButton.BackButton).setEnabled(False)
        wiz.button(QWizard.WizardButton.CancelButton).setEnabled(False)
        # Taşıma GUI iş parçacığında koşar (hedef DB bağlantısı ana iş parçacığına
        # bağlı); kısa bir gecikme ilerleme çubuğunun boyanmasını sağlar.
        QTimer.singleShot(120, self._run_migration)

    def _run_migration(self):
        source = self.wizard().source_path()
        try:
            self._report = migration.migrate(
                self._db, source, mode=self.wizard().mode(), make_backup=True)
            self._error = ""
            LOG.info("Taşıma sihirbazı tamamlandı: +%d mera",
                     self._report.get("imported", 0))
        except Exception as exc:
            self._report = None
            self._error = str(exc)
            LOG.warning("Taşıma sihirbazı başarısız: %s", exc)
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        if self._report is not None:
            self._finished = True
            self.lbl_status.setText(T.get("mig.page.progress.done"))
        else:
            self.lbl_status.setText(
                T.get("mig.page.progress.failed", err=self._error))
        wiz = self.wizard()
        wiz.button(QWizard.WizardButton.BackButton).setEnabled(True)
        wiz.button(QWizard.WizardButton.CancelButton).setEnabled(True)
        self.completeChanged.emit()

    def retranslate(self):
        self.setTitle(T.get("mig.page.progress.title"))
        self.setSubTitle(T.get("mig.page.progress.subtitle"))


class SummaryPage(QWizardPage):
    """Sayfa 4: sonuç raporu; tamamlanınca işaret dosyası temizlenir."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)
        self.setTitle(T.get("mig.page.summary.title"))
        self.setSubTitle(T.get("mig.page.summary.subtitle"))
        lay = QVBoxLayout(self)
        self.lbl_result = QLabel("")
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lbl_result)
        lay.addStretch(1)

    def initializePage(self):
        report = self.wizard().report()
        if report is not None:
            migration.clear_marker()
            self.lbl_result.setText(T.get(
                "mig.page.summary.text",
                mode=report.get("mode", ""),
                imported=report.get("imported", 0),
                skipped_identical=report.get("skipped_identical", 0),
                conflicts_renamed=report.get("conflicts_renamed", 0),
                imported_measurements=report.get("imported_measurements", 0),
                skipped_measurements=report.get("skipped_measurements", 0),
                pastures_after=report.get("pastures_after", 0),
                measurements_after=report.get("measurements_after", 0),
                backup=report.get("backup") or "-",
            ))
        else:
            self.lbl_result.setText(T.get("mig.page.summary.nochanges"))

    def retranslate(self):
        self.setTitle(T.get("mig.page.summary.title"))
        self.setSubTitle(T.get("mig.page.summary.subtitle"))


class MigrationWizard(QWizard):
    """Eski kurulumdan veri devralma sihirbazı (kaynak → önizleme → taşıma → özet)."""

    refresh_requested = pyqtSignal()

    def __init__(self, db_manager, parent=None, preselect=None):
        super().__init__(parent)
        self._db = db_manager
        self._preselect = preselect or ""
        self._report = None

        self.setWindowTitle(T.get("mig.wizard.title"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.WizardButton.NextButton, T.get("mig.btn.next"))
        self.setButtonText(QWizard.WizardButton.BackButton, T.get("mig.btn.back"))
        self.setButtonText(QWizard.WizardButton.CancelButton, T.get("mig.btn.cancel"))
        self.setButtonText(QWizard.WizardButton.FinishButton, T.get("mig.btn.finish"))

        self.src_page = SourcePage(db_manager, self)
        self.preview_page = PreviewPage(self)
        self.progress_page = ProgressPage(db_manager, self)
        self.summary_page = SummaryPage(self)
        self.addPage(self.src_page)
        self.addPage(self.preview_page)
        self.addPage(self.progress_page)
        self.addPage(self.summary_page)
        self.resize(680, 520)

    # --- sayfaların kullandığı durum ---------------------------------------

    def source_path(self):
        """Seçilmiş kaynak yolu ('' olabilir)."""
        return self.src_page.selected_path()

    def source_info(self):
        """Seçili kaynağın inceleme bilgisi (yok/özel yol ise None)."""
        path = self.source_path()
        if not path:
            return None
        for info in self.src_page._results:
            if os.path.abspath(info["path"]) == os.path.abspath(path):
                return info
        return None

    def mode(self):
        return "replace" if self.preview_page.rb_replace.isChecked() else "merge"

    def report(self):
        """Taşıma raporu (özet sayfası Next ile gelindiğinde de doludur)."""
        return self.progress_page._report

    def accept(self):
        """Özet sayfası bitirildiğinde: raporu sakla, görünümleri tazele."""
        self._report = self.progress_page._report
        if self._report is not None:
            self.refresh_requested.emit()
        super().accept()

    def retranslate(self):
        self.setWindowTitle(T.get("mig.wizard.title"))
        self.setButtonText(QWizard.WizardButton.NextButton, T.get("mig.btn.next"))
        self.setButtonText(QWizard.WizardButton.BackButton, T.get("mig.btn.back"))
        self.setButtonText(QWizard.WizardButton.CancelButton, T.get("mig.btn.cancel"))
        self.setButtonText(QWizard.WizardButton.FinishButton, T.get("mig.btn.finish"))
        for page in (self.src_page, self.preview_page,
                     self.progress_page, self.summary_page):
            page.retranslate()
