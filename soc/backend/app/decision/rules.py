"""
Policy Rule Engine.

Evaluates the ordered rule list from ``policies.yaml`` against a scored alert and
returns the first matching rule, the resulting mode/playbook, and a full trace of
why each rule did or did not match (persisted on the Decision for auditability).

Supported ``when`` conditions:
    min_score            float   score must be >= value
    min_confidence       float   confidence (0-1) must be >= value
    min_margin           float   top-2 probability margin must be >= value
    family               str     family key must equal value
    any_of               list    at least one sub-condition must hold:
                                     {intel_hit: true}
                                     {repeat_count_gte: N}
An empty ``when: {}`` always matches (the default fallback rule).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from soc.backend.app.policy.loader import PolicyBundle, Rule


@dataclass
class RuleMatch:
    rule_id: str
    mode: str
    playbook: Optional[str]
    trace: Dict[str, Any]


def _any_of_ok(any_of: List[Dict[str, Any]], *, intel_hit: bool, repeat_count: int) -> (bool, List[Dict[str, Any]]):
    results = []
    ok = False
    for cond in any_of:
        if "intel_hit" in cond:
            passed = bool(cond["intel_hit"]) == bool(intel_hit)
            results.append({"intel_hit": cond["intel_hit"], "passed": passed})
        elif "repeat_count_gte" in cond:
            passed = repeat_count >= int(cond["repeat_count_gte"])
            results.append({"repeat_count_gte": cond["repeat_count_gte"], "actual": repeat_count, "passed": passed})
        else:
            results.append({"unknown_condition": cond, "passed": False})
            passed = False
        ok = ok or passed
    return ok, results


def _eval_rule(
    rule: Rule,
    *,
    score: float,
    confidence: float,
    margin: float,
    family: Optional[str],
    intel_hit: bool,
    repeat_count: int,
) -> (bool, Dict[str, Any]):
    """Return (matched, per-condition trace) for one rule."""
    when = rule.when
    conds: Dict[str, Any] = {}
    matched = True

    if "min_score" in when:
        passed = score >= float(when["min_score"])
        conds["min_score"] = {"required": when["min_score"], "actual": score, "passed": passed}
        matched = matched and passed

    if "min_confidence" in when:
        passed = confidence >= float(when["min_confidence"])
        conds["min_confidence"] = {"required": when["min_confidence"], "actual": confidence, "passed": passed}
        matched = matched and passed

    if "min_margin" in when:
        passed = margin >= float(when["min_margin"])
        conds["min_margin"] = {"required": when["min_margin"], "actual": margin, "passed": passed}
        matched = matched and passed

    if "family" in when:
        passed = family == when["family"]
        conds["family"] = {"required": when["family"], "actual": family, "passed": passed}
        matched = matched and passed

    if "any_of" in when:
        ok, sub = _any_of_ok(when["any_of"], intel_hit=intel_hit, repeat_count=repeat_count)
        conds["any_of"] = {"results": sub, "passed": ok}
        matched = matched and ok

    if not when:
        conds["default"] = {"passed": True}

    return matched, conds


def evaluate_rules(
    policy: PolicyBundle,
    *,
    score: float,
    confidence: float,
    margin: float,
    family: Optional[str],
    intel_hit: bool,
    repeat_count: int,
) -> RuleMatch:
    """Evaluate all rules in priority order; first match wins. Always returns a match
    because ``policies.yaml`` defines a catch-all default rule."""
    evaluated: List[Dict[str, Any]] = []

    for rule in policy.rules:  # already sorted by priority ascending
        matched, conds = _eval_rule(
            rule,
            score=score,
            confidence=confidence,
            margin=margin,
            family=family,
            intel_hit=intel_hit,
            repeat_count=repeat_count,
        )
        evaluated.append(
            {"rule_id": rule.id, "priority": rule.priority, "matched": matched, "conditions": conds}
        )
        if matched:
            return RuleMatch(
                rule_id=rule.id,
                mode=rule.mode,
                playbook=rule.playbook,
                trace={"matched_rule": rule.id, "evaluated": evaluated},
            )

    # Should never happen if a default rule exists, but fail safe to monitor.
    return RuleMatch(
        rule_id="R-NONE",
        mode="monitor",
        playbook=None,
        trace={"matched_rule": None, "evaluated": evaluated, "warning": "no rule matched"},
    )
