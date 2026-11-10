#!/usr/bin/env bash
# ==============================================================================
# init-primary.sh — Bootstrap PostgreSQL Primary Replication Prerequisites
# ==============================================================================
set -e

echo "[init-primary] Initializing replication user and physical replication slot..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create replication user if not exists
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${POSTGRES_REPLICATION_USER}') THEN
            CREATE ROLE ${POSTGRES_REPLICATION_USER} WITH REPLICATION LOGIN PASSWORD '${POSTGRES_REPLICATION_PASSWORD}';
        END IF;
    END
    \$\$;

    -- Create physical replication slot for standby
    SELECT pg_create_physical_replication_slot('standby_slot')
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_replication_slots WHERE slot_name = 'standby_slot'
    );
EOSQL

echo "[init-primary] Replication user '${POSTGRES_REPLICATION_USER}' and slot 'standby_slot' ready."

