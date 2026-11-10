"""
verify-sqlite-integrity.py — Read-Only Database Integrity & Verification Tool for KAWAL SIBER.
Runs PRAGMA integrity_check, foreign_key_check, and documents file size and mtime
without modifying or locking existing operational records.
"""
import os
import sqlite3
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
DB_PATH = _root / "kawal-siber" / "storage" / "kawal_siber.db"
if not DB_PATH.exists():
    DB_PATH = _root / "storage" / "kawal_siber.db"

def verify_database():
    print(f"=== KAWAL SIBER Database Integrity Check ===")
    print(f"Target Database: {DB_PATH}")

    if not DB_PATH.exists():
        print(f"[ERROR] Database file not found at {DB_PATH}!")
        sys.exit(1)

    stat = DB_PATH.stat()
    print(f"File Size     : {stat.st_size} bytes")
    print(f"Last Modified : {stat.st_mtime}")

    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    cursor = conn.cursor()

    try:
        # 1. Structural integrity check
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchall()
        print(f"\n[PRAGMA integrity_check]")
        for row in integrity:
            print(f"  {row[0]}")
        is_ok = len(integrity) == 1 and integrity[0][0] == "ok"

        # 2. Foreign key violations check
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        print(f"\n[PRAGMA foreign_key_check]")
        if not fk_violations:
            print("  0 violations reported (Empty result).")
        else:
            print(f"  WARNING: {len(fk_violations)} violations found:")
            for row in fk_violations:
                print(f"    {row}")

        # 3. Foreign key enforcement setting
        cursor.execute("PRAGMA foreign_keys;")
        fk_enabled = cursor.fetchone()[0]
        print(f"\n[PRAGMA foreign_keys (Connection default)]")
        print(f"  Enforcement: {'ON (1)' if fk_enabled else 'OFF (0) - Standard SQLite connection default; application sets ON on connect'}")

        # 4. Table record counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        print(f"\n[Table Record Counts]")
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM \"{t}\";")
            count = cursor.fetchone()[0]
            print(f"  - {t:<28}: {count:>5} records")

        print("\n=============================================")
        if is_ok and not fk_violations:
            print("STATUS: DATABASE INTEGRITY FULLY VERIFIED (PASS)")
        else:
            print("STATUS: INTEGRITY ISSUES DETECTED (FAIL)")
        print("=============================================")

    finally:
        conn.close()

if __name__ == "__main__":
    verify_database()
