#!/usr/bin/env bash
# ==============================================================================
# check-replication-lag.sh — Monitor PostgreSQL Streaming Replication Lag
# ==============================================================================
set -e

DB_USER="${POSTGRES_USER:-kawal_user}"
DB_NAME="${POSTGRES_DB:-kawal_siber}"

echo "=================================================================="
echo " KAWAL SIBER — PostgreSQL Streaming Replication Lag Monitor"
echo "=================================================================="

# Check if primary is reachable
if pg_isready -h 127.0.0.1 -p 5432 -U "$DB_USER" >/dev/null 2>&1; then
    echo "[PRIMARY STATUS]: Online on port 5432"
    echo "--- Active Replication Slots & Connected Standbys ---"
    psql -h 127.0.0.1 -p 5432 -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT
            client_addr,
            application_name,
            state,
            sync_state,
            sync_priority,
            pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn) AS sent_lag_bytes,
            pg_wal_lsn_diff(pg_current_wal_lsn(), write_lsn) AS write_lag_bytes,
            pg_wal_lsn_diff(pg_current_wal_lsn(), flush_lsn) AS flush_lag_bytes,
            pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes
        FROM pg_stat_replication;
    "
else
    echo "[PRIMARY STATUS]: Offline or unreachable on port 5432!"
fi

echo ""
# Check standby status
if pg_isready -h 127.0.0.1 -p 5433 -U "$DB_USER" >/dev/null 2>&1; then
    echo "[STANDBY STATUS]: Online on port 5433"
    psql -h 127.0.0.1 -p 5433 -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT
            pg_is_in_recovery() AS in_recovery_mode,
            pg_last_wal_receive_lsn() AS last_received_lsn,
            pg_last_wal_replay_lsn() AS last_replayed_lsn,
            round(EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::numeric, 2) AS replay_lag_seconds;
    "
else
    echo "[STANDBY STATUS]: Offline or unreachable on port 5433!"
fi
echo "=================================================================="

