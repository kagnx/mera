from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QFrame, QGroupBox, QFormLayout
)

from i18n import T

class CalculatorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        self.title_label = QLabel(T.get("calc.title"))
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #558B2F;")
        main_layout.addWidget(self.title_label)

        self.sub_label = QLabel(T.get("calc.subtitle"))
        self.sub_label.setStyleSheet("color: #5C7164; font-size: 13px;")
        self.sub_label.setWordWrap(True)
        main_layout.addWidget(self.sub_label)

        content_layout = QHBoxLayout()

        # Left Column: Input Form
        self.input_box = QGroupBox(T.get("calc.group_params"))
        form_layout = QFormLayout(self.input_box)
        self.form_layout = form_layout
        form_layout.setSpacing(12)
        input_box = self.input_box

        self.bbhb_spin = QSpinBox()
        self.bbhb_spin.setRange(0, 100000)
        self.bbhb_spin.setValue(150)
        self.bbhb_spin.setSuffix(T.get("calc.suffix_unit"))

        self.kbhb_spin = QSpinBox()
        self.kbhb_spin.setRange(0, 500000)
        self.kbhb_spin.setValue(800)
        self.kbhb_spin.setSuffix(T.get("calc.suffix_unit"))

        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 365)
        self.days_spin.setValue(120)
        self.days_spin.setSuffix(T.get("calc.suffix_days"))

        self.yield_spin = QDoubleSpinBox()
        self.yield_spin.setRange(100.0, 10000.0)
        self.yield_spin.setValue(1800.0)
        self.yield_spin.setSuffix(" Kg/Ha")

        self.area_available_spin = QDoubleSpinBox()
        self.area_available_spin.setRange(0.0, 1000000.0)
        self.area_available_spin.setValue(2500.0)
        self.area_available_spin.setSuffix(" Ha")
        self.area_available_spin.setToolTip(T.get("calc.area_tip"))

        self.calc_btn = QPushButton(T.get("calc.btn_calc"))
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #7CB342; color: #FFFFFF; font-size: 14px; font-weight: bold; border-radius: 8px; padding: 12px;
            }
            QPushButton:hover { background-color: #9CCC65; }
        """)
        self.calc_btn.clicked.connect(self.calculate)

        form_layout.addRow(T.get("calc.lbl_bbhb"), self.bbhb_spin)
        form_layout.addRow(T.get("calc.lbl_kbhb"), self.kbhb_spin)
        form_layout.addRow(T.get("calc.lbl_days"), self.days_spin)
        form_layout.addRow(T.get("calc.lbl_yield"), self.yield_spin)
        form_layout.addRow(T.get("calc.lbl_area"), self.area_available_spin)
        form_layout.addRow(self.calc_btn)

        content_layout.addWidget(input_box, stretch=1)

        # Right Column: Results Display Cards
        self.results_box = QGroupBox(T.get("calc.group_results"))
        res_layout = QVBoxLayout(self.results_box)
        res_layout.setSpacing(12)

        self.card_total_units = self._create_result_card(T.get("calc.card_bbhb"), "0 BBHB")
        self.card_feed_req = self._create_result_card(T.get("calc.card_feed"), "0")
        self.card_area_req = self._create_result_card(T.get("calc.card_area"), "0")
        self.card_area_avail = self._create_result_card(T.get("calc.card_diff"), "0")
        self.card_status = self._create_result_card(T.get("calc.card_status"), "-")

        res_layout.addWidget(self.card_total_units)
        res_layout.addWidget(self.card_feed_req)
        res_layout.addWidget(self.card_area_req)
        res_layout.addWidget(self.card_area_avail)
        res_layout.addWidget(self.card_status)
        res_layout.addStretch()

        content_layout.addWidget(self.results_box, stretch=1)

        main_layout.addLayout(content_layout)

        # Initial calculation
        self.calculate()

    def _create_result_card(self, title, default_val):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #C6DBC1; border-radius: 8px; padding: 10px 14px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; color: #5C7164; font-weight: bold;")
        v_lbl = QLabel(default_val)
        v_lbl.setStyleSheet("font-size: 18px; color: #558B2F; font-weight: bold;")
        v_lbl.setObjectName("valLabel")

        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        return card

    def retranslate(self):
        """Dil değişince statik metinleri ve sonuç kartlarını günceller."""
        self.title_label.setText(T.get("calc.title"))
        self.sub_label.setText(T.get("calc.subtitle"))
        self.input_box.setTitle(T.get("calc.group_params"))
        self.results_box.setTitle(T.get("calc.group_results"))
        self.calc_btn.setText(T.get("calc.btn_calc"))
        self.bbhb_spin.setSuffix(T.get("calc.suffix_unit"))
        self.kbhb_spin.setSuffix(T.get("calc.suffix_unit"))
        self.days_spin.setSuffix(T.get("calc.suffix_days"))
        self.area_available_spin.setToolTip(T.get("calc.area_tip"))
        for field, key in [
            (self.bbhb_spin, "calc.lbl_bbhb"),
            (self.kbhb_spin, "calc.lbl_kbhb"),
            (self.days_spin, "calc.lbl_days"),
            (self.yield_spin, "calc.lbl_yield"),
            (self.area_available_spin, "calc.lbl_area"),
        ]:
            lbl = self.form_layout.labelForField(field)
            if lbl:
                lbl.setText(T.get(key))
        for card, key in [
            (self.card_total_units, "calc.card_bbhb"),
            (self.card_feed_req, "calc.card_feed"),
            (self.card_area_req, "calc.card_area"),
            (self.card_area_avail, "calc.card_diff"),
            (self.card_status, "calc.card_status"),
        ]:
            card.layout().itemAt(0).widget().setText(T.get(key))
        self.calculate()

    def calculate(self):
        bb_count = self.bbhb_spin.value()
        kb_count = self.kbhb_spin.value()
        days = self.days_spin.value()
        yield_per_ha = self.yield_spin.value()
        available_ha = self.area_available_spin.value()

        # Standards:
        # 1 Büyükbaş = 1.0 BBHB (Günlük ~12.5 kg kuru ot tüketimi)
        # 1 Küçükbaş = 0.15 BBHB (Günlük ~2.0 kg kuru ot tüketimi)
        total_bbhb = bb_count * 1.0 + kb_count * 0.15
        daily_feed_kg = total_bbhb * 12.5
        total_feed_kg = daily_feed_kg * days
        total_feed_ton = total_feed_kg / 1000.0

        # Required area (Hectares) = Total Feed Needed (kg) / Yield per Ha (kg/ha)
        req_ha = total_feed_kg / yield_per_ha if yield_per_ha > 0 else 0
        req_dekar = req_ha * 10.0
        diff_ha = available_ha - req_ha

        # Update Card UI
        self.card_total_units.findChild(QLabel, "valLabel").setText(
            T.get("calc.val_bbhb", n=total_bbhb, k=total_bbhb*6.66))
        self.card_feed_req.findChild(QLabel, "valLabel").setText(
            T.get("calc.val_feed", n=total_feed_ton, kg=total_feed_kg))
        self.card_area_req.findChild(QLabel, "valLabel").setText(
            T.get("calc.val_area", n=req_ha, d=req_dekar))
        if diff_ha >= 0:
            self.card_area_avail.findChild(QLabel, "valLabel").setText(
                T.get("calc.val_surplus", n=diff_ha))
        else:
            self.card_area_avail.findChild(QLabel, "valLabel").setText(
                T.get("calc.val_shortfall", n=abs(diff_ha)))

        status_lbl = self.card_status.findChild(QLabel, "valLabel")
        # Yeterlilik durumu: mevcut alan ile ihtiyaç karşılaştırmasına dayanır
        if available_ha >= req_ha:
            status_lbl.setText(T.get("calc.status_ok"))
            status_lbl.setStyleSheet("font-size: 16px; color: #558B2F; font-weight: bold;")
        elif available_ha >= req_ha * 0.6:
            status_lbl.setText(T.get("calc.status_warn"))
            status_lbl.setStyleSheet("font-size: 16px; color: #F59E0B; font-weight: bold;")
        else:
            status_lbl.setText(T.get("calc.status_bad"))
            status_lbl.setStyleSheet("font-size: 16px; color: #EF4444; font-weight: bold;")
