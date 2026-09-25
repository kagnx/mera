import os
import sys
import logging
import sqlite3
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QMessageBox, QComboBox, QStatusBar, QMenuBar,
    QInputDialog, QScrollArea
)
from PyQt6.QtGui import QIcon, QPixmap, QAction, QActionGroup, QKeySequence
from PyQt6.QtCore import Qt, QSettings, QTimer

from database.validation import MessageCatalog
from i18n import T

from gui.map_view import MapView
from gui.pasture_detail_panel import PastureDetailPanel
from gui.pasture_table_view import PastureTableView
from gui.analytics_view import AnalyticsView
from gui.calculator_view import CalculatorView
from gui.rotation_view import RotationView
from gui.backup_view import BackupView
from gui.measurements_view import MeasurementsView
from gui.measurement_dialog import MeasurementDialog
from gui.audit_view import AuditView
from gui.pasture_dialog import PastureDialog
from gui.about_dialog import AboutDialog
from gui.update_dialog import UpdateDialog

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'assets', filename)

class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle(T.get("window.title"))
        # Mantıksal minimum boyut: yüksek DPI ölçeklemede (örn. %250) tam HD
        # fiziksel çözünürlük bile mantıksal alanda çok küçük kalır; bu alt
        # sınırın altında kenar çubuğu içeriği ezilir. Kaydırılabilir kenar
        # çubuğuyla birlikte metin kaybolmak yerine erişilebilir kalır.
        self.setMinimumSize(980, 620)
        self.resize(1380, 850)
        self._log = logging.getLogger("merabis.ui")

        icon_path = get_asset_path("app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._init_ui()
        self._init_menubar()
        self._init_statusbar()

    def _init_menubar(self):
        """Menü çubuğu: Dosya / Araçlar / Yardım + kısayollar."""
        mb = self.menuBar()

        # Dosya menüsü
        m_file = mb.addMenu(T.get("menu.file"))
        self.act_exit = QAction(T.get("menu.exit"), self)
        self.act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        self.act_exit.triggered.connect(self._confirm_exit)
        m_file.addAction(self.act_exit)

        # Araçlar menüsü
        m_tools = mb.addMenu(T.get("menu.tools"))
        self.act_audit = QAction(T.get("menu.data_audit"), self)
        self.act_audit.triggered.connect(lambda: self.switch_page(6))
        m_tools.addAction(self.act_audit)
        self.act_backup = QAction(T.get("menu.backup"), self)
        self.act_backup.triggered.connect(lambda: self.switch_page(5))
        m_tools.addAction(self.act_backup)
        m_tools.addSeparator()
        self.act_updates = QAction(T.get("menu.check_updates"), self)
        self.act_updates.setShortcut(QKeySequence("Ctrl+U"))
        self.act_updates.triggered.connect(self.open_update_dialog)
        m_tools.addAction(self.act_updates)

        # Araçlar menüsü: eski kurulumdan veri taşıma
        self.act_migrate = QAction(T.get("menu.migrate_data"), self)
        self.act_migrate.triggered.connect(self.open_migration_wizard)
        m_tools.insertAction(self.act_updates, self.act_migrate)
        m_tools.insertSeparator(self.act_updates)

        # Araçlar menüsü: hızlı ölçüm girişi (mera seçtirerek diyalog)
        self.act_add_meas = QAction(T.get("menu.add_measurement"), self)
        self.act_add_meas.triggered.connect(self._add_measurement_via_menu)
        m_tools.insertAction(self.act_migrate, self.act_add_meas)

        # Yardım menüsü
        m_help = mb.addMenu(T.get("menu.help"))
        self.act_about = QAction(T.get("menu.about"), self)
        self.act_about.setShortcut(QKeySequence("F1"))
        self.act_about.triggered.connect(self.open_about_dialog)
        m_help.addAction(self.act_about)

    def _init_statusbar(self):
        """Durum çubuğu: hazır bilgisi, kural sürümü ve güncelleme bildirimi."""
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.status_left = QLabel("")
        self.status_left.setStyleSheet("color: #5C7164; padding: 2px 8px;")
        self.status_right = QLabel("")
        self.status_right.setStyleSheet("color: #3E8E63; padding: 2px 8px; font-weight: bold;")
        sb.addWidget(self.status_left, 1)
        sb.addPermanentWidget(self.status_right)
        self._update_statusbar()

    def _update_statusbar(self):
        stats = self.db.get_statistics()
        self.status_left.setText(T.get("status.ready", n=stats["total_count"]))
        self.status_right.setText(T.get("status.rules_v", v=self.db.get_rule_version()))

    def _check_updates_background(self):
        """Açılışta sessiz güncelleme denetimi; yeni sürüm varsa durum çubuğunda bildirir."""
        try:
            from core import update_checker as uc
            info = uc.check_for_updates()
            if info.get("status") == "update_available":
                v = info["manifest"]["version"]
                self.status_right.setText(
                    self.status_right.text() + "   |   " + T.get("status.update_available", v=v))
                self.status_right.setStyleSheet(
                    "color: #B45309; padding: 2px 8px; font-weight: bold;")
        except Exception as exc:
            self._log.debug("Güncelleme denetimi atlandı: %s", exc)

    def _confirm_exit(self):
        reply = QMessageBox.question(
            self, T.get("msg.quit_title"), T.get("msg.quit_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.close()

    def open_update_dialog(self):
        dlg = UpdateDialog(self, db_manager=self.db)
        dlg.exec()

    # ---- Veri taşıma sihirbazı -------------------------------------------

    def open_migration_wizard(self):
        """Araçlar > Eski Kurulumdan Veri Taşı: sihirbazı açar; tamamlanınca
        görünümleri ve durum çubuğunu tazeler."""
        from gui.migration_wizard import MigrationWizard
        dlg = MigrationWizard(self.db, self)
        dlg.refresh_requested.connect(self._after_migration)
        dlg.exec()

    def offer_migration_on_startup(self):
        """Açılışta: mevcut DB yalnızca örnek veri ve bilinen konumlarda daha
        zengin eski DB varsa kullanıcıya taşıma sihirbazı önerilir.
        Onaylanırsa sihirbaz açılır; kaynak işaret dosyası temizlenir.
        Herhangi bir hata sessizce loglanır (öneri akışı engellenmez)."""
        try:
            from database import migration
            proposal = migration.auto_proposal(self.db.db_path)
            if not proposal:
                return
            self._log.info(
                "Eski kurulum algılandı (%s: %d mera) — öneri gösteriliyor",
                proposal.get("path"), proposal.get("pastures", 0))
            reply = QMessageBox.question(
                self,
                T.get("mig.startup.title"),
                T.get("mig.startup.question",
                      path=proposal.get("path", ""),
                      pastures=proposal.get("pastures", 0),
                      measurements=proposal.get("measurements", 0)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                migration.clear_marker()
                self.open_migration_wizard()
            else:
                self._log.info("Taşıma önerisi reddedildi (açılış)")
        except Exception as exc:
            self._log.debug("Taşıma önerisi atlandı: %s", exc)

    def _after_migration(self):
        """Taşıma sonrası: tüm görünümler + durum çubuğu tazelenir."""
        try:
            self.refresh_all_views()
        except Exception as exc:
            self._log.warning("Taşıma sonrası görünüm tazeleme hatası: %s", exc)
        self._update_statusbar()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("sidebarFrame")
        sidebar_frame.setFixedWidth(250)

        # Kenar çubuğu kaydırılabilir: yüksek DPI / kısa pencerede içerik
        # (başlık + 9 gezinme + istatistik + dil + footer) ekrana sığmazsa
        # widget'lar sıfıra ezilip okunamaz hale gelir; scroll area bunu önler.
        sidebar_scroll = QScrollArea()
        self.sidebar_scroll = sidebar_scroll
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("sidebarFrame")
        sidebar_frame.setFixedWidth(250)
        sidebar_scroll.setWidget(sidebar_frame)

        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(15, 20, 15, 15)
        sidebar_layout.setSpacing(10)

        # App Brand Header with Logo Icon
        brand_layout = QHBoxLayout()
        logo_label = QLabel()
        icon_path = get_asset_path("app_icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(0)
        app_title = QLabel("MERA-BİS PRO")
        app_title.setObjectName("appTitleLabel")
        app_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #558B2F; padding: 0;")
        self.app_subtitle = QLabel(T.get("sidebar.subtitle"))
        self.app_subtitle.setStyleSheet("font-size: 11px; color: #5C7164;")
        app_subtitle = self.app_subtitle
        title_vbox.addWidget(app_title)
        title_vbox.addWidget(app_subtitle)

        brand_layout.addWidget(logo_label)
        brand_layout.addLayout(title_vbox)
        sidebar_layout.addLayout(brand_layout)

        # Nav Buttons
        self.nav_btn_map = QPushButton(T.get("nav.map"))
        self.nav_btn_map.setProperty("class", "nav-btn")
        self.nav_btn_map.setCheckable(True)
        self.nav_btn_map.setChecked(True)
        self.nav_btn_map.clicked.connect(lambda: self.switch_page(0))

        self.nav_btn_analytics = QPushButton(T.get("nav.analytics"))
        self.nav_btn_analytics.setProperty("class", "nav-btn")
        self.nav_btn_analytics.setCheckable(True)
        self.nav_btn_analytics.clicked.connect(lambda: self.switch_page(1))

        self.nav_btn_table = QPushButton(T.get("nav.table"))
        self.nav_btn_table.setProperty("class", "nav-btn")
        self.nav_btn_table.setCheckable(True)
        self.nav_btn_table.clicked.connect(lambda: self.switch_page(2))

        self.nav_btn_calc = QPushButton(T.get("nav.calc"))
        self.nav_btn_calc.setProperty("class", "nav-btn")
        self.nav_btn_calc.setCheckable(True)
        self.nav_btn_calc.clicked.connect(lambda: self.switch_page(3))

        self.nav_btn_rotation = QPushButton(T.get("nav.rotation"))
        self.nav_btn_rotation.setProperty("class", "nav-btn")
        self.nav_btn_rotation.setCheckable(True)
        self.nav_btn_rotation.clicked.connect(lambda: self.switch_page(4))

        self.nav_btn_measurements = QPushButton(T.get("nav.measurements"))
        self.nav_btn_measurements.setProperty("class", "nav-btn")
        self.nav_btn_measurements.setCheckable(True)
        self.nav_btn_measurements.clicked.connect(lambda: self.switch_page(5))

        self.nav_btn_backup = QPushButton(T.get("nav.backup"))
        self.nav_btn_backup.setProperty("class", "nav-btn")
        self.nav_btn_backup.setCheckable(True)
        self.nav_btn_backup.clicked.connect(lambda: self.switch_page(6))

        self.nav_btn_audit = QPushButton(T.get("nav.audit"))
        self.nav_btn_audit.setProperty("class", "nav-btn")
        self.nav_btn_audit.setCheckable(True)
        self.nav_btn_audit.clicked.connect(lambda: self.switch_page(7))

        self.nav_btn_about = QPushButton(T.get("nav.about"))
        self.nav_btn_about.setProperty("class", "nav-btn")
        self.nav_btn_about.clicked.connect(self.open_about_dialog)

        sidebar_layout.addWidget(self.nav_btn_map)
        sidebar_layout.addWidget(self.nav_btn_analytics)
        sidebar_layout.addWidget(self.nav_btn_table)
        sidebar_layout.addWidget(self.nav_btn_calc)
        sidebar_layout.addWidget(self.nav_btn_rotation)
        sidebar_layout.addWidget(self.nav_btn_measurements)
        sidebar_layout.addWidget(self.nav_btn_backup)
        sidebar_layout.addWidget(self.nav_btn_audit)
        sidebar_layout.addWidget(self.nav_btn_about)

        sidebar_layout.addStretch()

        # Sidebar Quick Stats Box
        # NOT: 'QFrame {' genel seçici QLabel'ları (QFrame türevidi) da yakalayıp
        # her etikete kenarlık/padding uygular; yüksek DPI'da metin bozulur.
        # Seçici nesne adına sabitlenir, boşluk layout ile verilir.
        self.quick_stats_box = QFrame()
        self.quick_stats_box.setObjectName("quickStatsBox")
        self.quick_stats_box.setStyleSheet("""
            QFrame#quickStatsBox {
                background-color: #FFFFFF; border: 1px solid #C6DBC1; border-radius: 8px;
            }
        """)
        qs_layout = QVBoxLayout(self.quick_stats_box)
        qs_layout.setContentsMargins(10, 8, 10, 8)
        qs_layout.setSpacing(2)

        self.qs_title = QLabel(T.get("sidebar.quick_title"))
        self.qs_title.setStyleSheet("font-size: 11px; color: #5C7164; font-weight: bold;")
        qs_title = self.qs_title
        self.qs_val1 = QLabel("0 Ha")
        self.qs_val1.setStyleSheet("font-size: 15px; color: #558B2F; font-weight: bold;")
        self.qs_val2 = QLabel("0 Kayıtlı Mera")
        self.qs_val2.setStyleSheet("font-size: 11px; color: #5C7164;")

        qs_layout.addWidget(qs_title)
        qs_layout.addWidget(self.qs_val1)
        qs_layout.addWidget(self.qs_val2)

        sidebar_layout.addWidget(self.quick_stats_box)

        # Dil Seçimi (doğrulama mesajları için Türkçe/İngilizce)
        lang_row = QHBoxLayout()
        self.lang_lbl = QLabel("🌐 Dil / Language")
        self.lang_lbl.setStyleSheet("font-size: 11px; color: #5C7164; font-weight: bold;")
        lang_lbl = self.lang_lbl
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Türkçe", "tr")
        self.lang_combo.addItem("English", "en")
        saved_lang = QSettings().value("language", "tr")
        self.lang_combo.setCurrentIndex(1 if saved_lang == "en" else 0)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(lang_lbl)
        lang_row.addWidget(self.lang_combo, stretch=1)
        sidebar_layout.addLayout(lang_row)

        # Footer Credit Banner (User Requested CopyRight Text)
        footer_card = QFrame()
        footer_card.setObjectName("footerCard")
        footer_card.setStyleSheet("""
            QFrame#footerCard {
                background-color: #FFFFFF; border: 1px solid #C6DBC1; border-radius: 6px; margin-top: 5px;
            }
        """)
        footer_layout = QVBoxLayout(footer_card)
        footer_layout.setContentsMargins(8, 6, 8, 6)
        footer_layout.setSpacing(2)

        self.credit_lbl = QLabel(T.get("footer.programmer"))
        self.credit_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #558B2F;")
        self.sub_credit_lbl = QLabel(T.get("footer.role"))
        self.sub_credit_lbl.setStyleSheet("font-size: 10px; color: #5C7164;")
        self.copy_lbl = QLabel(T.get("footer.copyright"))
        self.copy_lbl.setStyleSheet("font-size: 9px; color: #5C7164;")
        credit_lbl = self.credit_lbl
        sub_credit_lbl = self.sub_credit_lbl
        copy_lbl = self.copy_lbl

        footer_layout.addWidget(credit_lbl)
        footer_layout.addWidget(sub_credit_lbl)
        footer_layout.addWidget(copy_lbl)

        sidebar_layout.addWidget(footer_card)
        sidebar_layout.addStretch(1)

        root_layout.addWidget(sidebar_scroll)

        # 2. Main Work Area (Stacked Widget)
        self.stacked_widget = QStackedWidget()

        # Page 0: Map Workspace
        self.page_map_workspace = QWidget()
        map_work_layout = QHBoxLayout(self.page_map_workspace)
        map_work_layout.setContentsMargins(0, 0, 0, 0)
        map_work_layout.setSpacing(0)

        self.map_view = MapView(db_manager=self.db)
        self.detail_panel = PastureDetailPanel()
        self.detail_panel.hide()

        map_work_layout.addWidget(self.map_view, stretch=1)
        map_work_layout.addWidget(self.detail_panel)

        # Page 1: Analytics Dashboard
        self.analytics_view = AnalyticsView(self.db)

        # Page 2: Table Data View
        self.table_view = PastureTableView(self.db)

        # Page 3: Capacity Calculator
        self.calculator_view = CalculatorView()

        # Page 4: Rotation Grazing Planner
        self.rotation_view = RotationView(self.db)

        # Page 5: Vegetation Measurements & Observations
        self.measurements_view = MeasurementsView(self.db)

        # Page 6: Backup & Restore Management
        self.backup_view = BackupView(self.db)
        self.backup_view.restored.connect(self.refresh_all_views)

        # Page 6: Data Audit & Consistency
        self.audit_view = AuditView(self.db)

        self.stacked_widget.addWidget(self.page_map_workspace)
        self.stacked_widget.addWidget(self.analytics_view)
        self.stacked_widget.addWidget(self.table_view)
        self.stacked_widget.addWidget(self.calculator_view)
        self.stacked_widget.addWidget(self.rotation_view)
        self.stacked_widget.addWidget(self.measurements_view)
        self.stacked_widget.addWidget(self.backup_view)
        self.stacked_widget.addWidget(self.audit_view)

        root_layout.addWidget(self.stacked_widget, stretch=1)

        # Connect Signals
        self.map_view.bridge.mapReadySignal.connect(self._on_map_ready)
        self.map_view.pastureSelected.connect(self.select_pasture_by_id)
        self.map_view.addMeasurementRequested.connect(self.open_measurement_dialog)

        self.detail_panel.closeRequested.connect(self.detail_panel.hide)
        self.detail_panel.zoomRequested.connect(self.map_view.focus_location)
        self.detail_panel.editRequested.connect(self.open_edit_dialog)
        self.detail_panel.deleteRequested.connect(self.delete_pasture)

        self.table_view.pastureSelected.connect(self._on_table_pasture_selected)
        self.table_view.addRequested.connect(self.open_add_dialog)

        self.update_stats()
        # Tüm widget'lar hazır olduktan sonra kayıtlı dili uygula (retranslate tüm görünümlere ulaşır)
        self._on_language_changed()
        # Açılışta sessiz güncelleme denetimi (arayüzü engellemez)
        QTimer.singleShot(2500, self._check_updates_background)
        QTimer.singleShot(150, self.offer_migration_on_startup)

    def _on_map_ready(self):
        self.refresh_all_views()

    def refresh_all_views(self):
        pastures = self.db.get_all_pastures()
        self.map_view.update_map_data(pastures)
        self.table_view.refresh_table()
        self.analytics_view.refresh_analytics()
        self.update_stats()
        self._update_statusbar()

    def update_stats(self):
        stats = self.db.get_statistics()
        self.qs_val1.setText(f"{stats['total_area']:,} Ha")
        self.qs_val2.setText(T.get("sidebar.stats_count", n=stats['total_count']))

    def _on_language_changed(self):
        """Aktif dili uygular, tüm arayüzü yeniden diline çevirir ve kalıcı olarak saklar."""
        lang = self.lang_combo.currentData()
        T.set_language(lang)
        QSettings().setValue("language", lang)
        self._retranslate()

    def _retranslate(self):
        """Dil değişince ana pencere ve tüm görünümlerin metinlerini günceller."""
        self.setWindowTitle(T.get("window.title"))
        self.app_subtitle.setText(T.get("sidebar.subtitle"))
        self.qs_title.setText(T.get("sidebar.quick_title"))
        self.credit_lbl.setText(T.get("footer.programmer"))
        self.sub_credit_lbl.setText(T.get("footer.role"))
        self.copy_lbl.setText(T.get("footer.copyright"))
        # Menüler ve durum çubuğu
        if self.menuBar().actions():
            self.menuBar().actions()[0].setText(T.get("menu.file"))
            if len(self.menuBar().actions()) > 1:
                self.menuBar().actions()[1].setText(T.get("menu.tools"))
                self.menuBar().actions()[2].setText(T.get("menu.help"))
            for act in (self.act_exit, self.act_audit, self.act_backup,
                        self.act_add_meas, self.act_migrate, self.act_updates,
                        self.act_about):
                if act is not None:
                    act.setText({
                        id(self.act_exit): "menu.exit",
                        id(self.act_audit): "menu.data_audit",
                        id(self.act_backup): "menu.backup",
                        id(self.act_add_meas): "menu.add_measurement",
                        id(self.act_migrate): "menu.migrate_data",
                        id(self.act_updates): "menu.check_updates",
                        id(self.act_about): "menu.about",
                    }[id(act)])
        self.nav_btn_map.setText(T.get("nav.map"))
        self.nav_btn_analytics.setText(T.get("nav.analytics"))
        self.nav_btn_table.setText(T.get("nav.table"))
        self.nav_btn_calc.setText(T.get("nav.calc"))
        self.nav_btn_rotation.setText(T.get("nav.rotation"))
        self.nav_btn_measurements.setText(T.get("nav.measurements"))
        self.nav_btn_backup.setText(T.get("nav.backup"))
        self.nav_btn_audit.setText(T.get("nav.audit"))
        self.nav_btn_about.setText(T.get("nav.about"))
        self.update_stats()

        # Görünümler
        self.map_view.set_language(T.get_language())
        self.table_view.retranslate()
        self.calculator_view.retranslate()
        self.analytics_view.retranslate()
        self.rotation_view.retranslate()
        self.measurements_view.retranslate()
        self.backup_view.retranslate()
        self.audit_view.retranslate()
        self.detail_panel.retranslate()

    def switch_page(self, page_index):
        self.stacked_widget.setCurrentIndex(page_index)

        self.nav_btn_map.setChecked(page_index == 0)
        self.nav_btn_analytics.setChecked(page_index == 1)
        self.nav_btn_table.setChecked(page_index == 2)
        self.nav_btn_calc.setChecked(page_index == 3)
        self.nav_btn_rotation.setChecked(page_index == 4)
        self.nav_btn_measurements.setChecked(page_index == 5)
        self.nav_btn_backup.setChecked(page_index == 6)
        self.nav_btn_audit.setChecked(page_index == 7)

        if page_index == 1:
            self.analytics_view.refresh_analytics()
        elif page_index == 2:
            self.table_view.refresh_table()
        elif page_index == 4:
            self.rotation_view.refresh_pastures()
        elif page_index == 5:
            self.measurements_view.refresh_pastures()
        elif page_index == 6:
            self.backup_view.refresh()
        elif page_index == 7:
            self.audit_view.refresh()

    def select_pasture_by_id(self, pasture_id):
        pasture = self.db.get_pasture_by_id(pasture_id)
        if pasture:
            self.detail_panel.set_pasture_data(pasture)
            self.detail_panel.show()
            self.map_view.focus_location(pasture["lat"], pasture["lng"], zoom=12)

    def open_measurement_dialog(self, pasture_id, source="map"):
        """Popup'taki 'Ölçüm Ekle' düğmesi: seçili mera için ölçüm diyaloğu.

        source denetim izine yazılır ('map': harita popup'ı, 'menu': menü kısayolu).
        Kayıt yapıldıysa harita verisi (son ölçüm bloğu dahil) tazelenir ve
        aynı meranın popup'ı yeniden açılır.
        """
        try:
            dialog = MeasurementDialog(self, self.db, pasture_id, source=source)
        except ValueError as exc:
            LOG.warning("Ölçüm diyaloğu açılamadı: %s", exc)
            return
        dialog.exec()
        if dialog.result() == MeasurementDialog.DialogCode.Accepted:
            self.map_view.reload_map_data(pasture_id=dialog.saved_pasture_id())
            self.measurements_view.refresh_table()

    def _add_measurement_via_menu(self):
        """Araçlar > Ölçüm Ekle: mera seçtir, sonra diyaloğu aç.

        Harita görünümünde seçili/merkeze yakın mera varsa doğrudan o önerilir.
        """
        pastures = self.db.get_all_pastures()
        if not pastures:
            QMessageBox.information(self, T.get("meas.msg_title"),
                                    T.get("meas.warn_no_pasture"))
            return
        names = [f"{p['code']} - {p['name']} ({p['city']})" for p in pastures]
        name, ok = QInputDialog.getItem(
            self, T.get("menu.add_measurement"), T.get("meas.lbl_pasture"),
            names, 0, False)
        if not ok:
            return
        idx = names.index(name)
        self.open_measurement_dialog(pastures[idx]["id"], source="menu")

    def _on_table_pasture_selected(self, pasture):
        self.switch_page(0)
        self.select_pasture_by_id(pasture["id"])

    def open_add_dialog(self):
        default_code = self.db.get_next_code()
        dialog = PastureDialog(self, default_code=default_code, db=self.db)
        if dialog.exec() == PastureDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                new_id = self.db.add_pasture(data)
            except sqlite3.IntegrityError:
                QMessageBox.critical(
                    self, T.get("msg.error_title"),
                    T.get("msg.code_in_use", code=data['code'])
                )
                return
            except Exception as exc:
                QMessageBox.critical(
                    self, T.get("msg.error_title"), T.get("msg.add_error", exc=exc)
                )
                return
            self.refresh_all_views()
            self.select_pasture_by_id(new_id)

    def open_edit_dialog(self, pasture_data):
        dialog = PastureDialog(self, pasture_data=pasture_data, db=self.db)
        if dialog.exec() == PastureDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.db.update_pasture(pasture_data["id"], data)
            except sqlite3.IntegrityError:
                QMessageBox.critical(
                    self, T.get("msg.error_title"),
                    T.get("msg.code_used_edit", code=data['code'])
                )
                return
            except Exception as exc:
                QMessageBox.critical(
                    self, T.get("msg.error_title"), T.get("msg.update_error", exc=exc)
                )
                return
            self.refresh_all_views()
            self.select_pasture_by_id(pasture_data["id"])

    def delete_pasture(self, pasture_id):
        reply = QMessageBox.question(
            self, T.get("msg.delete_confirm_title"), T.get("msg.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_pasture(pasture_id)
            except Exception as exc:
                QMessageBox.critical(
                    self, T.get("msg.error_title"), T.get("msg.delete_error", exc=exc)
                )
                return
            self.detail_panel.hide()
            self.refresh_all_views()

    def open_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """Kapanışta harita web motorunu düzgün kapatır (geçici profil kilidi kalıntılarını önler)."""
        try:
            self.map_view.web_view.stop()
            self.map_view.web_view.page().deleteLater()
            self.map_view.web_view.deleteLater()
        except RuntimeError:
            pass
        super().closeEvent(event)
