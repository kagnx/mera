"""
Rotasyonlu Otlatma Planı modülü.

Meraya göre bölmeli rotasyon planı üretir ve sezonu duvar takvimi
biçiminde görselleştirir (her gün hangi bölmenin otlatıldığı renkli gösterilir).
"""
import math
from datetime import date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QDoubleSpinBox, QPushButton, QFrame, QGroupBox, QFormLayout,
    QTabWidget, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QFont, QPen

from gui.rotation_planner import compute_rotation_plan, format_interval
from i18n import T

PADDOCK_COLORS = [
    "#52B788", "#74C69D", "#95D5B2", "#2D6A4F", "#1B4332", "#40916C",
    "#F59E0B", "#3B82F6", "#A78BFA", "#F472B6", "#14B8A6", "#F87171"
]


class RotationCalendarWidget(QWidget):
    """Sezonu duvar takvimi olarak çizen özel widget."""

    CELL = 26
    PAD = 12
    TITLE_H = 28
    WD_H = 18
    SPACING = 24
    LEGEND_H = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan = None
        self._months = []
        self.setMinimumHeight(500)

    def set_plan(self, plan):
        self.plan = plan
        self._layout_geometry()
        self.update()

    def _layout_geometry(self):
        self._months = []
        if not self.plan:
            self.setMinimumWidth(600)
            return
        d = self.plan["season_start"]
        end = self.plan["season_end"]
        while d <= end:
            if (d.year, d.month) not in [(m.year, m.month) for m in self._months]:
                self._months.append(date(d.year, d.month, 1))
            d += timedelta(days=1)

        n = len(self._months)
        self._cols = 3 if n <= 6 else 4
        self._cols = min(self._cols, n)
        self._rows = math.ceil(n / self._cols) if n else 1

        block_w = 2 * self.PAD + 7 * self.CELL
        block_h = self.PAD + self.TITLE_H + self.WD_H + 6 * self.CELL + self.PAD
        total_w = self._cols * block_w + (self._cols - 1) * self.SPACING
        total_h = self._rows * block_h + (self._rows - 1) * self.SPACING + self.LEGEND_H
        self.setMinimumWidth(total_w + 40)
        self.setMinimumHeight(total_h + 40)

    def sizeHint(self):
        if self._months:
            return QSize(self.minimumWidth(), self.minimumHeight())
        return QSize(1200, 500)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.plan:
            painter.setPen(QColor("#5C7164"))
            font = QFont("Segoe UI", 13)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             T.get("rotation.cal_no_plan"))
            return

        schedule_map = self.plan["schedule_map"]
        season_start = self.plan["season_start"]
        season_end = self.plan["season_end"]
        n = self.plan["paddock_count"]

        block_w = 2 * self.PAD + 7 * self.CELL
        block_h = self.PAD + self.TITLE_H + self.WD_H + 6 * self.CELL + self.PAD

        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        wd_font = QFont("Segoe UI", 7)
        day_font = QFont("Segoe UI", 7)
        pad_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        legend_font = QFont("Segoe UI", 9)

        for idx, month_first in enumerate(self._months):
            col = idx % self._cols
            row = idx // self._cols
            ox = self.PAD + col * (block_w + self.SPACING)
            oy = self.PAD + row * (block_h + self.SPACING)

            # Ay başlığı
            months = T.get_list("months")
            painter.setFont(title_font)
            painter.setPen(QColor("#558B2F"))
            painter.drawText(ox, oy, block_w, self.TITLE_H,
                             Qt.AlignmentFlag.AlignCenter,
                             f"{months[month_first.month - 1]} {month_first.year}")

            # Hafta günü harfleri
            weekdays = T.get_list("weekdays")
            painter.setFont(wd_font)
            painter.setPen(QColor("#7C9284"))
            for w in range(7):
                x = ox + w * self.CELL + (self.CELL - 14) / 2
                painter.drawText(int(x), oy + self.TITLE_H, 16, self.WD_H,
                                 Qt.AlignmentFlag.AlignCenter, weekdays[w])

            # Ayın günleri
            days_in_month = (month_first.replace(month=month_first.month % 12 + 1, day=1)
                             - timedelta(days=1)).day if month_first.month < 12 else 31
            offset = month_first.weekday()  # Pazartesi = 0
            for day in range(1, days_in_month + 1):
                d = date(month_first.year, month_first.month, day)
                cell_col = (offset + day - 1) % 7
                cell_row = (offset + day - 1) // 7
                cx = ox + cell_col * self.CELL
                cy = oy + self.TITLE_H + self.WD_H + cell_row * self.CELL
                rect = (cx, cy, self.CELL, self.CELL)

                in_season = season_start <= d <= season_end
                paddock = schedule_map.get(d)
                if in_season and paddock:
                    color = QColor(PADDOCK_COLORS[(paddock - 1) % len(PADDOCK_COLORS)])
                    painter.fillRect(rect[0] + 1, rect[1] + 1, rect[2] - 2, rect[3] - 2, color)
                    text_color = QColor("#081C15") if color.lightness() > 150 else QColor("#FFFFFF")
                else:
                    painter.fillRect(rect[0] + 1, rect[1] + 1, rect[2] - 2, rect[3] - 2, QColor("#E3EDE0"))
                    text_color = QColor("#8A9D8E")

                painter.setPen(QPen(QColor("#C6DBC1"), 1))
                painter.drawRect(rect[0], rect[1], rect[2], rect[3])

                # Gün numarası (sol üst)
                painter.setFont(day_font)
                painter.setPen(text_color)
                painter.drawText(rect[0] + 2, rect[1] + 2, 18, 12,
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, str(day))
                # Otlatılan bölme numarası (orta)
                if in_season and paddock:
                    painter.setFont(pad_font)
                    painter.drawText(rect[0], rect[1] + 4, rect[2], rect[3] - 6,
                                     Qt.AlignmentFlag.AlignCenter, str(paddock))

        # Lejant
        ly = self.PAD + self._rows * (block_h + self.SPACING) - self.SPACING + self.PAD
        painter.setFont(legend_font)
        x = self.PAD + 4
        for p in range(1, n + 1):
            color = QColor(PADDOCK_COLORS[(p - 1) % len(PADDOCK_COLORS)])
            painter.fillRect(x, ly + 2, 14, 14, color)
            painter.setPen(QPen(QColor("#C6DBC1"), 1))
            painter.drawRect(x, ly + 2, 14, 14)
            painter.setPen(QColor("#5C7164"))
            painter.drawText(x + 18, ly, 80, 20, Qt.AlignmentFlag.AlignVCenter,
                             T.get("rotation.legend_paddock", p=p))
            x += 18 + 78
        painter.setPen(QColor("#5C7164"))
        painter.drawText(x + 8, ly, 250, 20, Qt.AlignmentFlag.AlignVCenter,
                         T.get("rotation.legend_cycle",
                               g=self.plan['graze_days'], r=self.plan['actual_rest_days']))


class RotationView(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_pasture = None
        self.plan = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        self.title_label = QLabel(T.get("rotation.title"))
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #558B2F;")
        main_layout.addWidget(self.title_label)

        self.desc_label = QLabel(T.get("rotation.desc"))
        self.desc_label.setStyleSheet("color: #5C7164; font-size: 13px;")
        self.desc_label.setWordWrap(True)
        main_layout.addWidget(self.desc_label)

        # ---- Parametreler ----
        self.controls_box = QGroupBox(T.get("rotation.group_params"))
        form = QFormLayout(self.controls_box)
        self.rotation_form = form
        form.setSpacing(10)
        controls_box = self.controls_box

        self.pasture_combo = QComboBox()
        self.pasture_combo.currentIndexChanged.connect(self._on_pasture_changed)

        self.paddock_spin = QSpinBox()
        self.paddock_spin.setRange(2, 12)
        self.paddock_spin.setValue(6)
        self.paddock_spin.setSuffix(T.get("rotation.suffix_paddock"))
        self.paddock_spin.setToolTip(T.get("rotation.paddock_tip"))

        self.rest_spin = QSpinBox()
        self.rest_spin.setRange(0, 120)
        self.rest_spin.setValue(30)
        self.rest_spin.setSuffix(T.get("rotation.suffix_days"))
        self.rest_spin.setToolTip(T.get("rotation.rest_tip"))

        self.bbhb_spin = QSpinBox()
        self.bbhb_spin.setRange(0, 100000)
        self.bbhb_spin.setSuffix(" BBHB")

        self.kbhb_spin = QSpinBox()
        self.kbhb_spin.setRange(0, 500000)
        self.kbhb_spin.setSuffix(" KBHB")

        self.yield_spin = QDoubleSpinBox()
        self.yield_spin.setRange(100.0, 10000.0)
        self.yield_spin.setSuffix(" Kg/Ha")

        self.season_info = QLabel(T.get("rotation.season_info"))
        self.season_info.setStyleSheet("color: #3E8E63; font-weight: bold;")

        self.generate_btn = QPushButton(T.get("rotation.btn_generate"))
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #7CB342; color: #FFFFFF; font-size: 14px;
                font-weight: bold; border-radius: 8px; padding: 10px 18px;
            }
            QPushButton:hover { background-color: #9CCC65; }
        """)
        self.generate_btn.clicked.connect(self.generate_plan)

        form.addRow(T.get("rotation.lbl_pasture"), self.pasture_combo)
        form.addRow(self.season_info)
        form.addRow(T.get("rotation.lbl_paddocks"), self.paddock_spin)
        form.addRow(T.get("rotation.lbl_rest"), self.rest_spin)
        form.addRow(T.get("rotation.lbl_bbhb"), self.bbhb_spin)
        form.addRow(T.get("rotation.lbl_kbhb"), self.kbhb_spin)
        form.addRow(T.get("rotation.lbl_yield"), self.yield_spin)
        form.addRow(self.generate_btn)
        main_layout.addWidget(controls_box)

        # ---- Özet kartları ----
        self.summary_layout = QHBoxLayout()
        self.summary_layout.setSpacing(10)
        main_layout.addLayout(self.summary_layout)

        # ---- Sekmeler ----
        self.tabs = QTabWidget()

        # Takvim sekmesi
        tab_calendar = QWidget()
        cal_layout = QVBoxLayout(tab_calendar)
        cal_layout.setContentsMargins(5, 5, 5, 5)
        self.calendar_widget = RotationCalendarWidget()
        cal_scroll = QScrollArea()
        cal_scroll.setWidgetResizable(True)
        cal_scroll.setWidget(self.calendar_widget)
        cal_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        cal_layout.addWidget(cal_scroll)
        self.tabs.addTab(tab_calendar, "📅 Takvim")

        # Detay sekmesi
        tab_detail = QWidget()
        det_layout = QVBoxLayout(tab_detail)
        det_layout.setContentsMargins(5, 5, 5, 5)
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(5)
        self.detail_table.setHorizontalHeaderLabels([
            T.get("rotation.h_paddock"), T.get("rotation.h_area"),
            T.get("rotation.h_graze_days"), T.get("rotation.h_graze_iv"),
            T.get("rotation.h_rest_iv"),
        ])
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.detail_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.detail_table.setAlternatingRowColors(True)
        det_layout.addWidget(self.detail_table)
        self.tabs.addTab(tab_detail, "📋 Plan Detayı")

        main_layout.addWidget(self.tabs, stretch=1)

        self.refresh_pastures()

    # ---- Veri ve hesaplama ----
    def refresh_pastures(self):
        pastures = self.db.get_all_pastures()
        current_code = self.current_pasture["code"] if self.current_pasture else None
        self.pasture_combo.blockSignals(True)
        self.pasture_combo.clear()
        for p in pastures:
            self.pasture_combo.addItem(f"{p['code']} - {p['name']} ({p['city']})", p["id"])
        self.pasture_combo.blockSignals(False)
        if current_code:
            for i in range(self.pasture_combo.count()):
                pid = self.pasture_combo.itemData(i)
                p = self.db.get_pasture_by_id(pid)
                if p and p["code"] == current_code:
                    self.pasture_combo.setCurrentIndex(i)
                    break
        else:
            self._on_pasture_changed()

    def _on_pasture_changed(self):
        idx = self.pasture_combo.currentIndex()
        if idx < 0:
            return
        pasture = self.db.get_pasture_by_id(self.pasture_combo.itemData(idx))
        if not pasture:
            return
        self.current_pasture = pasture
        self.bbhb_spin.setValue(int(pasture.get("bbhb_capacity") or 0))
        self.kbhb_spin.setValue(int(pasture.get("kbhb_capacity") or 0))
        self.yield_spin.setValue(float(pasture.get("dry_hay_yield_kg_per_ha") or 1500.0))
        self.season_info.setText(T.get(
            "rotation.season_fmt",
            s=pasture.get('grazing_season_start', '05-01'),
            e=pasture.get('grazing_season_end', '10-01'),
            a=float(pasture.get('area_hectares', 0) or 0),
        ))
        self.generate_plan()

    def generate_plan(self):
        if not self.current_pasture:
            return
        p = self.current_pasture
        self.plan = compute_rotation_plan(
            p.get("grazing_season_start", "05-01"),
            p.get("grazing_season_end", "10-01"),
            self.paddock_spin.value(),
            self.rest_spin.value(),
            self.bbhb_spin.value(),
            self.kbhb_spin.value(),
            self.yield_spin.value(),
            float(p.get("area_hectares") or 0.0),
        )
        self.calendar_widget.set_plan(self.plan)
        self._update_summary()
        self._fill_detail_table()

    # ---- Çıktılar ----
    def _create_summary_card(self, title, value):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #C6DBC1;
                border-radius: 8px; padding: 8px 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet("font-size: 11px; color: #5C7164; font-weight: bold;")
        v = QLabel(value)
        v.setStyleSheet("font-size: 16px; color: #558B2F; font-weight: bold;")
        layout.addWidget(t)
        layout.addWidget(v)
        return card

    def _update_summary(self):
        plan = self.plan
        self._clear_layout(self.summary_layout)
        day_unit = T.get("rotation.day_unit")
        cards = [
            (T.get("rotation.sum_season"), f"{plan['season_days']}{day_unit}"),
            (T.get("rotation.sum_paddocks"), f"{plan['paddock_count']}"),
            (T.get("rotation.sum_ratio"), f"{plan['graze_days']} / {plan['actual_rest_days']}{day_unit}"),
            (T.get("rotation.sum_cycle"), f"{plan['cycle_days']}{day_unit}"),
            (T.get("rotation.sum_herd"), f"{plan['herd_bbhb_total']:,}"),
            (T.get("rotation.sum_area"), f"{plan['paddock_area_ha']:,.0f} Ha"),
        ]
        for title, val in cards:
            self.summary_layout.addWidget(self._create_summary_card(title, val))
        self.summary_layout.addStretch()

    def _fill_detail_table(self):
        plan = self.plan
        n = plan["paddock_count"]
        self.detail_table.setRowCount(n)
        for p in range(1, n + 1):
            color = QColor(PADDOCK_COLORS[(p - 1) % len(PADDOCK_COLORS)])

            b = QTableWidgetItem(T.get("rotation.paddock_fmt", p=p))
            b.setBackground(color)
            b.setForeground(QColor("#081C15") if color.lightness() > 150 else QColor("#FFFFFF"))
            b.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.detail_table.setItem(p - 1, 0, b)

            self.detail_table.setItem(p - 1, 1, QTableWidgetItem(f"{plan['paddock_area_ha']:,.1f}"))

            grazed = plan["grazed_days_per_paddock"][p]
            util = grazed / plan["season_days"] * 100 if plan["season_days"] else 0
            self.detail_table.setItem(p - 1, 2, QTableWidgetItem(
                T.get("rotation.grazed_fmt", g=grazed, u=util)))

            graze_txt = ", ".join(format_interval(iv) for iv in plan["intervals"][p]) or "-"
            self.detail_table.setItem(p - 1, 3, QTableWidgetItem(graze_txt))

            rest_txt = ", ".join(format_interval(iv) for iv in plan["rest_intervals"][p]) or "-"
            self.detail_table.setItem(p - 1, 4, QTableWidgetItem(rest_txt))

    def retranslate(self):
        """Dil değişince parametre etiketlerini, tabları ve takvimi günceller."""
        self.title_label.setText(T.get("rotation.title"))
        self.desc_label.setText(T.get("rotation.desc"))
        self.controls_box.setTitle(T.get("rotation.group_params"))
        self.generate_btn.setText(T.get("rotation.btn_generate"))
        self.paddock_spin.setSuffix(T.get("rotation.suffix_paddock"))
        self.rest_spin.setSuffix(T.get("rotation.suffix_days"))
        self.paddock_spin.setToolTip(T.get("rotation.paddock_tip"))
        self.rest_spin.setToolTip(T.get("rotation.rest_tip"))
        for field, key in [
            (self.pasture_combo, "rotation.lbl_pasture"),
            (self.paddock_spin, "rotation.lbl_paddocks"),
            (self.rest_spin, "rotation.lbl_rest"),
            (self.bbhb_spin, "rotation.lbl_bbhb"),
            (self.kbhb_spin, "rotation.lbl_kbhb"),
            (self.yield_spin, "rotation.lbl_yield"),
        ]:
            lbl = self.rotation_form.labelForField(field)
            if lbl:
                lbl.setText(T.get(key))
        self.tabs.setTabText(0, T.get("rotation.tab_calendar"))
        self.tabs.setTabText(1, T.get("rotation.tab_detail"))
        self.detail_table.setHorizontalHeaderLabels([
            T.get("rotation.h_paddock"), T.get("rotation.h_area"),
            T.get("rotation.h_graze_days"), T.get("rotation.h_graze_iv"),
            T.get("rotation.h_rest_iv"),
        ])
        self.refresh_pastures()
        self.calendar_widget.update()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
