"""
Rotasyonlu otlatma planı hesaplayıcısı (saf Python, Qt bağımlılığı yok).

Mantık:
- Otlatma sezonu (grazing_season_start/end) MM-DD biçiminde verilir.
- Mera N bölmeye ayrılır.
- Her bölme bir döngüde G gün otlatılır, ardından (N-1)*G gün dinlendirilir.
- G, istenen dinlenme süresini (R gün) karşılayacak şekilde yukarı yuvarlanır:
      G = ceil(R / (N-1))   =>   gerçek dinlenme (N-1)*G >= R olur.
- Günlük program: gün indeksi i için bölme = (i // G) % N + 1 (ardışık döngüler).
"""
import math
from datetime import date, timedelta

# MM-DD biçimindeki tarihleri tam tarihe çevirmek için kullanılan takvim yılı
# (gün/ay bilgisi önemli, yıl görsel takvim için sabittir)
GRAZING_YEAR = 2026

DAILY_FEED_KG_PER_BBHB = 12.5   # 1 BBHB'nin günlük kuru ot tüketimi (kg)
KBHB_TO_BBHB = 0.15             # 1 küçükbaş = 0.15 BBHB


def parse_season(value, default="05-01"):
    """'MM-DD' metnini date'e çevirir; geçersizse varsayılanı kullanır."""
    try:
        parts = str(value).split("-")
        month = int(parts[0])
        day = int(parts[1]) if len(parts) > 1 else 1
        return date(GRAZING_YEAR, month, day)
    except (ValueError, TypeError, IndexError):
        m, d = default.split("-")
        return date(GRAZING_YEAR, int(m), int(d))


def season_days(start_str, end_str):
    """Sezon başlangıç/bitiş tarihlerini ve toplam gün sayısını döndürür."""
    start = parse_season(start_str)
    end = parse_season(end_str)
    if end < start:  # yıl dönümü güvencesi (örn. 11-15 -> 03-01)
        end = date(end.year + 1, end.month, end.day)
    return start, end, (end - start).days + 1


def compute_rotation_plan(start_str, end_str, paddock_count, rest_days,
                          herd_bbhb, herd_kbhb, yield_kg_per_ha, total_area_ha):
    """Rotasyonlu otlatma planını hesaplar ve ayrıntılı sözlük döndürür."""
    start, end, total = season_days(start_str, end_str)
    n = max(1, int(paddock_count))
    r = max(0, int(rest_days))

    # Bir döngüde her bölmenin otlatılacağı gün sayısı (dinlenme garantisiyle)
    graze_days = 1
    if n > 1 and r > 0:
        graze_days = max(1, math.ceil(r / (n - 1)))
    cycle_days = n * graze_days
    actual_rest = (n - 1) * graze_days if n > 1 else 0

    # Günlük program: hangi bölme hangi gün otlatılıyor
    schedule = []  # [(date, paddock_index_1_based)]
    for i in range(total):
        paddock = (i // graze_days) % n + 1
        schedule.append((start + timedelta(days=i), paddock))

    # Bölme bazlı kesintisiz otlatma aralıkları
    intervals = {p: [] for p in range(1, n + 1)}
    current = None
    for d, p in schedule:
        if current and current["paddock"] == p and d == current["end"] + timedelta(days=1):
            current["end"] = d
            current["days"] += 1
        else:
            current = {"paddock": p, "start": d, "end": d, "days": 1}
            intervals[p].append(current)

    # Bölme bazlı dinlenme aralıkları (otlatmalar arası boşluklar)
    rest_intervals = {}
    for p in range(1, n + 1):
        rests = []
        ivs = intervals[p]
        for a, b in zip(ivs, ivs[1:]):
            gap_start = a["end"] + timedelta(days=1)
            gap_end = b["start"] - timedelta(days=1)
            days = (gap_end - gap_start).days + 1
            if days > 0:
                rests.append({"start": gap_start, "end": gap_end, "days": days})
        rest_intervals[p] = rests

    grazed_days_per_paddock = {p: sum(iv["days"] for iv in intervals[p]) for p in intervals}
    full_cycles = total // cycle_days
    partial = total % cycle_days != 0

    # Hayvan ve yem metrikleri
    herd_bbhb_total = herd_bbhb + herd_kbhb * KBHB_TO_BBHB
    daily_demand_kg = herd_bbhb_total * DAILY_FEED_KG_PER_BBHB
    paddock_area_ha = total_area_ha / n if n else 0.0
    required_area_per_paddock = (daily_demand_kg * graze_days) / yield_kg_per_ha if yield_kg_per_ha > 0 else 0.0

    return {
        "season_start": start,
        "season_end": end,
        "season_days": total,
        "paddock_count": n,
        "rest_days": r,
        "graze_days": graze_days,
        "actual_rest_days": actual_rest,
        "cycle_days": cycle_days,
        "full_cycles": full_cycles,
        "partial_cycle": partial,
        "schedule": schedule,
        "schedule_map": {d: p for d, p in schedule},
        "intervals": intervals,
        "rest_intervals": rest_intervals,
        "grazed_days_per_paddock": grazed_days_per_paddock,
        "herd_bbhb_total": round(herd_bbhb_total, 1),
        "daily_demand_kg": round(daily_demand_kg, 1),
        "paddock_area_ha": round(paddock_area_ha, 1),
        "required_area_per_paddock_ha": round(required_area_per_paddock, 1),
    }


def format_interval(iv):
    """Aralık sözlüğünü '05-May - 12-May (8 gün)' biçiminde metne çevirir (dil duyarlı)."""
    from i18n import T
    months_short = T.get_list("months_short")
    start = f"{iv['start'].day:02d}-{months_short[iv['start'].month - 1]}"
    end = f"{iv['end'].day:02d}-{months_short[iv['end'].month - 1]}"
    if T.get_language() == "en":
        return f"{start} - {end} ({iv['days']} days)"
    return f"{start} - {end} ({iv['days']} gün)"
