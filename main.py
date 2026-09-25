import sys
import os
import logging
import traceback

# Ekran ölçekleme ayarı Qt modülleri yüklenmeden ÖNCE tanımlanmalıdır
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# Add project root directory to python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _setup_logging():
    """Uygulama loglarını kalıcı dosyaya yazar; hatalar logs/ altında birikir."""
    if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
        base_dir = os.environ.get("APPDATA") or os.path.expanduser("~")
        log_dir = os.path.join(base_dir, "MeraBisPro", "logs")
    else:
        log_dir = os.path.join(project_root, "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "merabis.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(log_path, encoding="utf-8"),
                logging.StreamHandler(sys.stderr),
            ],
        )
    except OSError:
        logging.basicConfig(level=logging.INFO)
    return logging.getLogger("merabis")


LOG = _setup_logging()


def _excepthook(exc_type, exc_value, exc_tb):
    """Yakalanmayan tüm istisnaları loglar; GUI çökerse kullanıcıya bildirir."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    LOG.critical("Yakalanmayan istisna:\n%s",
                 "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    try:
        from PyQt6.QtWidgets import QMessageBox
        if QApplication.instance() is not None:
            QMessageBox.critical(
                None, "MERA-BİS PRO",
                "Beklenmeyen bir hata oluştu:\n{}\n\nAyrıntılar log dosyasına yazıldı.".format(exc_value),
            )
    except Exception:
        pass


sys.excepthook = _excepthook


def _acquire_single_instance_lock():
    """Tek örnek kilidi: aynı veritabanı üzerinde paralel açılışı engeller.

    Paketli derlemede kullanıcı veri dizininde, kaynak modda proje dizininde
    kilit dosyası tutar. Kilit alınamazsa None döner.
    """
    import msvcrt
    if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        lock_dir = os.path.join(base, "MeraBisPro")
    else:
        lock_dir = project_root
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, "merabis.lock")
    try:
        # Önce ölü kalıntıları temizle: dosya kilitlenemiyorsa başka örnek açıktır
        if os.path.exists(lock_path):
            try:
                f = open(lock_path, "a+")
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                f.seek(0)
                f.truncate()
                f.write(str(os.getpid()))
                f.flush()
                return f  # kilit bizde
            except OSError:
                try:
                    f.close()
                except Exception:
                    pass
                return None
        f = open(lock_path, "w")
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        f.write(str(os.getpid()))
        f.flush()
        return f
    except OSError:
        return None
    except ImportError:
        return True  # Windows dışı platformlarda kilitsiz devam


# QtWebEngine must be imported before QApplication instance creation
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402,F401
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402
from PyQt6.QtGui import QIcon  # noqa: E402

from database.db_manager import DatabaseManager
from styles.pistachio_theme import PistachioTheme
from gui.main_window import MainWindow


def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    return os.path.join(project_root, 'assets', filename)


def main():
    # Tek örnek kilidi (yalnızca paketli derlemede uygulanır; geliştirmede çoklu
    # açılış denemelerine engel olmamak için kaynak modda kilitsiz kalınır)
    lock_handle = None
    if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
        lock_handle = _acquire_single_instance_lock()
        if lock_handle is None:
            LOG.error("Uygulama zaten açık; ikinci örnek başlatılmadı.")
            app_probe = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.warning(
                None, "MERA-BİS PRO",
                "Uygulama zaten çalışıyor.\nLütfen açık olan pencereyi kullanın."
            )
            return 1

    app = QApplication(sys.argv)
    app.setApplicationName("MERA-BİS PRO")
    app.setOrganizationName("TurkiyeMeraOtomasyonu")
    app.setApplicationVersion(_current_version())
    app.setQuitOnLastWindowClosed(True)

    icon_path = get_asset_path("app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply Pistachio Green Theme (light, fresh interface)
    app.setStyleSheet(PistachioTheme.LIGHT_STYLE)

    # ---- İmza denetimi (yalnızca paketli modda) ----
    # İmzasız/bozuk pakette kullanıcı modal güvenlik uyarısıyla bilgilendirilir;
    # HashMismatch durumunda güçlü öneri ile çıkış istenir.
    _run_signature_gate(app)

    # Initialize Database (şema göçleri + açılış bakımı burada yapılır)
    LOG.info("Veritabanı başlatılıyor...")
    db_manager = DatabaseManager()
    LOG.info("Veritabanı hazır: %s", db_manager.db_path)

    # Bekleyen güncelleme bildirimi (restarter yeni sürüm başlattıysa göster)
    _notify_pending_update()

    # Launch Main Window
    LOG.info("Ana pencere açılıyor (v%s)...", _current_version())
    window = MainWindow(db_manager)
    window.show()

    exit_code = app.exec()

    if lock_handle and lock_handle is not True:
        try:
            import msvcrt
            lock_handle.seek(0)
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            lock_handle.close()
            os.remove(lock_handle.name)
        except OSError:
            pass
    LOG.info("Uygulama kapandı (kod %s)", exit_code)
    return exit_code


def _current_version():
    try:
        from versioning import get_build_info
        return get_build_info().get("version", "1.0.0")
    except Exception:
        return "1.0.0"


def _notify_pending_update():
    """Güncelleme sonrası ilk açılışta kullanıcıya bilgi verir."""
    try:
        from core import update_checker as uc
        info = uc.consume_restart_flag()
        if info.get("updated"):
            LOG.info("Güncelleme sonrası ilk açılış: v%s", info.get("version"))
    except Exception:
        pass


def _run_signature_gate(app):
    """Paketli derlemede Authenticode imzasını denetler; imzasız/bozuk pakette
    modal uyarı gösterir. Kullanıcı 'Çıkış' derse uygulama kapatılır (rc=2).
    Herhangi bir hata durumunda sessizce devam eder (uyarı bir engel değildir;
    erişilebilirlik ilkesi: uyarıyı atlayabilir olmalı).
    """
    try:
        from core import signature_check as sc
        result = sc.check_executable_signature()
        if result.get("signed"):
            LOG.info("İmza denetimi: %s", result.get("state"))
            return
        if result.get("state") == "NotApplicable":
            return  # kaynak modda uyarı yok
        from gui.signature_dialog import SignatureWarningDialog
        dlg = SignatureWarningDialog(result)
        dlg.exec()
        if dlg.suppress_session:
            LOG.info("İmza uyarısı oturum için susturuldu (state=%s)", result.get("state"))
        if dlg.exit_requested:
            LOG.warning("Kullanıcı imza uyarısında çıkışı seçti (state=%s)", result.get("state"))
            sys.exit(2)
        LOG.warning("İmza uyarısıyla devam ediliyor (state=%s)", result.get("state"))
    except SystemExit:
        raise
    except Exception as exc:
        LOG.warning("İmza denetimi atlandı: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
