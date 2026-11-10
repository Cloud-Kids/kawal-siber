#!/usr/bin/env bash
# ==============================================================================
# promote-standby.sh — Promote PostgreSQL Standby to Primary Master
# Run this inside the postgres-standby container or via:
# docker exec -it postgres-standby /usr/local/bin/promote-standby.sh
# ==============================================================================
set -e

DATA_DIR="${PGDATA:-/var/lib/postgresql/data/pgdata}"

echo "[promote-standby] Initiating promotion of standby to primary master..."

# Check if standby is currently in recovery mode
IS_IN_RECOVERY=$(psql -U "${POSTGRES_USER:-kawal_user}" -d "${POSTGRES_DB:-kawal_siber}" -t -c "SELECT pg_is_in_recovery();" | xargs)

if [ "$IS_IN_RECOVERY" != "t" ]; then
    echo "[promote-standby] Instance is already running as primary (not in recovery mode)."
    exit 0
fi

echo "[promote-standby] Triggering pg_ctl promote..."
pg_ctl promote -D "$DATA_DIR"

# Wait until standby leaves recovery mode
until [ "$(psql -U "${POSTGRES_USER:-kawal_user}" -d "${POSTGRES_DB:-kawal_siber}" -t -c "SELECT pg_is_in_recovery();" | xargs)" = "f" ]; do
    echo "[promote-standby] Awaiting completion of WAL recovery..."
    sleep 1
done

echo "[promote-standby] SUCCESS: postgres-standby has been promoted to READ-WRITE Primary Master!"
echo "[promote-standby] ACTION REQUIRED: Update application DATABASE_URL or DNS endpoint to point to port 5433 / new master IP."

