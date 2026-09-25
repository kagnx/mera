"""
İmza uyarı diyaloğu — imzasız/bozuk paket çalıştırıldığında kullanıcıyı bilgilendirir.

`core/signature_check` sonucuna göre durumu, riski ve öneriyi gösterir;
kullanıcı "Yine de Çalıştır" veya "Çıkış" seçebilir. "Bu oturum için bir daha
gösterme" onayı yalnızca o oturumda geçerlidir (kalıcı susturma yok —
güvenlik uyarısı her başlangıçta tekrar edilebilir kalmalı).
"""
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from i18n import T

LOG = logging.getLogger("merabis.signature")


def _fallback_message(result):
    """core.signature_check import edilemezse durum bazlı yedek mesaj."""
    state = result.get("state", "UnknownError")
    detail = result.get("detail", "")
    key = {
        "NotSigned": "signature.warn.not_signed",
        "HashMismatch": "signature.warn.hash_mismatch",
        "UnknownPlatform": "signature.warn.unknown_platform",
    }.get(state, "signature.warn.generic")
    return {"key": key, "params": {"detail": detail}}


class SignatureWarningDialog(QDialog):
    """İmza denetimi sonucunu gösteren kalıcı (modal) güvenlik diyaloğu."""

    def __init__(self, result, parent=None):
        super().__init__(parent)
        # NOT: QDialog.result() metoduyla çakışmaması için ad check_result
        self.check_result = result
        self.exit_requested = False
        self.suppress_session = False
        self.setWindowTitle(T.get("signature.title"))
        self.setModal(True)
        self.setFixedWidth(520)
        self._init_ui()
        # Tanı: bozuk paket (HashMismatch) uyarıdan fazlasını hak eder
        if self.check_result.get("state") == "HashMismatch":
            LOG.warning("İmza uyumsuzluğu bildirildi: %s", self.check_result.get("detail"))

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #FDF6EC; color: #23332A; }
            QLabel { color: #23332A; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        # Başlık satırı
        title = QLabel("🔐 " + T.get("signature.title"))
        f = QFont()
        f.setBold(True)
        f.setPointSize(12)
        title.setFont(f)
        layout.addWidget(title)

        # Ayraç
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E4D5BC;")
        layout.addWidget(line)

        # Mesaj gövdesi
        msg_info = _fallback_message(self.check_result)
        body = QLabel(T.get(msg_info["key"], **msg_info["params"]))
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(body, 1)

        # Susturma onayı
        self.chk = QCheckBox(T.get("signature.remember_no"))
        layout.addWidget(self.chk)

        # Butonlar
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_exit = QPushButton(T.get("signature.exit_btn"))
        self.btn_exit.clicked.connect(self._on_exit)
        btns.addWidget(self.btn_exit)
        self.btn_run = QPushButton(T.get("signature.continue_btn"))
        self.btn_run.setDefault(True)
        self.btn_run.clicked.connect(self._on_run)
        btns.addWidget(self.btn_run)
        layout.addLayout(btns)

    def _on_exit(self):
        self.exit_requested = True
        self.reject()

    def _on_run(self):
        self.suppress_session = self.chk.isChecked()
        self.accept()
