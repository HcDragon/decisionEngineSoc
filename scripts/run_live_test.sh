#!/usr/bin/env bash
# ==============================================================================
# No-sudo live detection test for the SOC Manager.
# Starts the backend with real NFStream capture, generates real attack-shaped
# traffic, and checks that incidents are raised on the API.
# ==============================================================================
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
API=http://127.0.0.1:8000

echo "[*] Resetting database to a clean seed..."
rm -f soc.db
$PY -m soc.backend.app.db.seed >/dev/null 2>&1

echo "[*] Starting backend (native NFStream capture)..."
$PY -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000 >/tmp/soc_test.log 2>&1 &
UVI=$!
trap 'kill $UVI 2>/dev/null; pkill -9 -f "uvicorn.*8000" 2>/dev/null' EXIT
sleep 6

MODE=$(curl -s $API/api/traffic/status | $PY -c "import sys,json;print(json.load(sys.stdin)['engine_mode'])" 2>/dev/null)
echo "[*] engine_mode = $MODE"

# ---- Test 1: recon (connect-scan to a closed port) --------------------------
echo "[*] TEST 1: recon scan on port 9999"
curl -s -X POST $API/api/traffic/port -H 'Content-Type: application/json' -d '{"port":9999}' >/dev/null
sleep 5
$PY scripts/gen_traffic.py recon --port 9999 --count 80
echo "    waiting for flow expiry..."; sleep 4

# ---- Test 2: flood (packet burst to a built-in sink) ------------------------
echo "[*] TEST 2: dos flood on port 9900"
curl -s -X POST $API/api/traffic/port -H 'Content-Type: application/json' -d '{"port":9900}' >/dev/null
sleep 5
$PY scripts/gen_traffic.py flood --port 9900 --packets 600
echo "    waiting for flow expiry..."; sleep 4

# ---- Results ----------------------------------------------------------------
echo ""
echo "================= RESULTS ================="
$PY - <<'PY'
import json, urllib.request
def get(p): return json.load(urllib.request.urlopen("http://127.0.0.1:8000"+p))
inc = get("/api/incidents")
print("Incidents raised:", inc["count"])
for i in inc["incidents"]:
    d = i["latest_decision"] or {}
    print(f"  #{i['id']} {i['family']:10s} src={i['src_ip']:14s} alerts={i['alert_count']} "
          f"risk={i['max_risk']} tier={d.get('tier')} rule={d.get('rule_id')} mode={d.get('mode')}")
print("Overview stats:", get("/api/dashboard/overview")["stats"])
print("Audit chain   :", get("/api/audit/verify"))
PY
echo "==========================================="
