from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QScrollArea, QFrame, QProgressBar
)
from PyQt6.QtCore import pyqtSignal, Qt

from i18n import T

class PastureDetailPanel(QWidget):
    closeRequested = pyqtSignal()
    zoomRequested = pyqtSignal(float, float)
    editRequested = pyqtSignal(dict)
    deleteRequested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pasture = None
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("pastureDetailPanel")
        self.setMinimumWidth(360)
        self.setMaximumWidth(450)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header Bar
        header_layout = QHBoxLayout()
        self.title_label = QLabel(T.get("detail.title"))
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #558B2F;")

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #E7F1E2; color: #3D5245; border: none; border-radius: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #E53935; color: white; }
        """)
        self.close_btn.clicked.connect(self.closeRequested.emit)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        main_layout.addLayout(header_layout)

        # Summary Header Card
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #C6DBC1;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        summary_layout = QVBoxLayout(self.summary_card)

        self.name_label = QLabel(T.get("detail.no_pasture"))
        self.name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #23332A;")

        self.location_label = QLabel(T.get("detail.location"))
        self.location_label.setStyleSheet("font-size: 12px; color: #5C7164;")

        self.status_badge = QLabel("Aktif Otlatma")
        self.status_badge.setStyleSheet("""
            background-color: #7CB342; color: #FFFFFF; padding: 4px 10px;
            border-radius: 12px; font-size: 11px; font-weight: bold; max-width: 140px;
        """)

        summary_layout.addWidget(self.name_label)
        summary_layout.addWidget(self.location_label)
        summary_layout.addWidget(self.status_badge)
        main_layout.addWidget(self.summary_card)

        # Tabs for categorized details
        self.tabs = QTabWidget()

        # Tab 1: Coğrafi & Genel
        self.tab_general = QWidget()
        self.general_layout = QVBoxLayout(self.tab_general)
        self.scroll_general = self._create_scrollable_info_widget()
        self.general_layout.addWidget(self.scroll_general)
        self.tabs.addTab(self.tab_general, T.get("detail.tab_general"))

        # Tab 2: Vejetasyon & Kapasite
        self.tab_veg = QWidget()
        self.veg_layout = QVBoxLayout(self.tab_veg)
        self.scroll_veg = self._create_scrollable_info_widget()
        self.veg_layout.addWidget(self.scroll_veg)
        self.tabs.addTab(self.tab_veg, T.get("detail.tab_veg"))

        # Tab 3: Toprak & Su
        self.tab_soil = QWidget()
        self.soil_layout = QVBoxLayout(self.tab_soil)
        self.scroll_soil = self._create_scrollable_info_widget()
        self.soil_layout.addWidget(self.scroll_soil)
        self.tabs.addTab(self.tab_soil, T.get("detail.tab_soil"))

        # Tab 4: İdari & Notlar
        self.tab_notes = QWidget()
        self.notes_layout = QVBoxLayout(self.tab_notes)
        self.scroll_notes = self._create_scrollable_info_widget()
        self.notes_layout.addWidget(self.scroll_notes)
        self.tabs.addTab(self.tab_notes, T.get("detail.tab_notes"))

        main_layout.addWidget(self.tabs)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.zoom_btn = QPushButton(T.get("detail.btn_zoom"))
        self.zoom_btn.setObjectName("btnZoom")
        self.zoom_btn.setStyleSheet("""
            QPushButton {
                background-color: #7CB342; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 8px;
            }
            QPushButton:hover { background-color: #9CCC65; }
        """)
        self.zoom_btn.clicked.connect(self._on_zoom_clicked)

        self.edit_btn = QPushButton(T.get("detail.btn_edit"))
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #3D5245; border: 1px solid #C6DBC1; border-radius: 6px; padding: 8px;
            }
            QPushButton:hover { border-color: #7CB342; color: #558B2F; }
        """)
        self.edit_btn.clicked.connect(self._on_edit_clicked)

        self.delete_btn = QPushButton(T.get("detail.btn_delete"))
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; border: none; border-radius: 6px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        self.delete_btn.clicked.connect(self._on_delete_clicked)

        btn_layout.addWidget(self.zoom_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        main_layout.addLayout(btn_layout)

    def _create_scrollable_info_widget(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        scroll.setWidget(container)
        return scroll

    def retranslate(self):
        """Dil değişince statik metinleri ve (açıksa) mevcut mera kartını günceller."""
        self.title_label.setText(T.get("detail.title"))
        self.location_label.setText(T.get("detail.location"))
        if not self.current_pasture:
            self.name_label.setText(T.get("detail.no_pasture"))
        self.tabs.setTabText(0, T.get("detail.tab_general"))
        self.tabs.setTabText(1, T.get("detail.tab_veg"))
        self.tabs.setTabText(2, T.get("detail.tab_soil"))
        self.tabs.setTabText(3, T.get("detail.tab_notes"))
        self.zoom_btn.setText(T.get("detail.btn_zoom"))
        self.edit_btn.setText(T.get("detail.btn_edit"))
        self.delete_btn.setText(T.get("detail.btn_delete"))
        if self.current_pasture:
            self.set_pasture_data(self.current_pasture)

    def set_pasture_data(self, pasture):
        self.current_pasture = pasture
        if not pasture:
            return

        self.name_label.setText(pasture["name"])
        self.location_label.setText(f"{pasture['city']} / {pasture['district']} - {pasture.get('village', '')} ({pasture['region']})")
        self.status_badge.setText(pasture["status"])

        # Tab 1: General
        gen_container = self.scroll_general.widget()
        self._clear_layout(gen_container.layout())
        g_lay = gen_container.layout()

        g_lay.addWidget(self._create_info_row(T.get("detail.lbl_code"), pasture["code"]))
        g_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_area"),
            T.get("detail.area_fmt", area=pasture['area_hectares'],
                  dekar=round(pasture['area_hectares']*10, 1))
        ))
        g_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_elevation"), T.get("detail.elev_fmt", elev=pasture['elevation_m'])
        ))
        g_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_coord"),
            T.get("detail.coord_fmt", lat=pasture['lat'], lng=pasture['lng'])
        ))
        g_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_season"),
            T.get("detail.season_fmt",
                  start=pasture.get('grazing_season_start', '05-01'),
                  end=pasture.get('grazing_season_end', '10-01'))
        ))
        g_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_allocation"), pasture.get("allocation_purpose", "-")
        ))
        g_lay.addStretch()

        # Tab 2: Vegetation & Capacity
        veg_container = self.scroll_veg.widget()
        self._clear_layout(veg_container.layout())
        v_lay = veg_container.layout()

        v_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_bbhb"), T.get("detail.count_fmt", n=pasture['bbhb_capacity'])
        ))
        v_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_kbhb"), T.get("detail.count_fmt", n=pasture['kbhb_capacity'])
        ))
        v_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_yield"),
            T.get("detail.yield_fmt", n=pasture['dry_hay_yield_kg_per_ha'])
        ))

        # Progress bar for vegetation coverage
        cov_lbl = QLabel(T.get("detail.lbl_coverage", pct=pasture['vegetation_coverage_pct']))
        cov_lbl.setStyleSheet("font-weight: bold; color: #558B2F; margin-top: 5px;")
        pbar = QProgressBar()
        pbar.setValue(pasture['vegetation_coverage_pct'])
        pbar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #C6DBC1; border-radius: 5px; text-align: center; color: #23332A; background: #FBFDFA; height: 18px;
            }
            QProgressBar::chunk { background-color: #7CB342; border-radius: 4px; }
        """)
        v_lay.addWidget(cov_lbl)
        v_lay.addWidget(pbar)

        v_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_plants"), pasture.get("dominant_plants", "-")
        ))
        v_lay.addStretch()

        # Tab 3: Soil & Water
        soil_container = self.scroll_soil.widget()
        self._clear_layout(soil_container.layout())
        s_lay = soil_container.layout()

        s_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_soil"), pasture.get("soil_type", "-")
        ))
        s_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_water"), pasture.get("water_source", "-")
        ))
        s_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_erosion"), pasture.get("erosion_risk", "-")
        ))
        s_lay.addStretch()

        # Tab 4: Notes & Admin
        notes_container = self.scroll_notes.widget()
        self._clear_layout(notes_container.layout())
        n_lay = notes_container.layout()

        n_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_management"), pasture.get("management_entity", "-")
        ))
        n_lay.addWidget(self._create_info_row(
            T.get("detail.lbl_notes"), pasture.get("notes", T.get("detail.no_notes"))
        ))
        n_lay.addStretch()

    def _create_info_row(self, label_text, value_text):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FBFDFA; border: 1px solid #C6DBC1; border-radius: 6px; padding: 6px 10px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 11px; color: #5C7164; font-weight: bold;")
        val = QLabel(str(value_text))
        val.setStyleSheet("font-size: 13px; color: #23332A;")
        val.setWordWrap(True)

        layout.addWidget(lbl)
        layout.addWidget(val)
        return frame

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _on_zoom_clicked(self):
        if self.current_pasture:
            self.zoomRequested.emit(self.current_pasture["lat"], self.current_pasture["lng"])

    def _on_edit_clicked(self):
        if self.current_pasture:
            self.editRequested.emit(self.current_pasture)

    def _on_delete_clicked(self):
        if self.current_pasture:
            self.deleteRequested.emit(self.current_pasture["id"])
