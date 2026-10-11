#!/usr/bin/env bash
# ==============================================================================
# attack/scenarios/recon_scan.sh
# Port-scan recon from the attacker namespace -> 'recon' family -> R-RECON.
# Uses the no-sudo Python generator (attack/gen_traffic.py) so it needs no nmap:
# many short TCP connects to a closed port, run through the venv interpreter
# inside the attacker netns. Requires root and a running lab
# (sudo defend/setup_netns.sh).
#
#   sudo attack/scenarios/recon_scan.sh
#
# Env overrides: PORT (default 9999, a closed port), COUNT (probes, default 80).
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
source ./defend/lab.env

PORT="${PORT:-9999}"
COUNT="${COUNT:-80}"
PY=.venv/bin/python
[ -x "$PY" ] || { echo "[-] venv missing. Run run_linux.sh first." >&2; exit 1; }

echo "[attack] recon scan $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP:$PORT ($COUNT probes)"
attack/run.sh "$PY" attack/gen_traffic.py recon \
    --target "$DEFENDER_LAB_IP" --port "$PORT" --count "$COUNT" || true
echo "[attack] recon complete"
