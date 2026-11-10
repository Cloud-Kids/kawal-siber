#!/usr/bin/env bash
# ==============================================================================
# ks-frontend-01 Health Check Script
# Verifies both frontend-a (port 3001) and frontend-b (port 3002)
# ==============================================================================
set -e

STATUS_A=0
STATUS_B=0

echo "[Frontend Health Check] Checking frontend-a (127.0.0.1:3001)..."
if curl -s -f -o /dev/null --max-time 3 http://127.0.0.1:3001/; then
    echo "  [OK] frontend-a is responding with HTTP 200"
    STATUS_A=1
else
    echo "  [FAIL] frontend-a is NOT responding on port 3001"
fi

echo "[Frontend Health Check] Checking frontend-b (127.0.0.1:3002)..."
if curl -s -f -o /dev/null --max-time 3 http://127.0.0.1:3002/; then
    echo "  [OK] frontend-b is responding with HTTP 200"
    STATUS_B=1
else
    echo "  [FAIL] frontend-b is NOT responding on port 3002"
fi

if [ $STATUS_A -eq 1 ] && [ $STATUS_B -eq 1 ]; then
    echo "[Frontend Health Check] ALL FRONTEND INSTANCES HEALTHY (2/2 Active)"
    exit 0
elif [ $STATUS_A -eq 1 ] || [ $STATUS_B -eq 1 ]; then
    echo "[Frontend Health Check] DEGRADED: 1 instance healthy, 1 instance failed"
    exit 0
else
    echo "[Frontend Health Check] CRITICAL: Both frontend instances are down!"
    exit 1
fi

