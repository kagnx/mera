import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QApplication
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer

from versioning import get_build_info, get_legal_copyright
from i18n import T

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'assets', filename)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T.get("about.title"))
        # NOT: Diyalog içeriğe sığacak kadar geniş olmalı; dar boyut etiketleri
        # sıkıştırıp metinleri tamamen kırpabiliyor (okunamazlık sorunu).
        self.setFixedSize(500, 525)
        self._init_ui()

    def _init_ui(self):
        icon_path = get_asset_path("app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #EDF4EA;
                color: #23332A;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # Card container
        card = QFrame()
        # NOT: QFrame stylesheet'inde 'padding' KULLANMAYIN — Qt, yeterli içerik
        # olduğunda kart içindeki etiketlerin metnini yanlış konumda boyuyor
        # (okunamazlık hatası). İç boşluğu layout margin'i ile verin:
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #C6DBC1;
                border-radius: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # App Logo Icon
        logo_lbl = QLabel()
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        app_name = QLabel("MERA-BİS PRO")
        app_name.setStyleSheet("font-size: 22px; font-weight: bold; color: #558B2F;")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        app_desc = QLabel(T.get("about.desc"))
        app_desc.setStyleSheet("font-size: 13px; color: #5C7164; font-weight: 500;")
        app_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #C6DBC1; background-color: #C6DBC1;")

        # User specified copyright credit text
        credit_line1 = QLabel("Programlayan: kagnx")
        credit_line1.setStyleSheet("font-size: 14px; font-weight: bold; color: #558B2F;")
        credit_line1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        credit_line2 = QLabel(T.get("about.role"))
        credit_line2.setStyleSheet("font-size: 13px; font-weight: 600; color: #689F38;")
        credit_line2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        copyright_lbl = QLabel(T.get("about.copyright"))
        copyright_lbl.setStyleSheet("font-size: 12px; color: #5C7164; margin-top: 5px;")
        copyright_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # İletişim / sosyal medya satırı — tıklanınca ilgili uygulama/tarayıcı açılır
        contact_lbl = QLabel(
            '<a href="mailto:sertkartal@gmail.com">\u2709 sertkartal@gmail.com</a>'
            ' &nbsp;·&nbsp; '
            '<a href="https://www.facebook.com/kagnx">\U0001F4D8 Facebook: kagnx</a>'
            ' &nbsp;·&nbsp; '
            '<a href="https://www.instagram.com/kagnx">\U0001F4F7 Instagram: kagnx</a>'
        )
        contact_lbl.setTextFormat(Qt.TextFormat.RichText)
        contact_lbl.setOpenExternalLinks(True)
        contact_lbl.setStyleSheet("font-size: 12px; color: #5C7164;")
        contact_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sürüm + derleme tarihi (derleme sırasında versioning tarafından yazılır).
        # Sağ tık veya sol tık → sürüm metnini panoya kopyalar (kısa geri bildirimle).
        build_info = get_build_info()
        version_text = T.get("about.version", v=build_info.get('version', '1.0.0'))
        if build_info.get('build_date'):
            version_text += T.get("about.build", d=build_info['build_date'])
        version_lbl = QLabel()
        version_lbl.setTextFormat(Qt.TextFormat.RichText)
        version_lbl.setText(
            '<a href="#copy" style="color:#689F38; text-decoration:none; '
            'font-weight:600; font-size:11px;">' + version_text + '</a>'
        )
        version_lbl.setToolTip(T.get("about.version_copy_hint"))
        version_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def _restore_version_label():
            version_lbl.setText(
                '<a href="#copy" style="color:#689F38; text-decoration:none; '
                'font-weight:600; font-size:11px;">' + version_text + '</a>'
            )

        def _copy_version(*_args):
            QApplication.clipboard().setText(version_text)
            version_lbl.setText(T.get("about.copied"))
            QTimer.singleShot(1500, _restore_version_label)

        version_lbl.linkActivated.connect(_copy_version)
        version_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        version_lbl.customContextMenuRequested.connect(_copy_version)

        # PE sürüm kaynağından LegalCopyright — paketli derlemede exe'nin
        # kendisinden, kaynak modda version_info.txt şablonundan okunur.
        pe_copyright_lbl = QLabel(get_legal_copyright())
        pe_copyright_lbl.setStyleSheet("font-size: 10px; color: #7A8B7F;")
        pe_copyright_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(logo_lbl)
        card_layout.addWidget(app_name)
        card_layout.addWidget(app_desc)
        card_layout.addWidget(divider)
        card_layout.addWidget(credit_line1)
        card_layout.addWidget(credit_line2)
        card_layout.addWidget(copyright_lbl)
        card_layout.addWidget(contact_lbl)
        card_layout.addWidget(version_lbl)
        card_layout.addWidget(pe_copyright_lbl)

        layout.addWidget(card)

        # Close button
        close_btn = QPushButton(T.get("about.btn_close"))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #7CB342; color: #FFFFFF; font-weight: bold; padding: 10px; border-radius: 8px; font-size: 13px;
            }
            QPushButton:hover { background-color: #9CCC65; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
