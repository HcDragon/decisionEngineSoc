"""
Lab Firewall Executor — the ONLY place in the system that touches real packet
filtering. Applies real ``nft`` rules so a blocked source genuinely cannot reach
the defender host (used by the single-machine namespace test harness).

SAFETY GUARDRAILS (all must hold before a single real rule is applied):
  1. settings.SOC_LAB_MODE is True, and
  2. settings.SOC_EXECUTOR == "lab", and
  3. the target IP falls inside settings.LAB_ALLOWED_CIDRS, and
  4. the ``nft`` binary is available (and the process has privilege to use it).

If any guard fails, enforcement is a no-op that reports *why* — the decision is
still recorded in the DB virtual-firewall, exactly as in simulated mode, so the
default (safe) configuration keeps its "zero real side effects" guarantee.

Rules live in a dedicated table/chain (``inet soc_lab`` / ``SOC_BLOCK``) so
teardown can flush only our own rules and never disturb the host's firewall.
"""
from __future__ import annotations

import ipaddress
import logging
import shutil
import subprocess
from typing import Dict, List, Tuple

from soc.backend.app.config import settings

logger = logging.getLogger("soc.firewall")

FAMILY = "inet"
TABLE = "soc_lab"
CHAIN = "SOC_BLOCK"


def is_lab_enabled() -> bool:
    """True only when the operator has explicitly armed real enforcement."""
    return bool(settings.SOC_LAB_MODE) and settings.SOC_EXECUTOR == "lab"


def nft_available() -> bool:
    return shutil.which("nft") is not None


def target_in_lab(target: str) -> bool:
    """True if the target IP is inside one of the configured lab CIDRs."""
    try:
        ip = ipaddress.ip_address(str(target))
    except ValueError:
        return False
    for cidr in settings.lab_cidrs:
        try:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _run(args: List[str]) -> Tuple[int, str]:
    try:
        p = subprocess.run(["nft", *args], capture_output=True, text=True, timeout=5)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "nft not found"
    except Exception as e:  # pragma: no cover - defensive
        return 1, str(e)


def ensure_chain() -> bool:
    """Idempotently create our dedicated table + input-hook chain."""
    _run(["add", "table", FAMILY, TABLE])
    rc, out = _run([
        "add", "chain", FAMILY, TABLE, CHAIN,
        "{ type filter hook input priority 0 ; policy accept ; }",
    ])
    return rc == 0 or "File exists" in out


def _rule_body(target: str, kind: str) -> List[str]:
    if kind == "rate_limit":
        # Allow a trickle, drop the excess (demonstrable throttling).
        return ["ip", "saddr", str(target), "limit", "rate", "over", "20/second", "drop"]
    # block / isolate -> drop everything from this source.
    return ["ip", "saddr", str(target), "drop"]


def apply_block(target: str, kind: str = "block") -> Dict[str, object]:
    """Apply a real nft rule for ``target``. Returns a result dict describing
    whether enforcement actually happened and, if not, why (never raises)."""
    if not is_lab_enabled():
        return {"enforced": False, "reason": "lab_executor_disabled"}
    if not target_in_lab(target):
        return {"enforced": False, "reason": "target_outside_lab_cidrs", "target": str(target)}
    if not nft_available():
        return {"enforced": False, "reason": "nft_unavailable"}
    if not ensure_chain():
        return {"enforced": False, "reason": "ensure_chain_failed"}
    rc, out = _run(["add", "rule", FAMILY, TABLE, CHAIN, *_rule_body(target, kind)])
    ok = rc == 0
    (logger.info if ok else logger.warning)(
        "nft %s %s -> rc=%s %s", kind, target, rc, out
    )
    return {"enforced": ok, "kind": kind, "target": str(target), "nft_rc": rc, "detail": out}


def remove_block(target: str) -> Dict[str, object]:
    """Delete every SOC_BLOCK rule matching ``target`` (by handle)."""
    if not nft_available():
        return {"removed": False, "reason": "nft_unavailable"}
    rc, out = _run(["-a", "list", "chain", FAMILY, TABLE, CHAIN])
    if rc != 0:
        return {"removed": False, "reason": "chain_absent"}
    removed = 0
    needle = f"saddr {target} "
    for line in out.splitlines():
        if needle in line and "handle" in line:
            handle = line.rsplit("handle", 1)[-1].strip()
            r2, _ = _run(["delete", "rule", FAMILY, TABLE, CHAIN, "handle", handle])
            if r2 == 0:
                removed += 1
    return {"removed": removed > 0, "count": removed, "target": str(target)}


def flush_all() -> Dict[str, object]:
    """Remove our entire table/chain — used on test-lab teardown so no stale
    block rules persist on the real host."""
    _run(["flush", "chain", FAMILY, TABLE, CHAIN])
    rc, out = _run(["delete", "table", FAMILY, TABLE])
    logger.info("flushed %s/%s (rc=%s %s)", TABLE, CHAIN, rc, out)
    return {"flushed": True, "detail": out}


def list_rules() -> str:
    rc, out = _run(["list", "chain", FAMILY, TABLE, CHAIN])
    return out if rc == 0 else "(no SOC_BLOCK chain)"


if __name__ == "__main__":  # tiny CLI for the orchestration scripts
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "flush":
        print(flush_all())
    elif cmd == "list":
        print(list_rules())
    elif cmd == "status":
        print({
            "lab_enabled": is_lab_enabled(),
            "nft": nft_available(),
            "lab_cidrs": settings.lab_cidrs,
            "executor": settings.SOC_EXECUTOR,
            "lab_mode": settings.SOC_LAB_MODE,
        })
    else:
        print(f"usage: python -m soc.backend.app.response.firewall [flush|list|status]")
