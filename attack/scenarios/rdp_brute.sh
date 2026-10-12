#!/usr/bin/env bash
# ==============================================================================
# attack/scenarios/rdp_brute.sh
# RDP brute-force from the attacker namespace -> 'brute_force' family -> R-BRUTE
# (auto: temporary source block). A burst of short-lived connects to the RDP
# port (3389), which is in the detector's AUTH_PORTS set, so >=5 within the
# rate window trip 'Dictionary Brute Force'.
#
# Uses the no-sudo Python generator (attack/gen_traffic.py brute) -- no extra
# tools needed. Requires a running lab (sudo defend/setup_netns.sh).
#
#   sudo attack/scenarios/rdp_brute.sh
#
# Env overrides: PORT (default 3389), COUNT (connects, default 16).
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
source ./defend/lab.env

PORT="${PORT:-3389}"
COUNT="${COUNT:-16}"
PY=.venv/bin/python
[ -x "$PY" ] || { echo "[-] venv missing. Run run_linux.sh first." >&2; exit 1; }

echo "[attack] RDP brute-force $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP:$PORT ($COUNT attempts)"
attack/run.sh "$PY" attack/gen_traffic.py brute \
    --target "$DEFENDER_LAB_IP" --port "$PORT" --count "$COUNT" || true
echo "[attack] RDP brute-force complete"
