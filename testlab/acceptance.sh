#!/usr/bin/env bash
# ==============================================================================
# testlab/acceptance.sh — ONE-COMMAND full acceptance run.
# Verifies isolation, starts the lab, then runs TWO real attacks from the
# attacker namespace:
#   (A) SSH brute-force  -> brute_force -> R-BRUTE(auto) -> REAL nft block ->
#       attacker ping FAILS -> TTL expiry -> ping RECOVERS.
#   (B) SYN flood        -> dos_flood  -> R-DOS(recommend) -> detected +
#       mitigation PROPOSED (policy keeps DoS mitigation analyst-gated).
# Then tears everything down. Run:  sudo bash testlab/acceptance.sh
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source testlab/lab.env
[ "$(id -u)" -eq 0 ] || { echo "[-] run with sudo:  sudo bash testlab/acceptance.sh" >&2; exit 1; }

export DEFAULT_BLOCK_TTL_S=45
TTL=$DEFAULT_BLOCK_TTL_S
API=http://127.0.0.1:8000
PY=.venv/bin/python
cu(){ curl -s --max-time 5 "$@"; }
hr(){ printf '\n========== %s ==========\n' "$1"; }
incidents(){ cu $API/api/incidents | $PY -c "import sys,json;d=json.load(sys.stdin);[print('  incident',i['id'],i['family'],'src',i['src_ip'],'alerts',i['alert_count'],'risk',i['max_risk'],'->',(i['latest_decision'] or {}).get('rule_id'),'mode',(i['latest_decision'] or {}).get('mode'),'status',(i['latest_decision'] or {}).get('status')) for i in d['incidents']]" 2>/dev/null; }

hr "STEP 1/8  install deps (sshd + hydra + hping3)"
apt-get update -qq || true
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server hydra hping3 >/dev/null 2>&1 || true
systemctl enable --now ssh >/dev/null 2>&1 || service ssh start || true
echo "[+] sshd: $(ss -ltn 2>/dev/null | grep -q ':22 ' && echo listening || echo 'NOT listening')"
echo "[+] hping3: $(command -v hping3 >/dev/null && echo present || echo MISSING)"

hr "STEP 2/8  isolation gate"
testlab/setup_netns.sh >/dev/null
echo -n "[check] attacker -> defender : "; ip netns exec "$ATTACKER_NETNS" ping -c2 -W2 "$DEFENDER_LAB_IP" >/dev/null 2>&1 && echo OK || echo FAIL
echo -n "[check] attacker -> internet : "
if ip netns exec "$ATTACKER_NETNS" ping -c2 -W2 8.8.8.8 >/dev/null 2>&1; then
    echo "REACHABLE <-- ISOLATION BROKEN, aborting"; testlab/teardown_netns.sh >/dev/null; exit 1
else echo "blocked (correct)"; fi

hr "STEP 3/8  start lab (backend: lab executor + auto, TTL=${TTL}s)"
testlab/start_testlab.sh || { echo "[-] start failed"; testlab/stop_testlab.sh; exit 1; }

hr "STEP 4/8  ATTACK A — SSH brute-force from $ATTACKER_LAB_IP"
printf 'alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\ngolf\nhotel\n' > /tmp/wl.txt
ip netns exec "$ATTACKER_NETNS" hydra -l testuser -P /tmp/wl.txt -t 4 ssh://"$DEFENDER_LAB_IP" >/tmp/hydra.log 2>&1 || true
echo "[*] detection + auto-block settling..."; sleep 8

hr "STEP 5/8  RESULT A — incident, decision, REAL nft block"
incidents
cu $API/api/firewall | $PY -c "import sys,json;d=json.load(sys.stdin);print('  virtual-firewall:',[(e['kind'],e['target'],'active' if e['active'] else 'expired') for e in d['entries']])" 2>/dev/null
echo "  real nft rules (inet soc_lab):"
if nft list table inet soc_lab >/tmp/nft_block.txt 2>/dev/null; then
    grep -E "saddr|drop|limit" /tmp/nft_block.txt | sed 's/^/     /'
    echo "     -> $(grep -cE 'drop|limit' /tmp/nft_block.txt) enforcement rule(s)"
else echo "     (table absent)"; fi
echo -n "[check] attacker ping while blocked : "
ip netns exec "$ATTACKER_NETNS" ping -c3 -W2 "$DEFENDER_LAB_IP" >/tmp/pb.txt 2>&1 \
    && echo "got replies ($(grep -oE '[0-9]+% packet loss' /tmp/pb.txt|head -1))" \
    || echo "BLOCKED ($(grep -oE '[0-9]+% packet loss' /tmp/pb.txt|head -1)) <-- PASS"

hr "STEP 6/8  wait ${TTL}s for TTL expiry + auto-recovery"
sleep $((TTL + 8))
echo "  enforcement rules after expiry: $(nft list table inet soc_lab 2>/dev/null | grep -cE 'drop|limit' || echo 0) (expect 0)"
echo -n "[check] attacker ping after expiry  : "
ip netns exec "$ATTACKER_NETNS" ping -c3 -W2 "$DEFENDER_LAB_IP" >/dev/null 2>&1 && echo "RECOVERED <-- PASS" || echo "still blocked"

hr "STEP 7/8  ATTACK B — SYN flood (DoS) from $ATTACKER_LAB_IP"
if command -v hping3 >/dev/null; then
    echo "[*] hping3 SYN flood -p 22 (single flow, ~6s)"
    timeout 6 ip netns exec "$ATTACKER_NETNS" hping3 -S --flood -p 22 -s 5000 -k "$DEFENDER_LAB_IP" >/dev/null 2>&1 || true
    echo "[*] detection settling..."; sleep 6
    echo "  incidents now:"; incidents
    echo "  (DoS maps to R-DOS = recommend: detected + mitigation PROPOSED, not auto-enforced by policy)"
else
    echo "  hping3 missing — skipped"
fi
echo -n "[check] audit chain : "; cu $API/api/audit/verify; echo

hr "STEP 8/8  teardown"
testlab/stop_testlab.sh
echo ""
echo "ACCEPTANCE COMPLETE.  Logs: /tmp/soc_testlab.log  /tmp/hydra.log"
