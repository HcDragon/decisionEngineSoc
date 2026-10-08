#!/usr/bin/env bash
# ==============================================================================
# testlab/teardown_netns.sh  (MASTER PRD Phase 1)
# Fully remove the attacker namespace and veth pair. Idempotent: safe to run
# even if nothing exists. Requires root.
# ==============================================================================
set -uo pipefail

cd "$(dirname "$0")"
# shellcheck disable=SC1091
source ./lab.env

if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Must run as root:  sudo testlab/teardown_netns.sh" >&2
    exit 1
fi

# Deleting the netns removes veth-att automatically (its peer may then vanish).
if ip netns list | grep -qw "$ATTACKER_NETNS"; then
    ip netns del "$ATTACKER_NETNS"
    echo "[+] deleted netns '$ATTACKER_NETNS'"
else
    echo "[=] netns '$ATTACKER_NETNS' not present"
fi

# Remove the host-side veth if it lingers independently.
if ip link show "$VETH_DEF" >/dev/null 2>&1; then
    ip link del "$VETH_DEF"
    echo "[+] deleted $VETH_DEF"
else
    echo "[=] $VETH_DEF not present"
fi

echo ""
echo "[*] Post-teardown state:"
echo "    netns list : $(ip netns list | tr '\n' ' ' || true)"
ip link show "$VETH_DEF" >/dev/null 2>&1 && echo "    WARNING: $VETH_DEF still present" || echo "    $VETH_DEF gone"
echo "[OK] teardown complete."
