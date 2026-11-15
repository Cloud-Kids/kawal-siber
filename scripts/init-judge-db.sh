#!/bin/bash
# Initialize judge demo database with synthetic data
# This script creates a fresh judge.db with demo data for the interactive judge demo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JUDGE_DB_PATH="$PROJECT_ROOT/storage/judge/judge.db"
JUDGE_STORAGE_PATH="$PROJECT_ROOT/storage/judge"

# Create judge storage directory if it doesn't exist
mkdir -p "$JUDGE_STORAGE_PATH"
mkdir -p "$JUDGE_STORAGE_PATH/reports"
mkdir -p "$JUDGE_STORAGE_PATH/pcaps"
mkdir -p "$JUDGE_STORAGE_PATH/suricata"

# Remove existing judge.db if it exists (for fresh start)
if [ -f "$JUDGE_DB_PATH" ]; then
    echo "Removing existing judge.db..."
    rm -f "$JUDGE_DB_PATH"
fi

# Set environment variables for judge mode
echo "Initializing judge demo database..."
export KAWAL_JUDGE_MODE=interactive
export DATABASE_URL="sqlite:///$JUDGE_DB_PATH"
export KAWAL_STORAGE_ROOT="$JUDGE_STORAGE_PATH"
export REPORTS_STORAGE_PATH="$JUDGE_STORAGE_PATH/reports"
export PCAP_STORAGE_PATH="$JUDGE_STORAGE_PATH/pcaps"
export SURICATA_STORAGE_PATH="$JUDGE_STORAGE_PATH/suricata"

# Run Alembic migrations to create schema
cd "$PROJECT_ROOT/backend"
echo "Running database migrations..."
alembic upgrade head

# Run judge demo migration to populate synthetic data
echo "Populating synthetic demo data..."
alembic upgrade 0009_judge_demo

echo "Judge demo database initialized successfully at: $JUDGE_DB_PATH"
echo "Storage directory: $JUDGE_STORAGE_PATH"
echo ""
echo "To start the interactive judge demo:"
echo "  docker compose -f deploy/judge-demo/compose.judge-interactive.yaml up -d --build"
