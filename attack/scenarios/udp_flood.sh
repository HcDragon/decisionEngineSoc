#!/usr/bin/env bash
# ==============================================================================
# attack/scenarios/udp_flood.sh
# UDP flood from the attacker namespace -> 'dos_flood' family -> R-DOS
# (recommend: detected + mitigation proposed; policy keeps DoS mitigation
# analyst-gated).
#
# Uses the no-sudo Python generator (attack/gen_traffic.py udpflood): one
# connected UDP socket fires a high-rate burst of tiny datagrams at the target
# port, which NFStream aggregates into a single high-packet flow that trips the
# rate-rule flood branch. No hping3/root required beyond the netns.
# Requires a running lab (sudo defend/setup_netns.sh).
#
#   sudo attack/scenarios/udp_flood.sh
#
# Env overrides: PORT (target UDP port, default 9901), PACKETS (default 20000).
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
source ./defend/lab.env

PORT="${PORT:-9901}"
PACKETS="${PACKETS:-20000}"
PY=.venv/bin/python
[ -x "$PY" ] || { echo "[-] venv missing. Run run_linux.sh first." >&2; exit 1; }

echo "[attack] UDP flood $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP:$PORT ($PACKETS datagrams)"
attack/run.sh "$PY" attack/gen_traffic.py udpflood \
    --target "$DEFENDER_LAB_IP" --port "$PORT" --packets "$PACKETS" || true
echo "[attack] UDP flood complete"
