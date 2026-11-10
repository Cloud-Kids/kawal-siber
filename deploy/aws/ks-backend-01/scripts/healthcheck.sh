#!/usr/bin/env bash
# ==============================================================================
# ks-backend-01 Health Check Script
# Verifies both backend-a (port 8001) and backend-b (port 8002)
# ==============================================================================
set -e

STATUS_A=0
STATUS_B=0

echo "[Backend Health Check] Checking backend-a (127.0.0.1:8001/api/v1/health)..."
if curl -s -f -o /dev/null --max-time 3 http://127.0.0.1:8001/api/v1/health; then
    echo "  [OK] backend-a healthy (HTTP 200)"
    STATUS_A=1
else
    echo "  [FAIL] backend-a failed healthcheck"
fi

echo "[Backend Health Check] Checking backend-b (127.0.0.1:8002/api/v1/health)..."
if curl -s -f -o /dev/null --max-time 3 http://127.0.0.1:8002/api/v1/health; then
    echo "  [OK] backend-b healthy (HTTP 200)"
    STATUS_B=1
else
    echo "  [FAIL] backend-b failed healthcheck"
fi

if [ $STATUS_A -eq 1 ] && [ $STATUS_B -eq 1 ]; then
    echo "[Backend Health Check] ALL BACKEND INSTANCES HEALTHY (2/2 Active)"
    exit 0
elif [ $STATUS_A -eq 1 ] || [ $STATUS_B -eq 1 ]; then
    echo "[Backend Health Check] DEGRADED: 1 backend instance active, 1 offline"
    exit 0
else
    echo "[Backend Health Check] CRITICAL: Both backend instances failed!"
    exit 1
fi

