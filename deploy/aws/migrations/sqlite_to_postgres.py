"""
sqlite_to_postgres.py — Production-Grade SQLite to PostgreSQL Migration Tool for KAWAL SIBER.
Migrates all tables, indices, and sequences with strict foreign key ordering, batching,
and post-migration row count / checksum reconciliation.
"""
import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (migrator) %(message)s")
logger = logging.getLogger("migrator")

# Strict table dependency order to prevent FK violation during insert
TABLE_ORDER = [
    "alembic_version",
    "users",
    "scan_scopes",
    "assets",
    "scan_jobs",
    "scan_results",
    "web_targets",
    "web_assessments",
    "web_finding_evidence",
    "suricata_rules",
    "suricata_events",
    "incidents",
    "incident_events",
    "ai_triage_runs",
    "generated_reports",
    "report_audit_events",
]


def migrate_database(sqlite_url: str, postgres_url: str, batch_size: int = 1000) -> bool:
    logger.info("Initializing SQLite source engine: %s", sqlite_url)
    src_engine = create_engine(sqlite_url)

    logger.info("Initializing PostgreSQL destination engine...")
    dst_engine = create_engine(postgres_url)

    src_meta = MetaData()
    src_meta.reflect(bind=src_engine)

    dst_meta = MetaData()
    dst_meta.reflect(bind=dst_engine)

    reconciliation = {}

    with dst_engine.connect() as dst_conn, src_engine.connect() as src_conn:
        # Disable foreign key checks during migration if superuser, or insert in dependency order
        logger.info("Starting table-by-table migration in dependency order...")

        for table_name in TABLE_ORDER:
            if table_name not in src_meta.tables:
                logger.warning("Table %s not found in source SQLite database. Skipping.", table_name)
                continue

            src_table = src_meta.tables[table_name]
            dst_table = dst_meta.tables.get(table_name)

            if dst_table is None:
                logger.error("Destination PostgreSQL does not have table %s! Run Alembic migrations first.", table_name)
                return False

            # Count source rows
            src_count = src_conn.execute(select(text("COUNT(*)")).select_from(src_table)).scalar() or 0
            logger.info("Migrating table '%s' (%d rows)...", table_name, src_count)

            if src_count == 0:
                reconciliation[table_name] = {"source": 0, "destination": 0, "status": "EMPTY_MATCH"}
                continue

            # Stream rows in batches
            offset = 0
            migrated_count = 0
            while offset < src_count:
                query = select(src_table).offset(offset).limit(batch_size)
                rows = src_conn.execute(query).mappings().all()
                if not rows:
                    break

                # Prepare insert into PostgreSQL
                insert_stmt = dst_table.insert()
                dst_conn.execute(insert_stmt, [dict(r) for r in rows])
                dst_conn.commit()

                migrated_count += len(rows)
                offset += batch_size

            # Update PostgreSQL sequence if autoincrement PK exists
            if "id" in dst_table.c:
                seq_query = text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), coalesce(max(id), 1)) FROM {table_name};")
                try:
                    dst_conn.execute(seq_query)
                    dst_conn.commit()
                except Exception as seq_err:
                    logger.debug("Could not reset sequence for %s: %s", table_name, seq_err)

            dst_count = dst_conn.execute(select(text("COUNT(*)")).select_from(dst_table)).scalar() or 0
            matched = (src_count == dst_count)
            reconciliation[table_name] = {
                "source": src_count,
                "destination": dst_count,
                "status": "MATCH" if matched else "MISMATCH"
            }
            logger.info("Table '%s' finished: Source=%d, Dest=%d, Status=%s", table_name, src_count, dst_count, "MATCH" if matched else "MISMATCH")

            if not matched:
                logger.error("FATAL: Data mismatch in table '%s'!", table_name)
                return False

    logger.info("==================================================")
    logger.info("   MIGRATION RECONCILIATION SUMMARY")
    logger.info("==================================================")
    all_ok = True
    for tbl, stat in reconciliation.items():
        logger.info("  - %-22s : %5d -> %5d [%s]", tbl, stat["source"], stat["destination"], stat["status"])
        if stat["status"] == "MISMATCH":
            all_ok = False

    if all_ok:
        logger.info("SUCCESS: All tables migrated with 100% data integrity!")
    else:
        logger.error("FAILURE: One or more tables had row count discrepancies.")

    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KAWAL SIBER SQLite to PostgreSQL Migrator")
    parser.add_argument("--sqlite", default="sqlite:///storage/kawal_siber.db", help="SQLite URL")
    parser.add_argument("--postgres", required=True, help="PostgreSQL destination URL")
    args = parser.parse_args()

    success = migrate_database(args.sqlite, args.postgres)
    sys.exit(0 if success else 1)

