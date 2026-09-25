#!/usr/bin/env python3
"""
MERA-BİS PRO — Veri Denetim ve Kural Göçü komut satırı aracı.

Kullanım:
    python tools/data_report.py report              # kural sürümü + göç + denetim raporu (JSON)
    python tools/data_report.py pre-backup-check   # göçü otomatik çalıştır, sürümü doğrula (JSON)
    python tools/data_report.py migrate            # bekleyen kural göçünü uygula (JSON)

Tüm komutlar JSON çıktı üretir (stdout). Varsayılan veritabanı yerine
belirli bir dosya kullanmak için:  --db YOL

Örnek (bakım betiğinde):
    python tools/data_report.py pre-backup-check --db "C:\\data\\mera.db" > check.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager  # noqa: E402
from database.validation import RULES_VERSION  # noqa: E402


def _emit(result):
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="MERA-BİS PRO veri denetim ve kural göçü raporu."
    )
    parser.add_argument(
        "command",
        choices=["report", "pre-backup-check", "migrate"],
        help="Çalıştırılacak komut",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Veritabanı dosyası yolu (varsayılan: uygulamanın kullandığı veritabanı)",
    )
    args = parser.parse_args()

    db = DatabaseManager(args.db)

    if args.command == "report":
        _emit({
            "command": "report",
            "rule_version": db.get_rule_version(),
            "expected_version": RULES_VERSION,
            "last_migration": db.get_last_migration_info(),
            "audit": db.audit_consistency(),
        })
    elif args.command == "migrate":
        ok = db.ensure_migrated()
        _emit({
            "command": "migrate",
            "ok": ok,
            "rule_version": db.get_rule_version(),
            "expected_version": RULES_VERSION,
            "last_migration": db.get_last_migration_info(),
        })
        sys.exit(0 if ok else 1)
    else:  # pre-backup-check
        result = db.pre_backup_check()
        result["command"] = "pre-backup-check"
        _emit(result)
        sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
