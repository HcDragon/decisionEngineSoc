"""
Policy & Configuration Loader.

Loads and validates the YAML/CSV configuration that drives the Decision Engine:
  - policies.yaml  (scoring weights, tiers, attack families, rules, correlation)
  - assets.yaml    (asset inventory, criticality, isolatable, attacker pool)
  - allowlist.yaml (IPs that must never be acted upon)
  - intel/blocklist.csv (threat intel scores per IP)
  - playbooks/*.yaml (response playbooks referenced by rules)

A deterministic ``policy_hash`` is computed over the normalized policy document
so every Decision can be traced back to the exact policy version that produced it.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from soc.backend.app.config import settings


# ---------------------------------------------------------------------------
# Typed policy objects
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ScoringWeights:
    severity: float
    confidence: float
    asset: float
    intel: float


@dataclass(frozen=True)
class RepeatOffenderPolicy:
    window_s: int
    per_event: float
    max_bonus: float


@dataclass(frozen=True)
class AttackFamily:
    name: str
    members: List[str]
    severity: float


@dataclass(frozen=True)
class Rule:
    id: str
    priority: int
    description: str
    when: Dict[str, Any]
    mode: str
    playbook: Optional[str]


@dataclass(frozen=True)
class Asset:
    ip: str
    name: str
    role: str
    criticality: float
    owner: str
    isolatable: bool


@dataclass(frozen=True)
class IntelEntry:
    ip: str
    threat_score: float
    source: str
    description: str


@dataclass
class PolicyBundle:
    """Everything the engine needs to score and decide, loaded once and cached."""
    version: int
    weights: ScoringWeights
    repeat_offender: RepeatOffenderPolicy
    min_alert_confidence: float
    tiers: Dict[str, float]
    correlation_window_s: int
    correlation_key: List[str]
    families: Dict[str, AttackFamily]
    rules: List[Rule]
    assets: Dict[str, Asset]
    default_criticality: float
    attacker_pool: List[str]
    allowlist: Dict[str, str]
    intel: Dict[str, IntelEntry]
    playbooks: Dict[str, Dict[str, Any]]
    policy_hash: str

    # ---- convenience lookups -------------------------------------------------
    def family_for_label(self, label: str) -> Optional[str]:
        """Map a model label (e.g. 'DoS SYN Flood') to its family key (e.g. 'dos_flood')."""
        for key, fam in self.families.items():
            if label in fam.members:
                return key
        return None

    def severity_for_family(self, family: Optional[str]) -> float:
        fam = self.families.get(family) if family else None
        return fam.severity if fam else 0.0

    def asset_criticality(self, ip: Optional[str]) -> float:
        if ip and ip in self.assets:
            return self.assets[ip].criticality
        return self.default_criticality

    def intel_score(self, ip: Optional[str]) -> float:
        if ip and ip in self.intel:
            return self.intel[ip].threat_score
        return 0.0

    def is_allowlisted(self, ip: Optional[str]) -> bool:
        return bool(ip) and ip in self.allowlist

    def tier_for_score(self, score: float) -> str:
        # tiers map a lowercase name -> lower bound; pick the highest bound <= score
        ordered = sorted(self.tiers.items(), key=lambda kv: kv[1])
        label = ordered[0][0]
        for name, lo in ordered:
            if score >= lo:
                label = name
        return label.upper()


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _read_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _canonical_hash(obj: Any) -> str:
    """Stable SHA-256 over a JSON-normalized object (order-independent)."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_policy_bundle(config_dir: Optional[Path] = None) -> PolicyBundle:
    """Load and validate the full policy bundle from the config directory."""
    cfg = config_dir or settings.config_path

    policies = _read_yaml(cfg / "policies.yaml")
    assets_doc = _read_yaml(cfg / "assets.yaml")
    allowlist_doc = _read_yaml(cfg / "allowlist.yaml")

    # ---- scoring ------------------------------------------------------------
    scoring = policies["scoring"]
    w = scoring["weights"]
    weights = ScoringWeights(
        severity=float(w["severity"]),
        confidence=float(w["confidence"]),
        asset=float(w["asset"]),
        intel=float(w["intel"]),
    )
    ro = scoring["repeat_offender"]
    repeat = RepeatOffenderPolicy(
        window_s=int(ro["window_s"]),
        per_event=float(ro["per_event"]),
        max_bonus=float(ro["max_bonus"]),
    )
    min_alert_confidence = float(scoring.get("min_alert_confidence", 0.0))

    # ---- tiers --------------------------------------------------------------
    tiers = {str(k): float(v) for k, v in policies["tiers"].items()}

    # ---- correlation --------------------------------------------------------
    corr = policies.get("correlation", {})
    correlation_window_s = int(corr.get("window_s", 60))
    correlation_key = list(corr.get("key", ["src_ip", "family"]))

    # ---- families -----------------------------------------------------------
    families: Dict[str, AttackFamily] = {}
    for key, body in policies.get("attack_families", {}).items():
        families[key] = AttackFamily(
            name=key,
            members=list(body.get("members", [])),
            severity=float(body.get("severity", 0.0)),
        )

    # ---- rules (sorted by priority ascending; first match wins) -------------
    rules: List[Rule] = []
    for r in policies.get("rules", []):
        then = r.get("then", {})
        rules.append(
            Rule(
                id=str(r["id"]),
                priority=int(r.get("priority", 999)),
                description=str(r.get("description", "")),
                when=dict(r.get("when", {}) or {}),
                mode=str(then.get("mode", "monitor")),
                playbook=then.get("playbook"),
            )
        )
    rules.sort(key=lambda x: x.priority)

    # ---- assets -------------------------------------------------------------
    assets: Dict[str, Asset] = {}
    for a in assets_doc.get("assets", []):
        assets[a["ip"]] = Asset(
            ip=a["ip"],
            name=a.get("name", a["ip"]),
            role=a.get("role", "unknown"),
            criticality=float(a.get("criticality", 0.0)),
            owner=a.get("owner", "unknown"),
            isolatable=bool(a.get("isolatable", False)),
        )
    default_criticality = float(assets_doc.get("default_criticality", 0.4))
    attacker_pool = list(assets_doc.get("attacker_pool", []))

    # ---- allowlist ----------------------------------------------------------
    allowlist: Dict[str, str] = {}
    for entry in allowlist_doc.get("allowlist", []):
        allowlist[entry["ip"]] = entry.get("description", "")

    # ---- intel (CSV) --------------------------------------------------------
    intel: Dict[str, IntelEntry] = {}
    blocklist_path = cfg / "intel" / "blocklist.csv"
    if blocklist_path.exists():
        with open(blocklist_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                intel[row["ip"]] = IntelEntry(
                    ip=row["ip"],
                    threat_score=float(row.get("threat_score", 0.0)),
                    source=row.get("source", ""),
                    description=row.get("description", ""),
                )

    # ---- playbooks ----------------------------------------------------------
    playbooks: Dict[str, Dict[str, Any]] = {}
    pb_dir = cfg / "playbooks"
    if pb_dir.exists():
        for pb_file in sorted(pb_dir.glob("*.yaml")):
            pb = _read_yaml(pb_file)
            playbooks[pb["id"]] = pb

    # ---- policy hash (over the normalized policy inputs) --------------------
    policy_hash = _canonical_hash(
        {
            "policies": policies,
            "assets": assets_doc,
            "allowlist": allowlist_doc,
            "intel": sorted(intel.keys()),
            "playbooks": sorted(playbooks.keys()),
        }
    )

    return PolicyBundle(
        version=int(policies.get("version", 1)),
        weights=weights,
        repeat_offender=repeat,
        min_alert_confidence=min_alert_confidence,
        tiers=tiers,
        correlation_window_s=correlation_window_s,
        correlation_key=correlation_key,
        families=families,
        rules=rules,
        assets=assets,
        default_criticality=default_criticality,
        attacker_pool=attacker_pool,
        allowlist=allowlist,
        intel=intel,
        playbooks=playbooks,
        policy_hash=policy_hash,
    )


@lru_cache(maxsize=1)
def get_policy() -> PolicyBundle:
    """Process-wide cached policy bundle. Call :func:`reload_policy` to refresh."""
    return load_policy_bundle()


def reload_policy() -> PolicyBundle:
    """Clear the cache and reload (used after a config change / hot reload)."""
    get_policy.cache_clear()
    return get_policy()
