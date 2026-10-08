#!/usr/bin/env bash
# ==============================================================================
# testlab/stop_testlab.sh  (MASTER PRD Phase 3)
# Stop backend/dashboard (incl. NFStream child procs), FLUSH real SOC_BLOCK nft
# rules, tear down namespaces, and verify nothing is left. Requires root.
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source testlab/lab.env
[ "$(id -u)" -eq 0 ] || { echo "[-] run as root: sudo testlab/stop_testlab.sh" >&2; exit 1; }
PY=.venv/bin/python

echo "[1/4] stopping backend + dashboard (and NFStream children)"
if [ -f testlab/.backend.pid ]; then
    kill "$(cat testlab/.backend.pid)" 2>/dev/null || true
    rm -f testlab/.backend.pid
fi
pkill -9 -f "uvicorn.*soc.backend.app.main" 2>/dev/null || true
pkill -9 -f "soc.backend.app.main"          2>/dev/null || true   # nfstream forked children
command -v fuser >/dev/null 2>&1 && fuser -k 8000/tcp 2>/dev/null || true
pkill -f "vite"        2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
sleep 1

echo "[2/4] flushing real nft SOC_BLOCK rules"
$PY -m soc.backend.app.response.firewall flush 2>/dev/null || \
    { nft flush chain inet soc_lab SOC_BLOCK 2>/dev/null; nft delete table inet soc_lab 2>/dev/null; } || true

echo "[3/4] tearing down namespaces"
testlab/teardown_netns.sh >/dev/null || true

echo "[4/4] verification"
echo "   netns    : $(ip netns list | tr '\n' ' ' || true)"
echo "   veth     : $(ip link show "$VETH_DEF" >/dev/null 2>&1 && echo "$VETH_DEF STILL PRESENT" || echo gone)"
echo "   SOC_BLOCK: $(nft list table inet soc_lab >/dev/null 2>&1 && echo present || echo gone)"
echo "   port 8000: $(command -v fuser >/dev/null 2>&1 && (fuser 8000/tcp >/dev/null 2>&1 && echo 'still in use' || echo free) || echo '?')"
LEFT=$(pgrep -f 'uvicorn|vite' 2>/dev/null | grep -v "shell-snapshot" | wc -l)
echo "   procs    : $LEFT lab process(es) left"
echo "[OK] stopped."
