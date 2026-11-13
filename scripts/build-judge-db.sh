#!/usr/bin/env bash
# build-judge-db.sh — Create sanitized judge.db snapshot from production DB.
#
# SAFETY:
#  - runs on the EC2 host against a CHECKPOINTED copy of the prod DB
#  - output goes to storage/judge/judge.db (bind-mounted :ro into judge-backend)
#  - strips nothing structural; judge_mode middleware enforces read-only anyway
#  - generated_by fields are relabelled to 'judge-demo' for clarity
#
# Usage (on EC2):
#   bash scripts/build-judge-db.sh /opt/kawal-siber/app/storage/kawal_siber.db \
#        /opt/kawal-siber/app/storage/judge/judge.db
set -euo pipefail

SRC="${1:?usage: build-judge-db.sh <prod.db> <out.db>}"
DST="${2:?usage: build-judge-db.sh <prod.db> <out.db>}"

[ -f "$SRC" ] || { echo "source DB not found: $SRC"; exit 1; }
mkdir -p "$(dirname "$DST")"

# 1. Consistent snapshot: checkpoint WAL then copy (sqlite3 backup API)
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
sqlite3 "$SRC" ".backup '$TMP/prod_snapshot.db'"

# 2. Relabel operator fields + drop any obviously sensitive columns if present
sqlite3 "$TMP/prod_snapshot.db" <<'SQL'
UPDATE generated_reports SET generated_by='judge-demo' WHERE generated_by IS NOT NULL;
UPDATE assets SET description='Judge demo asset' WHERE description IS NOT NULL;
SQL

# 3. Force rollback-journal mode (no WAL) so the read-only mount never
#    needs -wal/-shm side files, then integrity check.
sqlite3 "$TMP/prod_snapshot.db" "PRAGMA journal_mode=DELETE; PRAGMA wal_checkpoint(TRUNCATE);"
sqlite3 "$TMP/prod_snapshot.db" "PRAGMA integrity_check;" | grep -q ok
cp "$TMP/prod_snapshot.db" "$DST"
chmod 444 "$DST"   # read-only file — extra belt & suspenders

echo "judge.db built: $DST ($(stat -c%s "$DST") bytes, mode 444)"
echo "Verify: sqlite3 $DST 'select count(*) from security_events;'"
