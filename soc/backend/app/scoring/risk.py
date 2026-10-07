"""
Risk Scoring.

Computes a 0-100 risk score for an alert from four weighted components plus a
repeat-offender bonus, exactly as specified in ``policies.yaml``:

    raw = 100 * (w.severity*severity + w.confidence*confidence
                 + w.asset*asset_criticality + w.intel*intel_score)
    score = min(100, raw + repeat_bonus)

All component contributions are returned in the ``breakdown`` so the Decision
record (and the explanation panel) can show exactly how the number was built.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from soc.backend.app.policy.loader import PolicyBundle


@dataclass
class ScoreResult:
    score: float                      # final 0-100 risk score
    tier: str                         # LOW | MEDIUM | HIGH | CRITICAL
    breakdown: Dict[str, float]       # point contribution of each component
    inputs: Dict[str, Any]            # the raw 0-1 inputs used (for explanation)
    intel_hit: bool
    repeat_count: int


def compute_risk(
    policy: PolicyBundle,
    *,
    family: Optional[str],
    confidence: float,
    src_ip: Optional[str],
    dst_ip: Optional[str],
    repeat_count: int = 0,
) -> ScoreResult:
    """
    Score a single alert.

    :param family: attack family key (e.g. ``dos_flood``); None/benign -> low severity
    :param confidence: model confidence in [0, 1]
    :param src_ip: attacking source (used for intel + repeat-offender)
    :param dst_ip: target asset (used for asset criticality)
    :param repeat_count: number of prior events from this source in the window
    """
    w = policy.weights

    severity = policy.severity_for_family(family)

    # Benign (or unknown) classification carries no risk by definition: the
    # confidence/asset/intel weights express how dangerous an *attack* is, so a
    # benign flow must not inflate the score just because it targets a critical
    # asset or the model is very sure it's benign. See docs/ASSUMPTIONS.md §5.
    is_threat = family is not None and family != "benign" and severity > 0.0
    if not is_threat:
        return ScoreResult(
            score=0.0,
            tier=policy.tier_for_score(0.0),
            breakdown={"severity": 0.0, "confidence": 0.0, "asset": 0.0, "intel": 0.0, "repeat_bonus": 0.0},
            inputs={"severity": round(severity, 4), "confidence": round(float(confidence), 4),
                    "family": family, "is_threat": False},
            intel_hit=policy.intel_score(src_ip) > 0.0,
            repeat_count=repeat_count,
        )

    conf = max(0.0, min(1.0, float(confidence)))
    asset_crit = policy.asset_criticality(dst_ip)
    intel = policy.intel_score(src_ip)
    intel_hit = intel > 0.0

    # Weighted components, expressed directly as points out of 100.
    sev_pts = 100.0 * w.severity * severity
    conf_pts = 100.0 * w.confidence * conf
    asset_pts = 100.0 * w.asset * asset_crit
    intel_pts = 100.0 * w.intel * intel

    # Repeat-offender bonus: per_event points each, capped at max_bonus.
    ro = policy.repeat_offender
    repeat_bonus = min(ro.max_bonus, ro.per_event * max(0, repeat_count))

    raw = sev_pts + conf_pts + asset_pts + intel_pts
    score = min(100.0, raw + repeat_bonus)
    tier = policy.tier_for_score(score)

    breakdown = {
        "severity": round(sev_pts, 2),
        "confidence": round(conf_pts, 2),
        "asset": round(asset_pts, 2),
        "intel": round(intel_pts, 2),
        "repeat_bonus": round(repeat_bonus, 2),
    }
    inputs = {
        "severity": round(severity, 4),
        "confidence": round(conf, 4),
        "asset_criticality": round(asset_crit, 4),
        "intel_score": round(intel, 4),
        "repeat_count": repeat_count,
        "weights": {
            "severity": w.severity,
            "confidence": w.confidence,
            "asset": w.asset,
            "intel": w.intel,
        },
    }

    return ScoreResult(
        score=round(score, 2),
        tier=tier,
        breakdown=breakdown,
        inputs=inputs,
        intel_hit=intel_hit,
        repeat_count=repeat_count,
    )
