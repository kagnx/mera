"""Merkezi çeviri (i18n) modülü birim testleri."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from i18n import T  # noqa: E402
from database.validation import MessageCatalog  # noqa: E402
from gui.rotation_planner import format_interval  # noqa: E402
from datetime import date  # noqa: E402

PASS = 0
FAIL = []


def check(name, condition, detail=""):
    global PASS
    PASS += 1
    if condition:
        print(f"  [OK]   {name}")
    else:
        FAIL.append(name)
        print(f"  [FAIL] {name} {detail}")


def main():
    # Varsayılan dil Türkçe
    T.set_language("tr")
    check("varsayılan dil tr", T.get_language() == "tr")

    # Dil değiştirme + MessageCatalog senkronizasyonu
    T.set_language("en")
    check("T dili en", T.get_language() == "en")
    check("MessageCatalog senkronize", MessageCatalog.get_language() == "en")
    T.set_language("tr")
    check("MessageCatalog geri senkronize", MessageCatalog.get_language() == "tr")

    # Bilinmeyen dil 'tr' sayılır
    T.set_language("fr")
    check("bilinmeyen dil tr'e döner", T.get_language() == "tr")
    T.set_language("tr")

    # Katalog eksiksizliği: her anahtarın tr + en değeri dolu
    missing = []
    for key, entry in T._strings.items():
        if not entry.get("tr") or not entry.get("en"):
            missing.append(key)
    check("tüm string anahtarları tr+en dolu", not missing, str(missing))

    # Liste eksiksizliği
    check("ay listesi 12 eleman (tr)", len(T.get_list("months")) == 12)
    T.set_language("en")
    check("ay listesi 12 eleman (en)", len(T.get_list("months")) == 12)
    check("ingilizce Ocak", T.get_list("months")[0] == "January")
    check("hafta günleri 7 (en)", len(T.get_list("weekdays")) == 7)
    T.set_language("tr")
    check("türkçe hafta günü Pzt", T.get_list("weekdays")[0] == "Pzt")

    # Bilinen anahtar çevirisi
    T.set_language("en")
    check("nav.map ingilizce", T.get("nav.map") == "🌍 Map View")
    check("about.title ingilizce", T.get("about.title") == "About - MERA-BIS PRO")
    T.set_language("tr")
    check("nav.map türkçe", T.get("nav.map") == "🌍 Harita Görünümü")

    # Format argümanları
    T.set_language("en")
    v = T.get("calc.val_bbhb", n=270.0, k=1798)
    check("format argümanları (en)", "270.0 BBHB" in v and "equivalent" in v, v)
    check("format anahtarı eksikse güvenli", T.get("sidebar.stats_count", n=5) == "5 Registered Pastures")
    # Eksik format argümanı çökmemeli
    safe = T.get("calc.val_bbhb")
    check("eksik format argümanı çökmez", isinstance(safe, str), safe)

    # Bilinmeyen anahtar kendi adını döndürür
    check("bilinmeyen anahtar", T.get("yok.anahtar") == "yok.anahtar")

    # format_interval dil duyarlı
    iv = {"start": date(2026, 5, 5), "end": date(2026, 5, 12), "days": 8}
    T.set_language("tr")
    check("format_interval tr", format_interval(iv) == "05-May - 12-May (8 gün)", format_interval(iv))
    T.set_language("en")
    check("format_interval en", format_interval(iv) == "05-May - 12-May (8 days)", format_interval(iv))
    T.set_language("tr")

    # Alan adları senkron (diyalog alan adları katalogdan)
    T.set_language("en")
    check("field_name en", MessageCatalog.get("field_name") == "Pasture Name")
    check("select_city en", MessageCatalog.get("select_city") == "Select City")
    T.set_language("tr")
    check("field_name tr", MessageCatalog.get("field_name") == "Mera Adı")

    print(f"\nSONUC: {PASS - len(FAIL)}/{PASS} gecti, {len(FAIL)} basarisiz")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
