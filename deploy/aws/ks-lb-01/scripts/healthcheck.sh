#!/usr/bin/env bash
# ==============================================================================
# ks-lb-01 Health Check Script
# Verifies nginx-a (port 8081) and nginx-b (port 8082)
# ==============================================================================
set -e

STATUS_A=0
STATUS_B=0

echo "[Load Balancer Health Check] Checking nginx-a (127.0.0.1:8081/nginx-health)..."
if curl -s -f -o /dev/null --max-time 2 http://127.0.0.1:8081/nginx-health; then
    echo "  [OK] nginx-a is healthy and accepting proxy traffic"
    STATUS_A=1
else
    echo "  [FAIL] nginx-a is down or failing healthcheck"
fi

echo "[Load Balancer Health Check] Checking nginx-b (127.0.0.1:8082/nginx-health)..."
if curl -s -f -o /dev/null --max-time 2 http://127.0.0.1:8082/nginx-health; then
    echo "  [OK] nginx-b is healthy and accepting proxy traffic"
    STATUS_B=1
else
    echo "  [FAIL] nginx-b is down or failing healthcheck"
fi

if [ $STATUS_A -eq 1 ] && [ $STATUS_B -eq 1 ]; then
    echo "[Load Balancer Health Check] ALL NGINX PROXIES HEALTHY (2/2 Active)"
    exit 0
elif [ $STATUS_A -eq 1 ] || [ $STATUS_B -eq 1 ]; then
    echo "[Load Balancer Health Check] DEGRADED: 1 proxy active, 1 offline"
    exit 0
else
    echo "[Load Balancer Health Check] CRITICAL: Both Nginx proxy containers are down!"
    exit 1
fi

