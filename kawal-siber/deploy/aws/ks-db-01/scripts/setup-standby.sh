#!/usr/bin/env bash
# ==============================================================================
# setup-standby.sh — Bootstrap and Start PostgreSQL Standby with Streaming Replication
# ==============================================================================
set -e

DATA_DIR="${PGDATA:-/var/lib/postgresql/data/pgdata}"

# Check if data directory already has a valid PostgreSQL cluster
if [ ! -s "$DATA_DIR/PG_VERSION" ]; then
    echo "[setup-standby] No existing cluster found in $DATA_DIR. Bootstrapping via pg_basebackup..."
    mkdir -p "$DATA_DIR"
    chmod 700 "$DATA_DIR"

    echo "[setup-standby] Waiting for postgres-primary ($PRIMARY_HOST:$PRIMARY_PORT) to become healthy..."
    until pg_isready -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$POSTGRES_USER"; do
        echo "[setup-standby] Waiting for primary..."
        sleep 2
    done

    echo "[setup-standby] Executing pg_basebackup from primary..."
    PGPASSWORD="$REPLICATION_PASSWORD" pg_basebackup \
        -h "$PRIMARY_HOST" \
        -p "$PRIMARY_PORT" \
        -D "$DATA_DIR" \
        -U "$REPLICATION_USER" \
        -v \
        -P \
        -R \
        --slot=standby_slot

    echo "[setup-standby] pg_basebackup completed successfully. standby.signal created."
else
    echo "[setup-standby] Existing cluster found in $DATA_DIR. Skipping pg_basebackup."
fi

# Ensure correct permissions
chown -R postgres:postgres "$DATA_DIR"
chmod 700 "$DATA_DIR"

echo "[setup-standby] Starting PostgreSQL Standby server..."
exec docker-ensure-initdb.sh "$@"

