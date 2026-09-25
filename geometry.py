# -*- coding: utf-8 -*-
"""Poligon geometri yardımcıları — shoelace alan hesabı ve tutarlılık denetimi.

JS tarafındaki (assets/map_template.html → polygonAreaHectares) hesapla aynı
küre yaklaşımını kullanır: y = lat·R, x = lng·R·cos(lat0). Böylece popup'taki
anlık alan ile denetim raporundaki alan tutarlıdır.
"""
import json
import logging
import math

LOG = logging.getLogger("merabis.geometry")

EARTH_RADIUS_M = 6371008.8
DEFAULT_THRESHOLD = 0.25  # >%25 sapma = uyumsuz
DEFAULT_MIN_HA = 1.0      # altındaki poligonlar gürültü sayılır (yer tutucu)


def polygon_area_hectares(coords):
    """[lat, lng] listesinden shoelace ile alan (hektar); geçersizse None.

    - coords: [[lat, lng], ...] (kapalı halka şart değil; otomatik kapatılır)
    - En az 3 eşsiz nokta gerekir; sıfır alan (collinear) None döner.
    """
    if not coords or len(coords) < 3:
        return None
    pts = []
    for c in coords:
        try:
            la, ln = float(c[0]), float(c[1])
        except (TypeError, ValueError, IndexError):
            return None
        if not (math.isfinite(la) and math.isfinite(ln)):
            return None
        pts.append((la, ln))
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return None
    k = math.pi / 180.0
    lat0 = sum(p[0] for p in pts) / len(pts)
    cos_lat0 = max(0.05, math.cos(lat0 * k))
    R = EARTH_RADIUS_M
    proj = [(la * k * R, ln * k * R * cos_lat0) for la, ln in pts]
    s = 0.0
    n = len(proj)
    for i in range(n):
        x1, y1 = proj[i]
        x2, y2 = proj[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    ha = abs(s) / 2.0 / 10000.0
    if not math.isfinite(ha) or ha <= 0.0:
        return None
    return ha


def is_seed_template(coords, lat, lng, tol=1e-6):
    """Koordinatlar seed üretecinin yer tutucu şablonuyla birebir eşleşiyor mu?

    Seed üreteci (db_manager._seed_81_provinces_data) her mera için merkez
    (lat, lng) etrafında ±0.02°'lik kare üretir. Kullanıcının elle çizdiği bir
    poligonun kendi merkezine göre bu şablonla köşe köşe eşleşmesi pratikte
    olanaksızdır — eşleşme, poligonun henüz gerçek sınır verisiyle
    değiştirilmediğini gösterir ve denetim dışı bırakılır.
    """
    if not coords or len(coords) != 4 or lat is None or lng is None:
        return False
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    template = [
        (round(lat + 0.02, 4), round(lng - 0.02, 4)),
        (round(lat + 0.02, 4), round(lng + 0.02, 4)),
        (round(lat - 0.02, 4), round(lng + 0.02, 4)),
        (round(lat - 0.02, 4), round(lng - 0.02, 4)),
    ]
    try:
        actual = [(round(float(c[0]), 4), round(float(c[1]), 4)) for c in coords]
    except (TypeError, ValueError, IndexError):
        return False
    return all(
        abs(a[0] - t[0]) <= tol and abs(a[1] - t[1]) <= tol
        for a, t in zip(actual, template)
    )


def load_polygon_coords(raw):
    """polygon_coords_json metnini ayrıştırır; bozuk/boşsa None döner."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, list) and len(data) >= 3 else None


def audit_polygon_consistency(pastures, threshold=DEFAULT_THRESHOLD,
                              min_ha=DEFAULT_MIN_HA):
    """Mera listesinden poligon–kayıtlı alan uyum raporu üretir.

    pastures: get_all_pastures() çıktısı (polygon_coords_json + area_hectares).
    threshold: göreli sapma eşiği (0.25 = >%25 sapma raporlanır).
    min_ha: hesaplanan alanı bu hektarın altındaki poligonlar "yer tutucu"
            sayılır ve denetlenmez (seed/örnek poligonlar raporu doldurmasın).

    Dönüş: {total, checked, placeholder, missing_polygon, deviations,
            worst_pct, threshold}
    """
    total = len(pastures)
    checked = placeholder = missing = 0
    deviations = []
    for p in pastures:
        raw = p.get("polygon_coords_json")
        coords = load_polygon_coords(raw)
        if not coords:
            missing += 1
            continue
        if is_seed_template(coords, p.get("lat"), p.get("lng")):
            placeholder += 1
            continue
        ha = polygon_area_hectares(coords)
        if ha is None:
            missing += 1
            continue
        if ha < min_ha:
            placeholder += 1
            continue
        rec = p.get("area_hectares")
        try:
            rec = float(rec) if rec is not None else None
        except (TypeError, ValueError):
            rec = None
        if rec is None or rec <= 0:
            deviations.append({
                "id": p.get("id"), "code": p.get("code", ""), "name": p.get("name", ""),
                "city": p.get("city", ""), "calc_ha": round(ha, 1), "recorded_ha": None,
                "deviation_pct": None,
                "reason": "missing_area",
            })
            checked += 1
            continue
        checked += 1
        pct = abs(ha - rec) / rec * 100.0
        if pct > threshold * 100.0:
            deviations.append({
                "id": p.get("id"), "code": p.get("code", ""), "name": p.get("name", ""),
                "city": p.get("city", ""),
                "calc_ha": round(ha, 1), "recorded_ha": round(rec, 1),
                "deviation_pct": round(pct, 1),
                "reason": "deviation",
            })
    deviations.sort(key=lambda d: -(d["deviation_pct"] or float("inf")))
    worst = deviations[0]["deviation_pct"] if deviations else 0.0
    return {
        "total": total,
        "checked": checked,
        "placeholder": placeholder,
        "missing_polygon": missing,
        "deviations": deviations,
        "worst_pct": worst,
        "threshold": threshold,
    }
