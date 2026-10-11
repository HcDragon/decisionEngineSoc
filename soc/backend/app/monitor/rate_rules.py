"""Rate-based detection layer — cross-flow / volumetric attacks the per-flow
ML model cannot see.

Two attack shapes defeat a per-flow classifier, no matter how good it is:

  * **Volumetric SYN flood** — NFStream aggregates the whole flood into one
    enormous flow (hundreds of thousands of packets). That magnitude is far
    outside the model's training distribution, so it extrapolates badly and
    scores it benign. The *signal* is the rate itself, not the flow's shape.

  * **SSH/auth brute force** — each login attempt is its own 2-3 packet flow,
    individually indistinguishable from a normal probe. The signal (many
    attempts from one source in a short window) exists only ACROSS flows; the
    correlation layer can't help because it only groups already-flagged alerts.

This detector runs alongside ML scoring in the capture path, keyed by source,
and emits an alert directly (bypassing the ML verdict) when a rate threshold is
crossed. Its alerts feed the existing decision pipeline exactly like an
ML-sourced one — same families, policy, correlation, playbooks — but are tagged
``rate-rule:*`` in ``model_version`` so their provenance is explicit (they are
deterministic rules, not ML probabilities).

Thresholds are overridable via env vars (SOC_FLOOD_PPS, SOC_FLOOD_SYN,
SOC_BRUTE_COUNT, SOC_BRUTE_WINDOW_S).
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple

# Auth service ports where a burst of short sessions from one source reads as a
# credential brute-force rather than normal traffic.
AUTH_PORTS = {21, 22, 23, 389, 445, 1433, 3306, 3389, 5432, 5900}


def _envf(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class RateDetector:
    """Sliding-window rate detector. Thread-safe; one instance per monitor.

    ``inspect`` is called once per captured flow and returns an alert dict to
    override the ML verdict, or ``None`` to leave ML scoring in charge.
    """

    def __init__(
        self,
        flood_pps: Optional[float] = None,
        flood_syn: Optional[float] = None,
        flood_min_packets: Optional[int] = None,
        brute_count: Optional[int] = None,
        brute_window_s: Optional[float] = None,
        short_flow_pkts: int = 40,
        cooldown_s: float = 15.0,
    ):
        self.flood_pps = flood_pps if flood_pps is not None else _envf("SOC_FLOOD_PPS", 1000.0)
        self.flood_syn = flood_syn if flood_syn is not None else _envf("SOC_FLOOD_SYN", 500.0)
        # Absolute packet floor for the pps branch. NFStream reports Flow
        # Packets/s as packets/duration, which explodes for near-zero-duration
        # tiny flows (a 2-3 packet RST/SSH flow at ~1ms computes thousands of
        # pps). Without this floor the pps rule misfires on those; a real flood
        # always has a large absolute packet count too.
        self.flood_min_packets = int(
            flood_min_packets if flood_min_packets is not None else _envf("SOC_FLOOD_MIN_PKTS", 50)
        )
        self.brute_count = int(brute_count if brute_count is not None else _envf("SOC_BRUTE_COUNT", 5))
        self.brute_window_s = brute_window_s if brute_window_s is not None else _envf("SOC_BRUTE_WINDOW_S", 10.0)
        self.short_flow_pkts = short_flow_pkts
        self.cooldown_s = cooldown_s

        self._lock = threading.Lock()
        # (src_ip, dst_port) -> timestamps of recent short-lived flows
        self._brute: Dict[Tuple[str, int], Deque[float]] = {}
        # key -> last-alert time, to avoid re-alerting every flow during an attack
        self._cooldown: Dict[str, float] = {}

    # -- helpers --------------------------------------------------------------
    def _cooling(self, key: str, now: float) -> bool:
        last = self._cooldown.get(key)
        return last is not None and (now - last) < self.cooldown_s

    def _arm_cooldown(self, key: str, now: float) -> None:
        self._cooldown[key] = now

    @staticmethod
    def _alert(label: str, kind: str, conf: float, reason: str) -> dict:
        # Deterministic rule -> full confidence on its one class, margin = conf.
        # Tagged so the decision engine / audit can tell rule alerts from ML ones.
        return {
            "label": label,
            "confidence": conf,
            "is_threat": True,
            "probabilities": {label: conf},
            "margin": conf,
            "detector": f"rate-rule:{kind}",
            "reason": reason,
            "dispatch": True,  # whether to raise/refresh an incident (cooldown-gated)
        }

    # -- main -----------------------------------------------------------------
    def inspect(
        self,
        *,
        src_ip: str,
        dst_ip: str,
        dst_port: int,
        packets: int,
        syn: int,
        ack: int,
        duration_ms: float,
        now: Optional[float] = None,
    ) -> Optional[dict]:
        """Return an override alert dict for a flood/brute pattern, else None."""
        now = time.time() if now is None else now
        packets = int(packets or 0)
        syn = int(syn or 0)
        ack = int(ack or 0)
        dur_s = (duration_ms or 0.0) / 1000.0

        with self._lock:
            self._prune(now)

            # --- Rule 1: volumetric flood ------------------------------------
            # pps over the flow; a sub-millisecond burst (dur~0) uses raw packet
            # count as its magnitude so an instantaneous spike still trips.
            pps = packets / dur_s if dur_s > 0 else float(packets)
            # pps trigger needs a real absolute packet count — guards against the
            # NFStream packets/duration artifact on tiny near-zero-duration flows.
            pps_trigger = packets >= self.flood_min_packets and pps >= self.flood_pps
            syn_skew = syn >= self.flood_syn and syn > 3 * max(ack, 1)
            if pps_trigger or syn_skew:
                # Flood detection is STATELESS: every matching flow is labelled a
                # flood (so the live table shows it, not the ML "benign" verdict).
                # The cooldown only throttles INCIDENT raising — `dispatch` is
                # False while cooling, so repeat flood chunks are shown but don't
                # spam new incidents.
                fkey = f"flood:{src_ip}->{dst_ip}"
                cooling = self._cooling(fkey, now)
                if not cooling:
                    self._arm_cooldown(fkey, now)
                a = self._alert(
                    "DoS SYN Flood", "flood", 0.99,
                    f"{int(pps)} pkts/s, {syn} SYN (ack={ack}) {src_ip}->{dst_ip}",
                )
                a["dispatch"] = not cooling
                return a

            # --- Rule 2: auth brute force ------------------------------------
            # Many short-lived flows from one source to the same auth port.
            if dst_port in AUTH_PORTS and packets <= self.short_flow_pkts:
                bkey = (src_ip, int(dst_port))
                dq = self._brute.setdefault(bkey, deque())
                dq.append(now)
                # prune to the window
                cutoff = now - self.brute_window_s
                while dq and dq[0] < cutoff:
                    dq.popleft()
                if len(dq) >= self.brute_count:
                    ckey = f"brute:{src_ip}:{dst_port}"
                    cooling = self._cooling(ckey, now)
                    if not cooling:
                        self._arm_cooldown(ckey, now)
                    a = self._alert(
                        "Dictionary Brute Force", "bruteforce", 0.95,
                        f"{len(dq)} short flows in {self.brute_window_s:.0f}s "
                        f"{src_ip}->:{dst_port}",
                    )
                    a["dispatch"] = not cooling
                    return a
        return None

    def _prune(self, now: float) -> None:
        """Drop empty/expired window and cooldown entries so memory stays bounded."""
        cutoff = now - self.brute_window_s
        for key in list(self._brute.keys()):
            dq = self._brute[key]
            while dq and dq[0] < cutoff:
                dq.popleft()
            if not dq:
                del self._brute[key]
        for key in list(self._cooldown.keys()):
            if now - self._cooldown[key] > self.cooldown_s:
                del self._cooldown[key]
