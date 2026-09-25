"""
Ortak kodlama ve veri tutarlılığı doğrulama servisi.

Kurallar ve kullanıcı mesajları tek kaynakta toplanır; veritabanı katmanı
(DatabaseManager), arayüz diyaloğu (PastureDialog) ve testlerin TÜMÜ bu
servisi kullanır. Tüm mesajlar MessageCatalog'ta Türkçe/İngilizce olarak
tutulur; dil, çalışma zamanında MessageCatalog.set_language(...) ile değişir.

Toplu denetim: audit_all_records(records) tüm kayıtları kural setine göre
denetler ve rapor üretir (bkz. DatabaseManager.audit_consistency).
"""
import re
from collections import Counter

# Mera kodu biçimi: MRA-<sayı>-<sayı> (örn. MRA-82-01)
CODE_PATTERN = re.compile(r"^MRA-\d+-\d+$", re.IGNORECASE)
# Geriye dönük uyumluluk için Türkçe ipucu sabiti
CODE_FORMAT_HINT = "MRA-XX-XX (örn. MRA-82-01)"

# Kural seti sürümü. Bu sayı yükseltildiğinde mevcut veri, _MIGRATION_STEPS'taki
# karşılık gelen adımlarla otomatik olarak göçürülür (bkz. apply_rule_migrations
# ve DatabaseManager._migrate_rules). Sürüm 0, sürümleme başlamadan önceki
# durumdur; her mevcut kullanıcı veritabanı ilk açılışta 0'dan 1'e göçürülür.
RULES_VERSION = 1


def _step_normalize_codes(record):
    """Göç adımı 1 (0→1): kayıt kodunu mevcut normalizasyon kurallarına göre
    düzeltir (büyük harf + boşluk sadeleştirme). Sürümlemeden önceki sürümlerde
    küçük harf veya boşluklu saklanmış kodlar bu adımla tazelenir."""
    data = dict(record)
    if data.get("code") is not None:
        data["code"] = normalize_code(data["code"])
    return data


# Sürüm → kayıt dönüşümü. Kural değiştiğinde yeni adım eklenir ve
# RULES_VERSION yükseltilir; adımlar sıralı uygulanır (örn. 0→1→2→…).
_MIGRATION_STEPS = {
    1: _step_normalize_codes,
}


def migrate_record(record, to_version=RULES_VERSION):
    """Tek kaydı hedef kural sürümüne göçürür; sürüm adımlarını sırayla uygular.
    Kayıt sözlüğü kopyalanarak döner (orijinal değişmez)."""
    data = dict(record)
    for version in sorted(_MIGRATION_STEPS):
        if version <= to_version:
            data = _MIGRATION_STEPS[version](data)
    return data


def apply_rule_migrations(records, from_version, to_version=RULES_VERSION):
    """Kayıt listesini from_version'dan to_version'a toplu göçürür (veri göçü raporu).

    - records: sözlük listesi (DatabaseManager.get_all_pastures() çıktısı gibi).
    - from_version: veritabanının mevcut kural sürümü (PRAGMA user_version).

    UNIQUE kod çakışması güvenliği: göç sonrası aynı koda düşecek birden fazla
    kayıt varsa (ör. 'mra-01-01' ile 'MRA-01-01' birlikte), bu kayıtlar
    DEĞİŞTİRİLMEZ ve conflicts listesinde raporlanır — kullanıcı denetim
    ekranıyla elle çözer.

    Dönen rapor:
      {
        "from_version": int, "to_version": int,
        "applied_steps": [int, ...],   # uygulanan adım sürümleri
        "total": int, "changed": int,  # değiştirilen kayıt sayısı
        "updates": [{"id": ..., "code": ...}, ...],   # yazılacak güncellemeler
        "conflicts": [{"id": ..., "code": ..., "reason": "duplicate_code"}, ...],
      }
    """
    applied_steps = [
        v for v in sorted(_MIGRATION_STEPS) if from_version < v <= to_version
    ]

    # Göç sonrası hedef kodları say (çakışma denetimi için)
    target_counts = Counter()
    for rec in records:
        code = normalize_code(rec.get("code"))
        if code:
            target_counts[code] += 1

    updates = []
    conflicts = []
    for rec in records:
        new_rec = dict(rec)
        for version in applied_steps:
            new_rec = _MIGRATION_STEPS[version](new_rec)
        raw = "" if rec.get("code") is None else str(rec.get("code"))
        new_code = new_rec.get("code") or ""
        if raw != new_code:
            norm = normalize_code(new_code)
            if norm and target_counts.get(norm, 0) > 1:
                conflicts.append({
                    "id": rec.get("id"),
                    "code": norm,
                    "reason": "duplicate_code",
                })
                continue
            updates.append({"id": rec.get("id"), "code": new_code})

    return {
        "from_version": from_version,
        "to_version": to_version,
        "applied_steps": applied_steps,
        "total": len(records),
        "changed": len(updates),
        "updates": updates,
        "conflicts": conflicts,
    }


class MessageCatalog:
    """Doğrulama servisine ait tüm kullanıcı mesajlarının tek kataloğu (tr/en)."""

    _lang = "tr"
    _messages = {
        "code_empty": {
            "tr": "Mera kodu boş olamaz",
            "en": "Pasture code cannot be empty",
        },
        "code_format": {
            "tr": "Geçerli biçim: {hint}",
            "en": "Valid format: {hint}",
        },
        "code_format_hint": {
            "tr": CODE_FORMAT_HINT,
            "en": "MRA-XX-XX (e.g. MRA-82-01)",
        },
        "code_duplicate": {
            "tr": "'{code}' kodu başka bir mera tarafından kullanılıyor",
            "en": "The code '{code}' is already used by another pasture",
        },
        "code_ok": {
            "tr": "Kod uygun",
            "en": "Code is valid",
        },
        "name_city_duplicate": {
            "tr": "'{name}' adı {city} ilinde başka bir mera tarafından kullanılıyor",
            "en": "The name '{name}' is already used by another pasture in {city}",
        },
        "field_name": {"tr": "Mera Adı", "en": "Pasture Name"},
        "field_city": {"tr": "İl", "en": "City"},
        "field_district": {"tr": "İlçe", "en": "District"},
        "select_city": {"tr": "İl Seçiniz", "en": "Select City"},
        "select_district": {"tr": "İlçe Seçiniz", "en": "Select District"},
        "missing_prefix": {"tr": "eksik: ", "en": "missing: "},
        "problem_name": {"tr": "ad: ", "en": "name: "},
        "problem_code": {"tr": "kod: ", "en": "code: "},
        "form_valid": {
            "tr": "Form geçerli — kaydedebilirsiniz",
            "en": "Form is valid — you can save",
        },
        "mark_ok": {"tr": "✅", "en": "✅"},
        "mark_warn": {"tr": "⚠️", "en": "⚠️"},
        "auto_fix": {
            "tr": "Otomatik düzeltme: {code}",
            "en": "Auto-corrected to: {code}",
        },
        "error_empty_field": {
            "tr": "'{field}' alanı boş",
            "en": "'{field}' field is empty",
        },
    }

    @classmethod
    def set_language(cls, lang):
        """Aktif dili değiştirir ('tr' veya 'en'; diğer değerler 'tr' sayılır)."""
        cls._lang = "en" if lang == "en" else "tr"

    @classmethod
    def get_language(cls):
        return cls._lang

    @classmethod
    def get(cls, key, **kwargs):
        """Aktif dildeki mesajı döndürür; bilinmeyen anahtar kendi adını döndürür."""
        entry = cls._messages.get(key)
        if entry is None:
            return key
        text = entry.get(cls._lang) or entry.get("tr") or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text


def normalize_text(text):
    """Metni normalleştirir: fazla boşlukları sadeleştirir ve büyük harfe çevirir.
    'mera adı ' = 'MERA ADI' sayılır. Türkçe karakterler dahil Unicode güvenlidir."""
    if text is None:
        return ""
    return " ".join(str(text).split()).upper()


def normalize_code(code):
    """Kodu normalleştirir (boşluk + büyük harf). 'mra-01-01 ' = 'MRA-01-01'."""
    return normalize_text(code)


def is_valid_code_format(code):
    """Kod biçim açısından geçerli mi? (MRA-<sayı>-<sayı>)"""
    return bool(CODE_PATTERN.match(normalize_code(code)))


def code_status_message(code, taken_codes=None):
    """Kod denetimi: (ok, message) döndürür.

    - taken_codes: veritabanındaki normalize edilmiş mevcut kod seti veya None.
      None verilirse yalnızca biçim denetimi yapılır (veri erişimi yokken).
    - Mesaj aktif dile göre MessageCatalog'tan çekilir.
    """
    code = normalize_code(code)
    if not code:
        return False, MessageCatalog.get("code_empty")
    if not CODE_PATTERN.match(code):
        hint = MessageCatalog.get("code_format_hint")
        return False, MessageCatalog.get("code_format", hint=hint)
    if taken_codes is not None and code in taken_codes:
        return False, MessageCatalog.get("code_duplicate", code=code)
    return True, MessageCatalog.get("code_ok")


def name_city_status_message(name, city, taken_pairs=None):
    """Aynı ilde aynı ad denetimi: (ok, message) döndürür.

    - taken_pairs: {(norm_ad, norm_il)} seti veya None (yalnızca boşluk/eksik denetimi).
    """
    name_n = normalize_text(name)
    city_n = normalize_text(city)
    if not name_n or not city_n:
        return True, ""
    if taken_pairs is not None and (name_n, city_n) in taken_pairs:
        return False, MessageCatalog.get("name_city_duplicate", name=name, city=city)
    return True, ""


def audit_all_records(records):
    """Tüm kayıtları kural setine göre toplu denetler ve rapor üretir.

    Kayıtlar sözlük listesidir (DatabaseManager.get_all_pastures() çıktısı gibi;
    her kayıtta en az id, code, name, city alanları beklenir). Denetlenen kurallar:
      - kod boş, biçim hatası (CODE_PATTERN), normalleştirilebilir (info),
        kopya kod (aynı normalleştirilmiş kod birden fazla kayıtta)
      - zorunlu alanlar: ad ve il boş olamaz
      - aynı ilde aynı ad (aynı normalleştirilmiş ad+il çifti birden fazla kayıtta)

    Dönen rapor:
      {
        "total": int,            # denetlenen kayıt sayısı
        "ok": int,               # sorunsuz kayıt sayısı
        "with_issues": int,      # en az bir sorunu olan kayıt sayısı
        "issues": [
            {
                "id": ..., "code": norm_kod, "name": ham_ad, "city": ham_il,
                "problems": [ {"severity": "error"|"info", "key": ..., "message": ...}, ... ]
            }, ...
        ],
        "summary": {anahtar: sayı},   # sorun türüne göre toplamlar
        "severity": {"error": n, "info": n},
      }
    Mesajlar aktif dile göre MessageCatalog'tan çekilir.
    """
    normalized = []
    for rec in records:
        code_raw = rec.get("code")
        name_raw = rec.get("name")
        city_raw = rec.get("city")
        normalized.append({
            "id": rec.get("id"),
            "code_raw": "" if code_raw is None else str(code_raw).strip(),
            "code": normalize_code(code_raw),
            "name_raw": "" if name_raw is None else str(name_raw),
            "name": normalize_text(name_raw),
            "city_raw": "" if city_raw is None else str(city_raw),
            "city": normalize_text(city_raw),
        })

    # Normalleştirilmiş anahtarlarla sayaçlar (kopya tespiti için)
    code_counts = Counter(n["code"] for n in normalized if n["code"])
    pair_counts = Counter(
        (n["name"], n["city"]) for n in normalized if n["name"] and n["city"]
    )

    issues = []
    summary = {}
    severity_counts = {"error": 0, "info": 0}
    ok_count = 0

    for n in normalized:
        problems = []

        # --- kod ---
        if not n["code"]:
            problems.append({
                "severity": "error", "key": "code_empty",
                "message": MessageCatalog.get("code_empty"),
            })
        elif not is_valid_code_format(n["code"]):
            hint = MessageCatalog.get("code_format_hint")
            problems.append({
                "severity": "error", "key": "code_format",
                "message": MessageCatalog.get("code_format", hint=hint),
            })
        elif code_counts[n["code"]] > 1:
            problems.append({
                "severity": "error", "key": "code_duplicate",
                "message": MessageCatalog.get("code_duplicate", code=n["code"]),
            })
        if n["code"] and n["code_raw"] != n["code"]:
            # Kayıt normalleştirilmiş biçimde saklanmamışsa düzeltme bildirimi
            problems.append({
                "severity": "info", "key": "code_normalize",
                "message": MessageCatalog.get("auto_fix", code=n["code"]),
            })

        # --- zorunlu alanlar ---
        if not n["name"]:
            problems.append({
                "severity": "error", "key": "name_empty",
                "message": MessageCatalog.get(
                    "error_empty_field", field=MessageCatalog.get("field_name")),
            })
        if not n["city"]:
            problems.append({
                "severity": "error", "key": "city_empty",
                "message": MessageCatalog.get(
                    "error_empty_field", field=MessageCatalog.get("field_city")),
            })

        # --- aynı ilde aynı ad ---
        if n["name"] and n["city"] and pair_counts[(n["name"], n["city"])] > 1:
            problems.append({
                "severity": "error", "key": "name_city_duplicate",
                "message": MessageCatalog.get(
                    "name_city_duplicate", name=n["name_raw"], city=n["city_raw"]),
            })

        if problems:
            issues.append({
                "id": n["id"],
                "code": n["code"],
                "name": n["name_raw"],
                "city": n["city_raw"],
                "problems": problems,
            })
            for p in problems:
                summary[p["key"]] = summary.get(p["key"], 0) + 1
                severity_counts[p["severity"]] += 1
        else:
            ok_count += 1

    return {
        "total": len(records),
        "ok": ok_count,
        "with_issues": len(issues),
        "issues": issues,
        "summary": summary,
        "severity": severity_counts,
    }
