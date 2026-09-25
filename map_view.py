import os
import json
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl

LOG = logging.getLogger("merabis.map")


# Haritaya gonderilecek son olcum alanlari (popup 'Son Olcum' blogu besler)
_MEAS_KEYS = ("m_date", "dry_hay_yield_kg_per_ha", "vegetation_coverage_pct",
              "avg_height_cm", "observer")


class PyBridge(QObject):
    mapReadySignal = pyqtSignal()
    pastureSelectedSignal = pyqtSignal(int)
    addMeasurementRequestedSignal = pyqtSignal(int)

    @pyqtSlot()
    def onMapReady(self):
        LOG.info("Harita yüklendi ve hazır")
        self.mapReadySignal.emit()

    @pyqtSlot(int)
    def onPastureSelected(self, pasture_id):
        LOG.debug("Haritada mera seçildi: id=%s", pasture_id)
        self.pastureSelectedSignal.emit(pasture_id)

    @pyqtSlot(int)
    def onAddMeasurementRequested(self, pasture_id):
        LOG.debug("Popup'tan ölçüm ekleme isteği: id=%s", pasture_id)
        self.addMeasurementRequestedSignal.emit(pasture_id)


class MapView(QWidget):
    pastureSelected = pyqtSignal(int)
    addMeasurementRequested = pyqtSignal(int)

    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

        # Configure QWebEngine Settings to allow local/remote resources
        settings = self.web_view.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        self.channel = QWebChannel()
        self.bridge = PyBridge()
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self.bridge.pastureSelectedSignal.connect(self._handle_pasture_selected)
        self.bridge.addMeasurementRequestedSignal.connect(self.addMeasurementRequested)
        self.bridge.mapReadySignal.connect(self._on_map_ready)

        self.map_loaded = False
        self.pending_pastures = None
        self._lang = "tr"

        self._load_html()

    def _load_html(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, "assets", "map_template.html")
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        base_url = QUrl.fromLocalFile(html_path)
        self.web_view.setHtml(html_content, base_url)

    def _on_map_ready(self):
        self.map_loaded = True
        self._apply_language()
        self._inject_province_boundaries()
        if self.pending_pastures:
            self._send_map_payload()
            self.pending_pastures = None

    def _latest_measurements_for_map(self):
        """Mera basina en guncel olcumu tek sorguda dondurur: {pasture_id: {...}}.

        latest_measurement() ile ayni siralama (m_date DESC, id DESC) — her mera
        icin ayri sorgu yerine pencere fonksiyonuyla tek tur (N+1 yok).
        """
        if self.db_manager is None:
            return {}
        try:
            conn = self.db_manager.get_connection()
        except AttributeError:
            return {}
        try:
            rows = conn.execute(
                "SELECT * FROM ("
                "  SELECT m.*, ROW_NUMBER() OVER ("
                "     PARTITION BY pasture_id ORDER BY m_date DESC, id DESC) AS _rn"
                "  FROM vegetation_measurements m"
                ") WHERE _rn = 1"
            ).fetchall()
            out = {}
            for r in rows:
                d = dict(r)
                out[d.get("pasture_id")] = {k: d.get(k) for k in _MEAS_KEYS}
            return out
        except Exception as exc:  # olcum tablosu yoksa harita yine calismali
            LOG.warning("Son olcum verisi alinamadi (popup bu blogu gostermez): %s", exc)
            return {}
        finally:
            conn.close()

    def _yield_history_for_map(self, window=6):
        """Mera basina son N verim olcumunu (ASC) tek sorguda dondurur.

        Donus: {pasture_id: [kg/ha, ...]} — popup sparkline'ini besler.
        Ustel siralama get_measurements ile ayni (m_date, id); pencere
        fonksiyonuyla her mera icin son N kayit tek turda secilir.
        """
        if self.db_manager is None:
            return {}
        try:
            conn = self.db_manager.get_connection()
        except AttributeError:
            return {}
        try:
            rows = conn.execute(
                "SELECT pasture_id, dry_hay_yield_kg_per_ha FROM ("
                "  SELECT pasture_id, dry_hay_yield_kg_per_ha,"
                "         ROW_NUMBER() OVER (PARTITION BY pasture_id "
                "         ORDER BY m_date DESC, id DESC) AS _rn"
                "  FROM vegetation_measurements"
                "  WHERE dry_hay_yield_kg_per_ha IS NOT NULL"
                ") WHERE _rn <= ? ORDER BY pasture_id, _rn DESC",
                (int(window),),
            ).fetchall()
            out = {}
            for r in rows:
                out.setdefault(r[0], []).append(r[1])
            return out
        except Exception as exc:
            LOG.warning("Verim serisi alinamadi (sparkline gosterilmez): %s", exc)
            return {}
        finally:
            conn.close()

    def _send_map_payload(self):
        """Bekleyen mera listesine son olcumleri ekleyip haritaya gonderir."""
        if self.pending_pastures is None:
            return
        payload = [dict(p) for p in self.pending_pastures]
        if self.db_manager is not None:
            latest = self._latest_measurements_for_map()
            hist = self._yield_history_for_map()
            if latest:
                for p in payload:
                    m = latest.get(p.get("id"))
                    if m and m.get("m_date"):
                        p["last_measurement"] = m
            if hist:
                for p in payload:
                    series = hist.get(p.get("id"))
                    if series and len(series) >= 2:
                        p["yield_history"] = series
        json_str = json.dumps(payload)
        script = (f"if (typeof loadPasturesOnMap === 'function') {{ "
                  f"loadPasturesOnMap({json_str}); }}")
        self.web_view.page().runJavaScript(script)

    def set_language(self, lang):
        """Harita arayüz dilini değiştirir (butonlar ve popup metinleri)."""
        self._lang = "en" if lang == "en" else "tr"
        self._apply_language()

    def _apply_language(self):
        script = (f"if (typeof setMapLanguage === 'function') {{ "
                  f"setMapLanguage({json.dumps(self._lang)}); }}")
        self.web_view.page().runJavaScript(script)

    def _inject_province_boundaries(self):
        """İl sınırları GeoJSON'unu harita sayfasına aktarır (yerel dosya, çevrimdışı)."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "assets", "turkiye_iller.geojson")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        except OSError:
            return
        script = f"if (typeof setProvinceGeoJSON === 'function') {{ setProvinceGeoJSON({data}); }}"
        self.web_view.page().runJavaScript(script)

    def update_map_data(self, pastures_list):
        self.pending_pastures = pastures_list
        if self.map_loaded:
            self._send_map_payload()
            self.pending_pastures = None

    def reload_map_data(self, pasture_id=None):
        """Harita verisini tazeler; pasture_id verilirse popup'ını yeniden açar.

        Ölçüm diyaloğu kayıttan sonra bunu çağırır: popup'taki 'Son Ölçüm'
        bloğu anında güncellenir ve kullanıcı aynı merada kalır.
        """
        if self.db_manager is None:
            return
        self.update_map_data(self.db_manager.get_all_pastures())
        if pasture_id is not None:
            script = (f"if (typeof openPasturePopup === 'function') {{ "
                      f"openPasturePopup({int(pasture_id)}); }}")
            self.web_view.page().runJavaScript(script)

    def focus_location(self, lat, lng, zoom=12):
        script = f"if (typeof focusPasture === 'function') {{ focusPasture({lat}, {lng}, {zoom}); }}"
        self.web_view.page().runJavaScript(script)

    def _handle_pasture_selected(self, pasture_id):
        self.pastureSelected.emit(pasture_id)
