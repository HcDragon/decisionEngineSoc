#!/usr/bin/env bash
# ==============================================================================
# testlab/start_testlab.sh  (MASTER PRD Phase 3, adapted to the NFStream stack)
# Bring up the lab: namespaces + backend (real nft executor, auto mode,
# capturing veth-def). Self-cleans stale processes and waits for readiness
# with timeouts so it never hangs. Requires root.
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source testlab/lab.env

[ "$(id -u)" -eq 0 ] || { echo "[-] run as root: sudo testlab/start_testlab.sh" >&2; exit 1; }
PY=.venv/bin/python
[ -x "$PY" ] || { echo "[-] venv missing. Run run_linux.sh first." >&2; exit 1; }
START_DASHBOARD="${START_DASHBOARD:-0}"   # default: do NOT start dashboard (avoids hangs)

echo "[0/5] clean stale processes / free port 8000"
pkill -9 -f "uvicorn.*soc.backend.app.main" 2>/dev/null || true
command -v fuser >/dev/null 2>&1 && fuser -k 8000/tcp 2>/dev/null || true
sleep 1

echo "[1/5] namespaces"
testlab/setup_netns.sh >/dev/null
echo "      attacker=$ATTACKER_LAB_IP  defender(host)=$DEFENDER_LAB_IP on $LAB_IFACE"

echo "[2/5] database (SQLite, clean seed)"
rm -f soc.db
$PY -m soc.backend.app.db.seed >/dev/null 2>&1

echo "[3/5] backend — LAB executor + auto mode, capturing $LAB_IFACE"
export TESTLAB_MODE=1 SOC_CAPTURE_IFACE="$LAB_IFACE" SOC_EXECUTOR=lab SOC_LAB_MODE=true \
       AUTOMATION_MODE=auto DATABASE_URL="sqlite:///./soc.db"
$PY -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000 >/tmp/soc_testlab.log 2>&1 &
echo $! > testlab/.backend.pid

# Readiness loop (timeout-bounded — never hang)
READY=0
for _ in $(seq 1 25); do
    if curl -s --max-time 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then READY=1; break; fi
    sleep 1
done
if [ "$READY" != "1" ]; then
    echo "[-] backend did not become ready; see /tmp/soc_testlab.log" >&2
    tail -5 /tmp/soc_testlab.log >&2 || true
    exit 1
fi
MODE=$(curl -s --max-time 3 http://127.0.0.1:8000/api/traffic/status | \
       $PY -c "import sys,json;print(json.load(sys.stdin)['engine_mode'])" 2>/dev/null || echo "?")
# Watch port 22 (brute-force -> block_ip -> real drop is the headline demo)
curl -s --max-time 3 -X POST http://127.0.0.1:8000/api/traffic/port \
     -H 'Content-Type: application/json' -d '{"port":22}' >/dev/null 2>&1 || true

echo "[4/5] dashboard"
if [ "$START_DASHBOARD" = "1" ] && [ -d soc/dashboard/node_modules ]; then
    # Run Vite as the REAL user, never as root — root-owned files under
    # node_modules/.vite* would otherwise break later non-root `npm run dev`.
    DASH_USER="${SUDO_USER:-$(id -un)}"
    setsid sudo -u "$DASH_USER" bash -c 'cd soc/dashboard && npm run dev -- --host 0.0.0.0 --port 3001' \
        >/tmp/soc_dash.log 2>&1 < /dev/null &
    echo "      dashboard dev server starting on http://localhost:3001 (as $DASH_USER)"
else
    echo "      skipped (set START_DASHBOARD=1 and run 'npm install' in soc/dashboard to enable)"
fi

echo "[5/5] ready — backend http://localhost:8000 (engine_mode=$MODE, executor=lab, auto, watching :22)"
