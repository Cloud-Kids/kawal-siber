#!/usr/bin/env bash
# ==============================================================================
# ks-tools-01 Health Check Script
# Verifies tools-agent-a (port 9001) and tools-agent-b (port 9002)
# ==============================================================================
set -e

STATUS_A=0
STATUS_B=0

echo "[Tools Agent Health Check] Checking tools-agent-a (127.0.0.1:9001/health)..."
if curl -s -f -o /dev/null --max-time 3 http://127.0.0.1:9001/health; then
    echo "  [OK] tools-agent-a is healthy"
    STATUS_A=1
else
    echo "  [FAIL] tools-agent-a is unreachable"
fi

echo "[Tools Agent Health Check] Checking tools-agent-b (127.0.0.1:9002/health)..."
if curl -s -f -o /dev/null --max-time 3 http://127.0.0.1:9002/health; then
    echo "  [OK] tools-agent-b is healthy"
    STATUS_B=1
else
    echo "  [FAIL] tools-agent-b is unreachable"
fi

if [ $STATUS_A -eq 1 ] && [ $STATUS_B -eq 1 ]; then
    echo "[Tools Agent Health Check] ALL TOOLS AGENTS HEALTHY (2/2 Active)"
    exit 0
elif [ $STATUS_A -eq 1 ] || [ $STATUS_B -eq 1 ]; then
    echo "[Tools Agent Health Check] DEGRADED: 1 agent active, 1 offline"
    exit 0
else
    echo "[Tools Agent Health Check] CRITICAL: Both tools agents are down!"
    exit 1
fi

