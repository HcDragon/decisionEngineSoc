#!/usr/bin/env bash
# ==============================================================================
# testlab/run_attacker.sh  (MASTER PRD Phase 2, adapted)
# Thin wrapper: run a command INSIDE the attacker namespace, so it originates
# from 10.66.0.20 against the defender host at 10.66.0.10. Requires root.
#
# The PRD wraps lab/attacker/*.sh here; this repo has no lab/ suite, so the
# attacker payload is this project's own generator or any installed tool.
#
# Examples:
#   # no-sudo-tool recon (pure Python, runs the venv interpreter in the netns):
#   sudo testlab/run_attacker.sh .venv/bin/python scripts/gen_traffic.py \
#        recon --target 10.66.0.10 --port 9999 --count 80
#
#   # real tools once installed (scripts/setup_attack_lab.sh):
#   sudo testlab/run_attacker.sh nmap -sS -T4 10.66.0.10 -p 3000
#   sudo testlab/run_attacker.sh hping3 -S --flood -p 3000 10.66.0.10
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source ./testlab/lab.env

if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Must run as root:  sudo testlab/run_attacker.sh <cmd> ..." >&2
    exit 1
fi
if [ "$#" -eq 0 ]; then
    echo "usage: sudo testlab/run_attacker.sh <command> [args...]" >&2
    exit 2
fi
if ! ip netns list | grep -qw "$ATTACKER_NETNS"; then
    echo "[-] netns '$ATTACKER_NETNS' not found. Run: sudo testlab/setup_netns.sh" >&2
    exit 1
fi

echo "[*] exec in netns '$ATTACKER_NETNS' (src $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP): $*"
exec ip netns exec "$ATTACKER_NETNS" env TESTLAB_MODE=1 "$@"
