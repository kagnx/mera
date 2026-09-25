class PistachioTheme:
    # =====================================================================
    # AÇIK (FISTIK YEŞİLİ) TEMA — ana tema
    # Kullanıcı isteği: uygulama genelinde ferah, okunabilir fıstık yeşili
    # arayüz. Koyu temayı sevenler için DARK_STYLE aşağıda korunur.
    # =====================================================================
    LIGHT_STYLE = """
    /* Ana Pencere & Çekirdek Widget'lar */
    QMainWindow, QWidget {
        background-color: #EDF4EA;
        color: #23332A;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        font-size: 13px;
    }

    /* Kaydırma Çubukları */
    QScrollBar:vertical {
        border: none;
        background: #E2EEDC;
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #A8CC96;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #7CB342;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        border: none;
        background: #E2EEDC;
        height: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background: #A8CC96;
        min-width: 20px;
        border-radius: 5px;
    }

    /* Kenar Çubuğu Gezinme Paneli */
    #sidebarFrame {
        background-color: #F4F9F1;
        border-right: 1px solid #C6DBC1;
    }

    #appTitleLabel {
        font-size: 18px;
        font-weight: bold;
        color: #558B2F;
        padding: 10px 5px;
    }

    #appSubtitleLabel {
        font-size: 11px;
        color: #5C7164;
        padding-bottom: 15px;
    }

    /* Gezinme Butonları */
    QPushButton.nav-btn {
        background-color: transparent;
        color: #3D5245;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
    }

    QPushButton.nav-btn:hover {
        background-color: #E4F0DE;
        color: #558B2F;
    }

    QPushButton.nav-btn:checked {
        background-color: #7CB342;
        color: #FFFFFF;
        font-weight: bold;
    }

    /* Birincil & İkincil Butonlar */
    QPushButton.btn-primary {
        background-color: #7CB342;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        font-size: 13px;
    }
    QPushButton.btn-primary:hover {
        background-color: #9CCC65;
    }
    QPushButton.btn-primary:pressed {
        background-color: #689F38;
    }

    QPushButton.btn-secondary {
        background-color: #FFFFFF;
        color: #3D5245;
        border: 1px solid #C6DBC1;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
    }
    QPushButton.btn-secondary:hover {
        background-color: #E7F1E2;
        border-color: #7CB342;
        color: #558B2F;
    }

    QPushButton.btn-danger {
        background-color: #E53935;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
    }
    QPushButton.btn-danger:hover {
        background-color: #C62828;
    }

    /* Girdi Kontrolleri */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
        background-color: #FBFDFA;
        color: #23332A;
        border: 1px solid #C6DBC1;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #7CB342;
        background-color: #FFFFFF;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        color: #23332A;
        selection-background-color: #7CB342;
        selection-color: #FFFFFF;
        border: 1px solid #C6DBC1;
    }

    /* Kartlar ve Grup Kutuları */
    QGroupBox {
        background-color: #FFFFFF;
        border: 1px solid #C6DBC1;
        border-radius: 10px;
        margin-top: 12px;
        padding-top: 15px;
        font-weight: bold;
        color: #558B2F;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 15px;
    }

    .card-widget {
        background-color: #FFFFFF;
        border: 1px solid #C6DBC1;
        border-radius: 12px;
        padding: 15px;
    }

    .metric-value {
        font-size: 26px;
        font-weight: bold;
        color: #558B2F;
    }

    .metric-label {
        font-size: 12px;
        color: #5C7164;
        font-weight: 500;
    }

    /* Tablolar */
    QTableWidget {
        background-color: #FFFFFF;
        color: #23332A;
        gridline-color: #C6DBC1;
        border: 1px solid #C6DBC1;
        border-radius: 8px;
        selection-background-color: #CBE3BC;
        selection-color: #23332A;
    }

    QHeaderView::section {
        background-color: #E7F1E2;
        color: #558B2F;
        font-weight: bold;
        padding: 8px;
        border: none;
        border-bottom: 2px solid #C6DBC1;
    }

    QTableWidget::item {
        padding: 6px;
    }

    QTableWidget::item:alternate {
        background-color: #F6FAF4;
    }

    /* Sekmeler */
    QTabWidget::pane {
        border: 1px solid #C6DBC1;
        border-radius: 8px;
        background-color: #FFFFFF;
    }

    QTabBar::tab {
        background-color: #E7F1E2;
        color: #3D5245;
        border: 1px solid #C6DBC1;
        padding: 8px 18px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
    }

    QTabBar::tab:selected {
        background-color: #7CB342;
        color: #FFFFFF;
        font-weight: bold;
    }

    /* İpuçları */
    QToolTip {
        background-color: #FFFFFF;
        color: #558B2F;
        border: 1px solid #7CB342;
        padding: 6px;
        border-radius: 4px;
    }
    """

    # =====================================================================
    # ESKİ (KOYU) TEMA — geriye dönük referans için korunur
    # =====================================================================
    DARK_STYLE = """
    /* Main Window & Core Widgets */
    QMainWindow, QWidget {
        background-color: #0D1B16;
        color: #ECFDF5;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        font-size: 13px;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: #142520;
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #52B788;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #74C69D;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        border: none;
        background: #142520;
        height: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background: #52B788;
        min-width: 20px;
        border-radius: 5px;
    }

    /* Sidebar Navigation Panel */
    #sidebarFrame {
        background-color: #142520;
        border-right: 1px solid #2A4B3F;
    }

    #appTitleLabel {
        font-size: 18px;
        font-weight: bold;
        color: #52B788;
        padding: 10px 5px;
    }

    #appSubtitleLabel {
        font-size: 11px;
        color: #95D5B2;
        padding-bottom: 15px;
    }

    /* Navigation Buttons */
    QPushButton.nav-btn {
        background-color: transparent;
        color: #A7F3D0;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
    }

    QPushButton.nav-btn:hover {
        background-color: #1F382F;
        color: #52B788;
    }

    QPushButton.nav-btn:checked {
        background-color: #52B788;
        color: #081C15;
        font-weight: bold;
    }

    /* Primary & Secondary Buttons */
    QPushButton.btn-primary {
        background-color: #52B788;
        color: #081C15;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        font-size: 13px;
    }
    QPushButton.btn-primary:hover {
        background-color: #74C69D;
    }
    QPushButton.btn-primary:pressed {
        background-color: #2D6A4F;
        color: #FFFFFF;
    }

    QPushButton.btn-secondary {
        background-color: #1F382F;
        color: #ECFDF5;
        border: 1px solid #2A4B3F;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
    }
    QPushButton.btn-secondary:hover {
        background-color: #2A4B3F;
        border-color: #52B788;
        color: #52B788;
    }

    QPushButton.btn-danger {
        background-color: #EF4444;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
    }
    QPushButton.btn-danger:hover {
        background-color: #DC2626;
    }

    /* Input Controls */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
        background-color: #172A23;
        color: #ECFDF5;
        border: 1px solid #2A4B3F;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #52B788;
        background-color: #1F382F;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox QAbstractItemView {
        background-color: #172A23;
        color: #ECFDF5;
        selection-background-color: #52B788;
        selection-color: #081C15;
        border: 1px solid #2A4B3F;
    }

    /* Cards and GroupBoxes */
    QGroupBox {
        background-color: #142520;
        border: 1px solid #2A4B3F;
        border-radius: 10px;
        margin-top: 12px;
        padding-top: 15px;
        font-weight: bold;
        color: #52B788;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 15px;
    }

    .card-widget {
        background-color: #142520;
        border: 1px solid #2A4B3F;
        border-radius: 12px;
        padding: 15px;
    }

    .metric-value {
        font-size: 26px;
        font-weight: bold;
        color: #52B788;
    }

    .metric-label {
        font-size: 12px;
        color: #95D5B2;
        font-weight: 500;
    }

    /* Tables */
    QTableWidget {
        background-color: #142520;
        color: #ECFDF5;
        gridline-color: #2A4B3F;
        border: 1px solid #2A4B3F;
        border-radius: 8px;
        selection-background-color: #2D6A4F;
        selection-color: #FFFFFF;
    }

    QHeaderView::section {
        background-color: #172A23;
        color: #52B788;
        font-weight: bold;
        padding: 8px;
        border: none;
        border-bottom: 2px solid #2A4B3F;
    }

    QTableWidget::item {
        padding: 6px;
    }

    QTableWidget::item:alternate {
        background-color: #11211C;
    }

    /* Tabs */
    QTabWidget::pane {
        border: 1px solid #2A4B3F;
        border-radius: 8px;
        background-color: #142520;
    }

    QTabBar::tab {
        background-color: #172A23;
        color: #A7F3D0;
        border: 1px solid #2A4B3F;
        padding: 8px 18px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
    }

    QTabBar::tab:selected {
        background-color: #52B788;
        color: #081C15;
        font-weight: bold;
    }

    /* Tooltips */
    QToolTip {
        background-color: #081C15;
        color: #52B788;
        border: 1px solid #52B788;
        padding: 6px;
        border-radius: 4px;
    }
    """
