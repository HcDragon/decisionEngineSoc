#!/usr/bin/env bash
# ==============================================================================
# attack/scenarios/dns_flood.sh
# DNS flood from the attacker namespace -> 'dos_flood' family -> R-DOS
# (recommend). A high-rate UDP burst aimed at port 53, which reads as a DNS
# flood to the SOC. Same rate-rule flood branch as the SYN/UDP floods; the
# distinction is the destination port (53).
#
# Uses the no-sudo Python generator (attack/gen_traffic.py udpflood) -- no
# hping3/root needed. Requires a running lab (sudo defend/setup_netns.sh).
#
#   sudo attack/scenarios/dns_flood.sh
#
# Env overrides: PORT (default 53), PACKETS (default 20000).
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
source ./defend/lab.env

PORT="${PORT:-53}"
PACKETS="${PACKETS:-20000}"
PY=.venv/bin/python
[ -x "$PY" ] || { echo "[-] venv missing. Run run_linux.sh first." >&2; exit 1; }

echo "[attack] DNS flood $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP:$PORT ($PACKETS datagrams)"
attack/run.sh "$PY" attack/gen_traffic.py udpflood \
    --target "$DEFENDER_LAB_IP" --port "$PORT" --packets "$PACKETS" || true
echo "[attack] DNS flood complete"
