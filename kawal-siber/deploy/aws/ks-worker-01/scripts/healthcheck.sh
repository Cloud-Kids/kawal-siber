#!/usr/bin/env bash
# ==============================================================================
# ks-worker-01 Health Check Script
# Verifies container processes and heartbeat files for worker-a and worker-b
# ==============================================================================
set -e

STATUS_A=0
STATUS_B=0

echo "[Worker Health Check] Checking worker-a container status..."
if docker exec worker-a python -c "import sys, time, os; t=os.path.getmtime('/tmp/worker_heartbeat') if os.path.exists('/tmp/worker_heartbeat') else 0; sys.exit(0 if (time.time() - t) < 30 else 1)" >/dev/null 2>&1; then
    echo "  [OK] worker-a is running and actively heartbeating"
    STATUS_A=1
else
    echo "  [FAIL] worker-a heartbeat stale or container down"
fi

echo "[Worker Health Check] Checking worker-b container status..."
if docker exec worker-b python -c "import sys, time, os; t=os.path.getmtime('/tmp/worker_heartbeat') if os.path.exists('/tmp/worker_heartbeat') else 0; sys.exit(0 if (time.time() - t) < 30 else 1)" >/dev/null 2>&1; then
    echo "  [OK] worker-b is running and actively heartbeating"
    STATUS_B=1
else
    echo "  [FAIL] worker-b heartbeat stale or container down"
fi

if [ $STATUS_A -eq 1 ] && [ $STATUS_B -eq 1 ]; then
    echo "[Worker Health Check] ALL WORKERS HEALTHY (2/2 Active Concurrent Consumers)"
    exit 0
elif [ $STATUS_A -eq 1 ] || [ $STATUS_B -eq 1 ]; then
    echo "[Worker Health Check] DEGRADED: 1 worker active, 1 offline (queue still served)"
    exit 0
else
    echo "[Worker Health Check] CRITICAL: Both workers are offline! Queue is stalled!"
    exit 1
fi

