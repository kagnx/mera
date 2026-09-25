"""
İzole harita (QtWebEngine) doğrulama betiği — fonksiyonel + görsel (piksel).

Ana smoke testi (smoke_gui.py) bu betiği alt süreç olarak çalıştırır; GPU'suz
ortamlarda Chromium'ın çökmesi ana fonksiyonel takımı etkilemez. Betik kendi
geçici veritabanıyla minimal MainWindow kurar ve iki aşamada doğrular:

1. **Fonksiyonel:** il sınırları katmanı, ray-casting nokta-il eşleştirmesi.
2. **Görsel (piksel):** haritaya gerçek bir popup açılır (pasture-popup CSS
   sınıflarıyla), sayfa QWebEngineView.grab() ile yakalanır ve popup ile üst
   sağ lejant (map-floating-controls) bölgeleri taranır. "Açık temada koyu
   metin garantisi": bölgede koyu metin pikselleri var OLMALI ve zemin
   ağırlıklı açık OLMALI (koyu zemin bloğu olmamalı).

Sonuç, stdout'ta "RESULT_JSON <json>" satırıyla bildirilir; çıkış kodu 0/1.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402,F401
from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtCore import QTimer  # noqa: E402

from database.db_manager import DatabaseManager  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402

FAILURES = []
PASS_COUNT = 0


def check(name, condition, detail=""):
    global PASS_COUNT
    PASS_COUNT += 1
    if condition:
        print(f"  [OK]   {name}", flush=True)
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name} {detail}", flush=True)


# ---- Dil aşaması: buton metinleri setMapLanguage ile değişir mi? ----
LANG_JS = r"""
JSON.stringify((function(){
  if (typeof setMapLanguage !== 'function') return {missing: true};
  setMapLanguage('en');
  var g = function(id){ var el = document.getElementById(id); return el ? el.textContent : null; };
  var out = {
    street: g('lblStreet'),
    provinces: g('lblProvinces'),
    rivers: g('lblRivers'),
    satellite: g('lblSatellite'),
    dark: g('lblDark')
  };
  setMapLanguage('tr');
  return out;
})())
"""

# ---- Menü davranışı: açılma, seçim sonrası otomatik kapanma, rozet ----
MENU_JS = r"""
JSON.stringify((function(){
  var out = {};
  var wrap = document.getElementById('mapMenuWrap');
  var btn = document.getElementById('mapMenuBtn');
  if (!wrap || !btn || typeof pickBaseLayer !== 'function') return {missing: true};
  btn.click();
  out.openAfterClick = wrap.classList.contains('open');
  pickBaseLayer('satellite');
  out.closedAfterPick = !wrap.classList.contains('open');
  out.satelliteActive = document.getElementById('btnSatellite').classList.contains('active');
  out.streetInactive = !document.getElementById('btnStreet').classList.contains('active');
  toggleRivers();
  out.riversActiveAfterToggle = document.getElementById('btnRivers').classList.contains('active');
  var badge = document.getElementById('menuBadge');
  out.badgeAfterRivers = badge ? badge.textContent : null;
  toggleRivers();
  out.riversInactiveAfterSecond = !document.getElementById('btnRivers').classList.contains('active');
  // İl Sınırları varsayılan aktif → kapatınca rozet "1" kalır (gizlenmez)
  out.badgeTextAfterOff = badge ? badge.textContent : null;
  out.badgeStillVisibleAfterOff = badge ? badge.style.display !== 'none' : null;
  pickBaseLayer('street');
  out.streetRestored = document.getElementById('btnStreet').classList.contains('active');
  return out;
})())
"""

# ---- Karanlık mod: aç/kapa + karo filtresi (piksel yakalamadan ÖNCE koşar) ----
DARK_JS = r"""
JSON.stringify((function(){
  var wrap = document.getElementById('mapMenuWrap');
  var btn = document.getElementById('btnDark');
  if (!wrap || !btn || typeof toggleDarkMode !== 'function') return {missing: true};
  toggleDarkMode();
  var dark1 = document.body.classList.contains('dark');
  var pane = document.querySelector('.leaflet-tile-pane');
  var filterDark = pane ? getComputedStyle(pane).filter : null;
  toggleDarkMode();
  var dark2 = document.body.classList.contains('dark');
  // Açık temaya geri dön (açık-mod piksel yakalaması bundan sonra yapılır)
  document.body.classList.remove('dark');
  wrap.classList.remove('open');
  return {
    dark: document.body.classList.contains('dark'),
    toggleOn: dark1 === true,
    toggleOff: dark2 === false,
    tileFilter: filterDark
  };
})())
"""

# ---- Karanlık mod görsel aşaması: koyu temayı etkinleştir, rect'leri al ----
DARK_VISUAL_JS = r"""
JSON.stringify((function(){
  document.body.classList.add('dark');
  var wrap = document.getElementById('mapMenuWrap');
  if (wrap) wrap.classList.add('open');
  function rectOf(sel){
    var el = document.querySelector(sel);
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, height: r.height };
  }
  var pane = document.querySelector('.leaflet-tile-pane');
  var panel = document.querySelector('.map-menu-panel');
  return {
    darkSet: document.body.classList.contains('dark'),
    panelBg: panel ? getComputedStyle(panel).backgroundColor : null,
    tileFilter: pane ? getComputedStyle(pane).filter : null,
    popupRect: rectOf('.leaflet-popup-content-wrapper'),
    controlsRect: rectOf('.map-menu-btn'),
    panelRect: rectOf('.map-menu-panel')
  };
})())
"""

# Grab anında sayfanın gerçek temasını doğrula (enkstrümantasyon)
DARK_VERIFY_JS = r"""
JSON.stringify((function(){
  var panel = document.querySelector('.map-menu-panel');
  var pane = document.querySelector('.leaflet-tile-pane');
  return {
    dark: document.body.classList.contains('dark'),
    panelBg: panel ? getComputedStyle(panel).backgroundColor : null,
    tileFilter: pane ? getComputedStyle(pane).filter : null
  };
})())
"""

# ---- Görsel aşama: popup aç + bölge rect'lerini al ----
# ---- Popup uçtan uca: ilk mera popup'ını aç, poligon alanı + son ölçüm oku ----
POPUP_E2E_JS = r"""
JSON.stringify((function(){
  try {
    if (!window.map || typeof loadPasturesOnMap !== 'function') return {missing: true};
    var data = (typeof currentPasturesData !== 'undefined') ? currentPasturesData : null;
    if (!data || !data.length) return {missing: true, reason: 'no data'};
    var p = data[0];
    var layers = (window.markersGroup && window.markersGroup.getLayers)
                 ? window.markersGroup.getLayers() : [];
    if (!layers.length) return {missing: true, reason: 'no marker'};
    layers[0].openPopup();
    var c = document.querySelector('.leaflet-popup-content');
    if (!c) return {missing: true, reason: 'no popup'};
    var txt = c.innerText || c.textContent || '';
    var secs = c.querySelectorAll('.pasture-popup-section');
    var polySec = secs[0] || null;
    var measSec = secs[1] || null;
    var val = function (sec) {
      if (!sec) return null;
      var v = sec.querySelector('.v');
      if (v) return v.textContent;
      var n = sec.querySelector('.pasture-popup-note');
      return n ? n.textContent : null;
    };
    var out = {
      title: txt.indexOf(String(p.name)) !== -1,
      polyTitle: polySec ? (polySec.textContent || '').toUpperCase().indexOf('POLIGON ALANI') !== -1 : false,
      calcHa: (typeof polygonAreaHectares === 'function')
              ? polygonAreaHectares(p.__polyCoords) : null,
      polyValue: val(polySec),
      measTitle: measSec ? (measSec.textContent || '').toUpperCase().indexOf('SON \u00d6L\u00c7\u00dcM') !== -1 : false,
      measValue: val(measSec),
      gridCells: c.querySelectorAll('.pasture-popup-grid .k').length
    };
    // Sparkline: verim trendi (SVG path + trend oku + uc degerler)
    var spark = c.querySelector('.pasture-popup-spark');
    var spath = c.querySelector('.spark-line');
    var sar = spark ? spark.querySelector('.spark-arrow') : null;
    out.sparkPresent = !!spark;
    out.sparkPoints = spath ? ((spath.getAttribute('d') || '').match(/L/g) || []).length + 1 : 0;
    out.sparkArrowClass = sar ? ((sar.getAttribute('class') || '').match(/spark-arrow (\w+)/) || [])[1] : null;
    out.sparkText = spark ? (spark.textContent || '') : '';
    out.sparkTitle = spark ? (spark.getAttribute('title') || '') : '';
    return out;
  } catch (e) { return {error: String(e)}; }
})())
"""

# ---- Serisiz mera: sparkline OLMAMALI (icerik kimligi dogrulamali yoklama) ----
# Leaflet popup icerigi yeni acilan popupa ayni tick'te oturmuyor; kimlik
# dogrulamasi olmadan onceki popupin icerigi okunur (yanlis pozitif).
POLL2_JS = r"""
(function(){
  try {
    var data = (typeof currentPasturesData !== 'undefined') ? currentPasturesData : null;
    if (!data || data.length < 2) return JSON.stringify({missing: true, reason: 'no data'});
    var p2 = data[1];
    var layers = (window.markersGroup && window.markersGroup.getLayers)
                 ? window.markersGroup.getLayers() : [];
    if (layers.length < 2) return JSON.stringify({missing: true, reason: 'no marker'});
    layers[1].openPopup();
    var c = document.querySelector('.leaflet-popup-content');
    if (!c) return JSON.stringify({settled: false});
    var txt = c.innerText || c.textContent || '';
    if (txt.indexOf(String(p2.name)) === -1) return JSON.stringify({settled: false});
    var secs = c.querySelectorAll('.pasture-popup-section');
    var m2 = secs[1] || null;
    window.map.closePopup();  // sonraki asamaya bayat icerik birakma
    return JSON.stringify({
      settled: true,
      titleMatch: true,
      sparkPresent: !!c.querySelector('.pasture-popup-spark'),
      noMeasNote: m2 ? ((m2.textContent || '').toUpperCase().indexOf('HEN') !== -1) : null
    });
  } catch (e) { return JSON.stringify({error: String(e)}); }
})()
"""

# ---- 'Ölçüm Ekle' düğmesi: açılır mı, JS istek köprüsü tetiklenir mi? ----
ADDMEAS_JS = r"""
JSON.stringify((function(){
  try {
    if (!window.map || typeof loadPasturesOnMap !== 'function') return {missing: true};
    var layers = (window.markersGroup && window.markersGroup.getLayers)
                 ? window.markersGroup.getLayers() : [];
    if (!layers.length) return {missing: true, reason: 'no marker'};
    layers[0].openPopup();
    var c = document.querySelector('.leaflet-popup-content');
    if (!c) return {missing: true, reason: 'no popup'};
    var btn = c.querySelector('.btn-addmeas');
    if (!btn) return {missing: true, reason: 'no button'};
    // Dugmenin KENDI mera id'si onclick'ten okunur — Leaflet icerik gecisdash
    // olsa bile invariant saglanir: istek, tiklanan dugmenin merasina gider
    var m = (btn.getAttribute('onclick') || '').match(/requestAddMeasurement\((\d+)\)/);
    var pid = m ? parseInt(m[1], 10) : null;
    var label = (btn.textContent || '').trim();
    btn.click();
    var req = window.__addMeasRequest;
    window.map.closePopup();
    return { clicked: true, requestSent: (req === pid), pid: pid, labelHasLeaf: label.indexOf('\uD83C\uDF31') !== -1 };
  } catch (e) { return {error: String(e)}; }
})())
"""

VISUAL_JS = r"""
(function(){
  try {
    if (window.map && typeof L !== 'undefined') {
      var opts = { zIndexOffset: 1000 };
      if (typeof pistachioIcon !== 'undefined') opts.icon = pistachioIcon;
      var tm = L.marker([39.0, 35.0], opts).addTo(window.map);
      tm.bindPopup(
        '<div style="min-width:220px;">' +
        '<div class="pasture-popup-title">Test Merası</div>' +
        '<span class="pasture-popup-badge">Ankara / Çankaya</span>' +
        '<div class="pasture-popup-detail">Kod: MRA-01-01<br/>' +
        '<strong>Yüzölçümü:</strong> 1.250 Hektar</div>' +
        '<button class="btn-inspect">\uD83D\uDD0D Detayları İncele</button>' +
        '</div>'
      ).openPopup();
    }
  } catch (e) {}
  function rectOf(sel){
    var el = document.querySelector(sel);
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, height: r.height };
  }
  function cssOf(sel){
    var el = document.querySelector(sel);
    if (!el) return null;
    var cs = getComputedStyle(el);
    return { bg: cs.backgroundColor, color: cs.color };
  }
  return JSON.stringify({
    popupRect: rectOf('.leaflet-popup-content-wrapper'),
    controlsRect: rectOf('.map-menu-btn'),
    panelRect: rectOf('.map-menu-panel'),
    popupCss: cssOf('.leaflet-popup-content-wrapper'),
    controlsCss: cssOf('.map-menu-btn'),
    titleCss: cssOf('.pasture-popup-title'),
    detailCss: cssOf('.pasture-popup-detail'),
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight
  });
})()
"""


def analyze_region(img, rect, sx, sy):
    """Bölgedeki pikselleri karanlık/orta/açık kovalarına ayırır.

    - dark  (lum < 100):  metin glifleri (#23332A detay, #3D5245 buton yazısı)
    - mid   (100-175):    başlık yeşili (#558B2F), rozet/buton zemini (#7CB342)
    - light (lum > 215):  açık zemin (beyaz / #EDF4EA)
    """
    if not rect:
        return {"error": "rect bulunamadı"}
    left = max(0, int(rect["left"] * sx))
    top = max(0, int(rect["top"] * sy))
    right = min(img.width(), int((rect["left"] + rect["width"]) * sx))
    bottom = min(img.height(), int((rect["top"] + rect["height"]) * sy))
    dark = mid = light = total = 0
    for y in range(top, bottom, 2):
        for x in range(left, right, 2):
            c = img.pixelColor(x, y)
            lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
            total += 1
            if lum < 100:
                dark += 1
            elif lum < 175:
                mid += 1
            elif lum > 215:
                light += 1
    return {
        "rect": [left, top, right, bottom],
        "total": total,
        "dark": dark,
        "mid": mid,
        "light": light,
    }


def main():
    app = QApplication(sys.argv)
    db = DatabaseManager(os.path.join(tempfile.mkdtemp(), "map.db"))
    # Popup uçtan uca doğrulaması için ilk meraya 3 ölçüm ekle — sparkline
    # serisi: artan verim trendi 900 -> 1050 -> 1250.4 (ok: yukari)
    db.add_measurement({
        "pasture_id": 1, "m_date": "2026-06-01",
        "dry_hay_yield_kg_per_ha": 900.0, "vegetation_coverage_pct": 60,
        "avg_height_cm": 20, "observer": "Test Gozlemci",
    })
    db.add_measurement({
        "pasture_id": 1, "m_date": "2026-07-01",
        "dry_hay_yield_kg_per_ha": 1050.0, "vegetation_coverage_pct": 64,
        "avg_height_cm": 22, "observer": "Test Gozlemci",
    })
    db.add_measurement({
        "pasture_id": 1, "m_date": "2026-08-15",
        "dry_hay_yield_kg_per_ha": 1250.4, "vegetation_coverage_pct": 68,
        "avg_height_cm": 24.5, "observer": "Test Gozlemci",
    })
    window = MainWindow(db)
    window.resize(1380, 850)
    window.show()

    js_result = {}
    visual = {}

    def _after_js(v):
        try:
            js_result.update(json.loads(v))
        except Exception as exc:
            js_result["_error"] = str(exc)
        # Popup uçtan uca aşaması: ilk mera popup'ı (poligon alanı + son ölçüm)
        window.map_view.web_view.page().runJavaScript(POPUP_E2E_JS, _after_popup_e2e)

    def _after_popup_e2e(v):
        try:
            js_result["popup_e2e"] = json.loads(v)
        except Exception as exc:
            js_result["_error"] = str(exc)
        # Modal tuzağını kırma: gerçek handler'ı ÖNCE sök, test kaydedici bağla.
        # JS tıklaması köprü sinyalini tam yürütür ama modal diyalog
        # app.exec()'i bloklamaz (kuyruk sırası tuzağına karşı).
        try:
            window.map_view.addMeasurementRequested.disconnect(
                window.open_measurement_dialog)
        except TypeError:
            pass

        def _on_addmeas_signal(pid):
            js_result["addmeas_signal_pid"] = pid

        window.map_view.addMeasurementRequested.connect(_on_addmeas_signal)
        _poll2["n"] = 0
        # Serisiz mera aşaması: ikinci popup içerik oturana dek yoklanır
        window.map_view.web_view.page().runJavaScript(POLL2_JS, _poll_second_pasture)

    _poll2 = {"n": 0}

    def _poll_second_pasture(v):
        try:
            data = json.loads(v)
        except Exception as exc:
            data = {"error": str(exc)}
        if data.get("settled") is True or data.get("missing") or data.get("error"):
            js_result["second"] = data
            window.map_view.web_view.page().runJavaScript(ADDMEAS_JS, _after_addmeas)
            return
        _poll2["n"] += 1
        if _poll2["n"] > 25:
            js_result["second"] = {"settled": False, "timeout": True}
            window.map_view.web_view.page().runJavaScript(ADDMEAS_JS, _after_addmeas)
            return
        QTimer.singleShot(150, lambda: window.map_view.web_view.page()
                          .runJavaScript(POLL2_JS, _poll_second_pasture))

    def _after_addmeas(v):
        try:
            js_result["addmeas"] = json.loads(v)
        except Exception as exc:
            js_result["_error"] = str(exc)
        # Dil aşaması: harita butonları İngilizceye geçiyor mu?
        window.map_view.web_view.page().runJavaScript(LANG_JS, _after_lang)

    def _after_lang(v):
        try:
            js_result["map_lang"] = json.loads(v)
        except Exception as exc:
            js_result["_error"] = str(exc)
        # Menü davranışı aşaması: açılma/seçim-sonrası-kapanma/rozet
        window.map_view.web_view.page().runJavaScript(MENU_JS, _after_menu)

    def _after_menu(v):
        try:
            js_result["menu"] = json.loads(v)
        except Exception as exc:
            js_result["_error"] = str(exc)
        # Karanlık mod aşaması: aç/kapa + filtre; karanlıkta kalır
        window.map_view.web_view.page().runJavaScript(DARK_JS, _after_dark)

    def _after_dark(v):
        try:
            js_result["dark"] = json.loads(v)
        except Exception as exc:
            js_result["_error"] = str(exc)
        # Görsel aşama: popup aç + rect'leri al (karanlık modda)
        window.map_view.web_view.page().runJavaScript(VISUAL_JS, _after_visual)

    def _wait_settled(expr, on_ok, tries=25):
        """JS koşulu true olana dek yoklar (render oturması), sonra devam ettirir."""
        state = {"n": 0}

        def _poll(v):
            if str(v) == "true":
                on_ok()
                return
            state["n"] += 1
            if state["n"] > tries:
                on_ok()  # zaman aşımı: yine de dene (analiz raporlar)
                return
            QTimer.singleShot(150, lambda: window.map_view.web_view.page()
                              .runJavaScript(expr, _poll))

        window.map_view.web_view.page().runJavaScript(expr, _poll)

    def _nudge_compositor(on_done, settle_ms=450):
        # Offscreen grab bayat kare döndürebilir → kompozitörü tetiklemek için
        # pencere boyutunu 1 px oynat ve yeniden göster
        sz = window.size()
        window.resize(sz.width() + 2, sz.height() + 2)
        window.hide()
        window.show()
        QTimer.singleShot(settle_ms, on_done)

    def _after_visual(v):
        try:
            visual.update(json.loads(v))
        except Exception as exc:
            visual["_error"] = str(exc)
        # Popup render oturana dek bekle, sonra kompozitörü tetikleyip yakala
        _wait_settled(
            "!!document.querySelector('.leaflet-popup-content-wrapper')",
            lambda: _nudge_compositor(_grab))

    def _grab():
        pm = window.map_view.web_view.grab()
        img = pm.toImage()
        visual["_grab_size"] = [img.width(), img.height()]
        inner_w = visual.get("innerWidth") or 1
        inner_h = visual.get("innerHeight") or 1
        sx = img.width() / inner_w
        sy = img.height() / inner_h
        visual["popup"] = analyze_region(img, visual.get("popupRect"), sx, sy)
        visual["controls"] = analyze_region(img, visual.get("controlsRect"), sx, sy)
        # Açık tema yakalaması bitti → karanlık mod görsel aşaması
        window.map_view.web_view.page().runJavaScript(
            DARK_VISUAL_JS, _after_dark_visual)

    def _after_dark_visual(v):
        try:
            data = json.loads(v)
            visual["dark_rects"] = data
            visual["dark_set_at_add"] = data.get("darkSet")
            visual["panel_bg_at_add"] = data.get("panelBg")
        except Exception as exc:
            visual["dark_rects"] = {"_error": str(exc)}
        # Grab öncesi sayfa durumunu doğrula
        window.map_view.web_view.page().runJavaScript(
            DARK_VERIFY_JS, _after_dark_verify)

    def _dark_settle_expr():
        return ("(function(){ return !!(document.body.classList.contains('dark') "
                "&& document.querySelector('.leaflet-popup-content-wrapper') "
                "&& document.querySelector('.map-menu-panel')); })()")

    def _after_dark_verify(v):
        try:
            visual["dark_state_at_grab"] = json.loads(v)
        except Exception as exc:
            visual["dark_state_at_grab"] = {"_error": str(exc)}
        # Koyu tema render oturana dek bekle → kompozitörü tetikle → yakala
        _wait_settled(_dark_settle_expr(),
                      lambda: _nudge_compositor(_grab_dark, settle_ms=700))

    def _grab_dark():
        pm = window.map_view.web_view.grab()
        img = pm.toImage()
        inner_w = visual.get("innerWidth") or 1
        inner_h = visual.get("innerHeight") or 1
        sx = img.width() / inner_w
        sy = img.height() / inner_h
        dr = visual.get("dark_rects") or {}
        visual["dark_popup"] = analyze_region(img, dr.get("popupRect"), sx, sy)
        visual["dark_controls"] = analyze_region(img, dr.get("controlsRect"), sx, sy)
        visual["dark_panel"] = analyze_region(img, dr.get("panelRect"), sx, sy)
        # Açık temaya geri dön (test sonrası temiz durum)
        window.map_view.web_view.page().runJavaScript(
            "document.body.classList.remove('dark'); 'ok'")
        window.close()
        app.quit()

    def _verify():
        window.map_view.web_view.page().runJavaScript(
            "JSON.stringify({"
            "  built: !!window.provinceFeatureCount,"
            "  count: window.provinceFeatureCount || 0,"
            "  hasLayer: !!(window.provinceLayer && window.map && window.map.hasLayer(window.provinceLayer)),"
            "  fns: (typeof toggleProvinces) + '/' + (typeof toggleSettlements) + '/' + (typeof toggleRivers),"
            "  pane: !!(window.map && window.map.getPane('provincePane')),"
            "  geo: (function(){"
            "    var tests = ["
            "      {lng:32.859, lat:39.933, expect:'Ankara'},"
            "      {lng:28.978, lat:41.008, expect:'İstanbul'},"
            "      {lng:32.484, lat:37.872, expect:'Konya'}"
            "    ];"
            "    var out = [];"
            "    tests.forEach(function(t){"
            "      var found = null;"
            "      window.provinceLayer.eachLayer(function(layer){"
            "        if (layer.feature && layer.feature.geometry && pointInPolygon([t.lng, t.lat], layer.feature.geometry)) found = layer.feature.properties.name;"
            "      });"
            "      out.push({expect: t.expect, found: found});"
            "    });"
            "    return out;"
            "  })()"
            "})",
            _after_js,
        )

    QTimer.singleShot(2500, _verify)
    app.exec()

    # ---- Ölçüm diyaloğu gerçek kayıt denemesi (exec olmadan accept) ----
    try:
        from gui.measurement_dialog import MeasurementDialog  # noqa: E402
        # Popup akisi gibi source='map' (ana pencere aynen boyle acar)
        dlg = MeasurementDialog(None, db, 1, source="map")
        dlg.yield_spin.setValue(1500.0)
        dlg.cover_spin.setValue(70)
        dlg.height_spin.setValue(30)
        dlg.observer_input.setCurrentText("E2E Gozlemci")
        dlg._on_save()
        saved = db.get_measurements(1)  # ASC: en guncel kayit sondadir
        last = saved[-1] if saved else {}
        js_result["dlg_save"] = {
            "ok": (dlg.result() == MeasurementDialog.DialogCode.Accepted
                   and bool(last) and last.get("observer") == "E2E Gozlemci"),
            "rows": len(saved),
        }
        # Denetim izi: en yeni kayit bu E2E eklemenin izi olmali
        trail = db.get_measurement_audit_log(pasture_id=1)
        top = trail[0] if trail else {}
        js_result["audit_trail"] = {
            "source": top.get("source"), "action": top.get("action"),
            "observer": last.get("observer"),
        }
    except Exception as exc:
        js_result["dlg_save"] = {"ok": False, "error": str(exc)}

    # ---- Rapor ----
    out = dict(js_result)
    out["visual"] = visual
    print("RESULT_JSON " + json.dumps(out, ensure_ascii=False), flush=True)

    if js_result.get("_error"):
        check("harita JS yanıtı çözümlendi", False, js_result["_error"])
    else:
        check("il sınırları GeoJSON yüklendi (81 il)", js_result.get("count") == 81,
              str(js_result.get("count")))
        check("il sınırları katmanı haritada aktif", js_result.get("hasLayer") is True)
        check("il sınırları pane'i oluşturuldu", js_result.get("pane") is True)
        check("katman açma/kapama fonksiyonları tanımlı",
              js_result.get("fns") == "function/function/function",
              str(js_result.get("fns")))
        geo = js_result.get("geo") or []
        geo_ok = all(g.get("found") == g.get("expect") for g in geo)
        check("nokta-il eşleştirme (ray casting) doğru", geo_ok, str(geo))

        # Harita arayüz dili (emoji, alt süreç stdout kodlamasında bozulabilir;
        # bu yüzden yalnızca İngilizce metin kısmı karşılaştırılır)
        ml = js_result.get("map_lang") or {}
        lang_ok = (str(ml.get("street", "")).endswith("Standard Map")
                   and str(ml.get("provinces", "")).endswith("Province Borders")
                   and str(ml.get("rivers", "")).endswith("Rivers")
                   and str(ml.get("satellite", "")).endswith("Google Earth / Satellite"))
        check("harita butonları İngilizceye geçiyor (JS)", lang_ok, str(ml))

        # Kompakt menü davranışı
        menu = js_result.get("menu") or {}
        if menu.get("missing"):
            check("menü JS köprüsü mevcut", False, "menu missing")
        else:
            check("menü düğmesi tıklanınca açılır",
                  menu.get("openAfterClick") is True, str(menu))
            check("temel harita seçimi menüyü kapatır (kullanıcı seçimi)",
                  menu.get("closedAfterPick") is True, str(menu))
            check("seçilen temel harita aktif işaretlenir",
                  menu.get("satelliteActive") is True
                  and menu.get("streetInactive") is True, str(menu))
            check("overlay açma menüyü kapatır + rozet güncellenir",
                  menu.get("riversActiveAfterToggle") is True
                  and menu.get("badgeAfterRivers") == "2", str(menu))
            check("overlay kapatınca rozet İl Sınırları için 1 kalır",
                  menu.get("riversInactiveAfterSecond") is True
                  and menu.get("badgeTextAfterOff") == "1"
                  and menu.get("badgeStillVisibleAfterOff") is True, str(menu))
            check("varsayılan temel haritaya dönüş çalışır",
                  menu.get("streetRestored") is True, str(menu))

        # Popup uçtan uca: poligon alanı + son ölçüm bölümleri
        pe = js_result.get("popup_e2e") or {}
        if pe.get("missing") or pe.get("error"):
            check("popup uçtan uca köprüsü mevcut", False, str(pe))
        else:
            check("popup mera başlığını gösterir", pe.get("title") is True, str(pe))
            ha = pe.get("calcHa")
            # Seed poligonu 0.04x0.04 derece kare: enlem 35-42 araliginda ~1460-1620 ha
            check("shoelace poligon alan makul (seed karesi ~1580 ha)",
                  isinstance(ha, (int, float)) and 1400.0 <= ha <= 1700.0, str(ha))
            pv = str(pe.get("polyValue") or "")
            try:
                pv_num = float(pv.split()[0].replace(".", "").replace(",", "."))
            except (ValueError, IndexError):
                pv_num = None
            check("popup poligon değeri hesapla uyumlu (tr biçim)",
                  pv_num is not None and isinstance(ha, (int, float))
                  and abs(pv_num - round(ha * 10) / 10) < 0.06,
                  f"popup={pv!r} hesap={ha}")
            check("popup'ta SON ÖLÇÜM bölümü var", pe.get("measTitle") is True, str(pe))
            mv = str(pe.get("measValue") or "")
            check("son ölçüm tarihi popup'ta görünüyor", "2026" in mv, mv)
            check("ölçüm grid hücreleri doldu", (pe.get("gridCells") or 0) >= 4,
                  str(pe.get("gridCells")))

            # Sparkline: verim trendi (3 olcumluk artan seri)
            check("sparkline seri >= 2 verimde görünür",
                  pe.get("sparkPresent") is True, str(pe.get("sparkPresent")))
            check("spark nokta sayısı serideki ölçüm sayısı (3)",
                  pe.get("sparkPoints") == 3, str(pe.get("sparkPoints")))
            check("trend oku yukarı (artış serisi)",
                  pe.get("sparkArrowClass") == "up", str(pe.get("sparkArrowClass")))
            st_txt = str(pe.get("sparkText") or "")
            check("spark metni uç değerleri içerir (tr biçim)",
                  ("1.250" in st_txt and "kg/ha" in st_txt),
                  "metin-uzunluk:" + str(len(st_txt)))
            check("spark tooltip başlığı tr etiketli",
                  ("Verim" in str(pe.get("sparkTitle") or "")),
                  str(pe.get("sparkTitle") is not None))
            sec2 = js_result.get("second") or {}
            if sec2.get("settled") is not True:
                check("serisiz mera popup icerigi oturdu", False, str(sec2))
            else:
                check("serisiz mera popup icerigi oturdu", True)
                check("serisiz merada sparkline yok",
                      sec2.get("sparkPresent") is False, str(sec2.get("sparkPresent")))

        # 'Ölçüm Ekle' düğmesi: JS tıklaması köprü isteğini tetikledi mi?
        am = js_result.get("addmeas") or {}
        if am.get("missing") or am.get("error"):
            check("'Ölçüm Ekle' düğmesi köprüsü mevcut", False, str(am))
        else:
            check("'Ölçüm Ekle' düğmesi popup'ta görünüyor",
                  am.get("clicked") is True, str(am))
            check("düğme tıklaması köprü isteği gönderdi",
                  am.get("requestSent") is True, str(am))
            check("köprü sinyali Qt tarafına ulaştı",
                  js_result.get("addmeas_signal_pid") == am.get("pid"),
                  str(js_result.get("addmeas_signal_pid")))

        # Ölçüm diyaloğu gerçek kayıt (uçtan uca)
        dsv = js_result.get("dlg_save") or {}
        check("ölçüm diyaloğu gerçek kayıt yapıyor", dsv.get("ok") is True, str(dsv))

        # Denetim izi: harita kaynağı ekleme kaydı
        at = js_result.get("audit_trail") or {}
        check("denetim izi: map kaynağıyla ekleme",
              at.get("source") == "map" and at.get("action") == "add", str(at))

        # Karanlık mod (JS durumu)
        dark = js_result.get("dark") or {}
        if dark.get("missing"):
            check("karanlık mod JS köprüsü mevcut", False, "dark missing")
        else:
            check("karanlık mod toggle açılıyor/kapanıyor",
                  dark.get("toggleOn") is True and dark.get("toggleOff") is True,
                  str(dark))
            check("karo filtresi etkin (invert+hue-rotate)",
                  bool(dark.get("tileFilter")) and "invert" in str(dark.get("tileFilter"))
                  and "hue-rotate" in str(dark.get("tileFilter")),
                  str(dark.get("tileFilter")))

    # ---- Görsel (piksel) kontrolleri ----
    popup = visual.get("popup") or {}
    controls = visual.get("controls") or {}

    def _light_dominant(st):
        return st.get("total", 0) > 0 and st.get("light", 0) / st["total"] >= 0.40

    def _no_dark_bg(st):
        return st.get("total", 0) > 0 and st.get("dark", 0) / st["total"] < 0.20

    if visual.get("_error"):
        check("görsel analiz çözümlendi", False, str(visual.get("_error")))
    else:
        check("popup rect'i bulundu", popup.get("total", 0) > 0, str(popup))
        check("popup: açık zeminde koyu metin (piksel)",
              popup.get("dark", 0) >= 20 and popup.get("mid", 0) >= 25
              and _light_dominant(popup),
              str(popup))
        check("popup: koyu zemin bloğu yok", _no_dark_bg(popup), str(popup))
        check("lejant rect'i bulundu", controls.get("total", 0) > 0, str(controls))
        check("lejant: açık zeminde koyu metin (piksel)",
              controls.get("dark", 0) >= 10 and _light_dominant(controls),
              str(controls))
        check("lejant: koyu zemin bloğu yok", _no_dark_bg(controls), str(controls))

        # ---- Karanlık mod piksel kontrolleri (koyu zemin + açık metin) ----
        dp = visual.get("dark_popup") or {}
        dc = visual.get("dark_controls") or {}
        dpanel = visual.get("dark_panel") or {}

        def _dark_dominant(st):
            return st.get("total", 0) > 0 and st.get("dark", 0) / st["total"] >= 0.40

        def _no_light_bg(st):
            return st.get("total", 0) > 0 and st.get("light", 0) / st["total"] < 0.20

        if dp.get("total", 0) > 0:
            check("karanlık popup: koyu zemin bloğu (piksel)",
                  _dark_dominant(dp) and _no_light_bg(dp), str(dp))
            check("karanlık popup: açık metin glifleri okunur",
                  dp.get("light", 0) >= 15, str(dp))
        else:
            check("karanlık popup yakalaması", False, str(dp))
        if dc.get("total", 0) > 0:
            check("karanlık menü düğmesi: koyu zemin + açık metin",
                  _dark_dominant(dc) and dc.get("light", 0) >= 5, str(dc))
        else:
            check("karanlık menü düğmesi yakalaması", False, str(dc))
        if dpanel.get("total", 0) > 0:
            check("karanlık menü paneli: koyu zemin + açık metin",
                  _dark_dominant(dpanel) and dpanel.get("light", 0) >= 15,
                  str(dpanel))
        else:
            check("karanlık menü paneli yakalaması", False, str(dpanel))

    passed = PASS_COUNT - len(FAILURES)
    print(f"SONUC: {passed}/{PASS_COUNT} kontrol, {len(FAILURES)} basarisiz", flush=True)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
