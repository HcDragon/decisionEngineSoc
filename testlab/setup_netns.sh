#!/usr/bin/env bash
# ==============================================================================
# testlab/setup_netns.sh  (MASTER PRD Phase 1)
# Create an isolated attacker network namespace connected to the host by a veth
# pair, simulating the two-machine lab (defender host 10.66.0.10 / attacker
# 10.66.0.20) on a single Ubuntu box. Requires root.
#
# Isolation guarantee: the attacker namespace gets ONLY the directly-connected
# 10.66.0.0/24 route. It has NO default route and NO DNS, so it can reach the
# defender host and nothing else (not the internet, not your real LAN).
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")"
# shellcheck disable=SC1091
source ./lab.env

if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Must run as root:  sudo testlab/setup_netns.sh" >&2
    exit 1
fi

echo "[*] Setting up namespace lab: $ATTACKER_NETNS ($ATTACKER_LAB_IP) <-> host ($DEFENDER_LAB_IP)"

# --- Idempotent create: skip pieces that already exist ----------------------
if ip netns list | grep -qw "$ATTACKER_NETNS"; then
    echo "[=] netns '$ATTACKER_NETNS' already exists"
else
    ip netns add "$ATTACKER_NETNS"
    echo "[+] created netns '$ATTACKER_NETNS'"
fi

if ip link show "$VETH_DEF" >/dev/null 2>&1; then
    echo "[=] veth pair already present ($VETH_DEF)"
else
    ip link add "$VETH_DEF" type veth peer name "$VETH_ATT"
    ip link set "$VETH_ATT" netns "$ATTACKER_NETNS"
    echo "[+] created veth pair $VETH_DEF <-> $VETH_ATT (att end in netns)"
fi

# --- Host (defender) side ---------------------------------------------------
ip addr replace "$DEFENDER_LAB_IP/24" dev "$VETH_DEF"
ip link set "$VETH_DEF" up

# --- Attacker namespace side ------------------------------------------------
ip netns exec "$ATTACKER_NETNS" ip addr replace "$ATTACKER_LAB_IP/24" dev "$VETH_ATT"
ip netns exec "$ATTACKER_NETNS" ip link set "$VETH_ATT" up
ip netns exec "$ATTACKER_NETNS" ip link set lo up

# --- SAFETY: do NOT add a default route in the attacker namespace -----------
# The ONLY route inside the attacker netns is the directly-connected
# 10.66.0.0/24 added implicitly by the address above. Never add a line like:
#     ip netns exec attacker ip route add default via ...
# Doing so would give the attacker internet/LAN reach and defeat the isolation
# this whole harness exists to test. (MASTER PRD Section 8.)

# --- Host must never bridge the lab interface to anything else --------------
sysctl -w net.ipv4.ip_forward=0 >/dev/null
echo "[+] net.ipv4.ip_forward=0 (host will not bridge $VETH_DEF)"

echo ""
echo "[OK] Namespace lab ready."
echo "     Defender (host) : $DEFENDER_LAB_IP on $VETH_DEF  <- point NFStream here"
echo "     Attacker (netns): $ATTACKER_LAB_IP in '$ATTACKER_NETNS'"
echo ""
echo "Verify isolation (MASTER PRD 3.3):"
echo "  ip netns exec $ATTACKER_NETNS ping -c3 $DEFENDER_LAB_IP   # must SUCCEED"
echo "  ip netns exec $ATTACKER_NETNS ping -c3 8.8.8.8            # must FAIL"
echo "  ip netns exec $ATTACKER_NETNS ip route show              # ONLY 10.66.0.0/24"
