from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from i18n import T

class AnalyticsView(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        self.title_label = QLabel(T.get("analytics.title"))
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #558B2F;")
        main_layout.addWidget(self.title_label)

        # Top KPI Cards
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(12)
        main_layout.addLayout(self.kpi_layout)

        # Scroll area for charts grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        charts_container = QWidget()
        self.charts_grid = QGridLayout(charts_container)
        self.charts_grid.setSpacing(15)
        scroll.setWidget(charts_container)

        main_layout.addWidget(scroll)

        self.refresh_analytics()

    def refresh_analytics(self):
        # 1. Refresh KPI Cards
        stats = self.db.get_statistics()

        self._clear_layout(self.kpi_layout)

        kpis = [
            (T.get("analytics.kpi_area"), f"{stats['total_area']:,} Ha",
             T.get("analytics.kpi_area_sub", n=int(stats['total_area']*10))),
            (T.get("analytics.kpi_count"), f"{stats['total_count']}",
             T.get("analytics.kpi_count_sub")),
            (T.get("analytics.kpi_bbhb"), f"{stats['total_bbhb']:,} BBHB",
             T.get("analytics.kpi_bbhb_sub")),
            (T.get("analytics.kpi_kbhb"), f"{stats['total_kbhb']:,} KBHB",
             T.get("analytics.kpi_kbhb_sub"))
        ]

        for title, val, sub in kpis:
            card = self._create_kpi_card(title, val, sub)
            self.kpi_layout.addWidget(card)

        # 2. Refresh Matplotlib Charts
        self._clear_layout(self.charts_grid)

        all_pastures = self.db.get_all_pastures()

        # Chart 1: Region Distribution (Bar)
        fig1 = Figure(figsize=(5, 3.5), facecolor='#FFFFFF')
        ax1 = fig1.add_subplot(111)
        ax1.set_facecolor('#FFFFFF')
        regions = [r['region'] for r in stats['region_stats']]
        areas = [r['total_area'] for r in stats['region_stats']]
        bars = ax1.bar(regions, areas, color='#7CB342', edgecolor='#C6DBC1')
        ax1.set_title(T.get("analytics.chart_region"), color='#558B2F', fontsize=11, fontweight='bold')
        ax1.tick_params(colors='#5C7164', labelsize=8)
        fig1.autofmt_xdate(rotation=25)
        canvas1 = FigureCanvas(fig1)

        # Chart 2: Status Breakdown (Pie)
        fig2 = Figure(figsize=(5, 3.5), facecolor='#FFFFFF')
        ax2 = fig2.add_subplot(111)
        statuses = [s['status'] for s in stats['status_stats']]
        counts = [s['count'] for s in stats['status_stats']]
        colors = ['#7CB342', '#F59E0B', '#EF4444', '#3B82F6']
        ax2.pie(counts, labels=statuses, autopct='%1.1f%%', colors=colors[:len(statuses)],
                textprops={'color': '#23332A', 'fontsize': 9}, startangle=140)
        ax2.set_title(T.get("analytics.chart_status"), color='#558B2F', fontsize=11, fontweight='bold')
        canvas2 = FigureCanvas(fig2)

        # Chart 3: Top Cities (Horizontal Bar)
        fig3 = Figure(figsize=(5, 3.5), facecolor='#FFFFFF')
        ax3 = fig3.add_subplot(111)
        ax3.set_facecolor('#FFFFFF')
        cities = [c['city'] for c in stats['city_stats']][::-1]
        c_areas = [c['total_area'] for c in stats['city_stats']][::-1]
        ax3.barh(cities, c_areas, color='#9CCC65', edgecolor='#C6DBC1')
        ax3.set_title(T.get("analytics.chart_city"), color='#558B2F', fontsize=11, fontweight='bold')
        ax3.tick_params(colors='#5C7164', labelsize=8)
        canvas3 = FigureCanvas(fig3)

        # Chart 4: Elevation vs Yield (Scatter)
        fig4 = Figure(figsize=(5, 3.5), facecolor='#FFFFFF')
        ax4 = fig4.add_subplot(111)
        ax4.set_facecolor('#FFFFFF')
        elevations = [p['elevation_m'] for p in all_pastures if p['elevation_m']]
        yields = [p['dry_hay_yield_kg_per_ha'] for p in all_pastures if p['elevation_m']]
        ax4.scatter(elevations, yields, color='#F59E0B', alpha=0.8, edgecolors='#23332A', s=60)
        ax4.set_title(T.get("analytics.chart_elev"), color='#558B2F', fontsize=11, fontweight='bold')
        ax4.set_xlabel(T.get("analytics.axis_elev"), color='#5C7164', fontsize=8)
        ax4.set_ylabel(T.get("analytics.axis_yield"), color='#5C7164', fontsize=8)
        ax4.tick_params(colors='#5C7164', labelsize=8)
        canvas4 = FigureCanvas(fig4)

        self.charts_grid.addWidget(canvas1, 0, 0)
        self.charts_grid.addWidget(canvas2, 0, 1)
        self.charts_grid.addWidget(canvas3, 1, 0)
        self.charts_grid.addWidget(canvas4, 1, 1)

    def retranslate(self):
        """Dil değişince paneli yeni dille yeniden çizer."""
        self.title_label.setText(T.get("analytics.title"))
        self.refresh_analytics()

    def _create_kpi_card(self, title, value, subtext):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #C6DBC1; border-radius: 10px; padding: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 12px; color: #5C7164; font-weight: bold;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet("font-size: 22px; color: #558B2F; font-weight: bold;")
        lbl_sub = QLabel(subtext)
        lbl_sub.setStyleSheet("font-size: 11px; color: #3E8E63;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_sub)
        return card

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
