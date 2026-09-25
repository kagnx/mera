"""
Türkiye 81 il ve ilçe verisi (seçim listeleri için).

Veri: assets/turkiye_il_ilce.json (nested: {il: [ilçe, ...]}).
Kaynak: muratgozel/turkey-neighbourhoods (MIT Lisansı — Murat Gözel),
81 il ve 973 ilçe (güncel idari yapı).
Paketlenmiş (PyInstaller) uygulamada varlıklar _MEIPASS/assets içinden yüklenir.
"""
import json
import os
import sys


def _load_data():
    if getattr(sys, "_MEIPASS", None):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "assets", "turkiye_il_ilce.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


PROVINCES_AND_DISTRICTS = _load_data()

# Alfabetik sıralı il adları
PROVINCE_NAMES = sorted(PROVINCES_AND_DISTRICTS.keys())


def get_districts(province):
    """Verilen ile ait ilçe listesini döndürür (bilinmeyen il için boş liste)."""
    return PROVINCES_AND_DISTRICTS.get(province, [])
