import os
import yaml
from typing import Optional, Dict, Any, List
from decision_engine.models.context import EnrichedContext
from decision_engine.models.risk import RiskAssessment, RiskSeverity, RiskFactorContribution
from decision_engine.audit.audit_logger import AuditLogger

class RiskEngine:
    """
    Mathematical, explainable Risk Engine driven by external YAML configuration.
    Calculates normalized scores (0-100) and explicit factor contributions.
    """
    def __init__(self, config_path: Optional[str] = None, audit_logger: Optional[AuditLogger] = None):
        self.audit = audit_logger or AuditLogger()
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "risk.yaml")
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            # Fallback default configuration
            self._config = {
                "risk": {
                    "factors": {
                        "detection_confidence": {"weight": 0.25},
                        "attack_severity": {
                            "weight": 0.25,
                            "base_scores": {
                                "Benign Traffic": 0,
                                "Dictionary Brute Force": 70,
                                "DoS ICMP Flood": 80,
                                "DoS DNS Flood": 85,
                                "DoS UDP Flood": 90,
                                "DoS SYN Flood": 95,
                                "default": 50
                            }
                        },
                        "traffic_intensity": {"weight": 0.20},
                        "asset_criticality": {"weight": 0.15, "default_score": 50},
                        "recurrence": {"weight": 0.15}
                    }
                }
            }

    def assess_risk(self, context: EnrichedContext, event_id: Optional[str] = None, incident_id: Optional[str] = None) -> RiskAssessment:
        factors_cfg = self._config.get("risk", {}).get("factors", {})
        factor_contributions: List[RiskFactorContribution] = []
        total_risk = 0.0

        # 1. Detection Confidence Factor
        conf_cfg = factors_cfg.get("detection_confidence", {})
        conf_weight = float(conf_cfg.get("weight", 0.25))
        conf_score = min(100.0, max(0.0, context.observed.confidence * 100.0))
        conf_contrib = conf_score * conf_weight
        total_risk += conf_contrib
        factor_contributions.append(RiskFactorContribution(
            name="Detection Confidence",
            raw_value=context.observed.confidence,
            normalized_score=round(conf_score, 2),
            weight=conf_weight,
            contribution=round(conf_contrib, 2),
            explanation=f"ML detector reported {context.observed.confidence * 100:.1f}% confidence."
        ))

        # 2. Attack Severity Factor
        sev_cfg = factors_cfg.get("attack_severity", {})
        sev_weight = float(sev_cfg.get("weight", 0.25))
        base_scores = sev_cfg.get("base_scores", {})
        attack_type = context.observed.attack_type
        sev_score = float(base_scores.get(attack_type, base_scores.get("default", 50)))
        sev_contrib = sev_score * sev_weight
        total_risk += sev_contrib
        factor_contributions.append(RiskFactorContribution(
            name="Attack Inherent Severity",
            raw_value=attack_type,
            normalized_score=round(sev_score, 2),
            weight=sev_weight,
            contribution=round(sev_contrib, 2),
            explanation=f"Inherent risk score for '{attack_type}' is {sev_score}."
        ))

        # 3. Traffic Intensity Factor
        int_cfg = factors_cfg.get("traffic_intensity", {})
        int_weight = float(int_cfg.get("weight", 0.20))
        pps = context.observed.packets_per_second
        if pps >= 20000:
            int_score = 100.0
            int_desc = f"Extreme packet volume ({pps:.0f} pps)"
        elif pps >= 5000:
            int_score = 75.0
            int_desc = f"High packet volume ({pps:.0f} pps)"
        elif pps >= 1000:
            int_score = 50.0
            int_desc = f"Elevated packet volume ({pps:.0f} pps)"
        elif pps >= 100:
            int_score = 25.0
            int_desc = f"Moderate packet volume ({pps:.0f} pps)"
        else:
            int_score = 0.0
            int_desc = f"Normal/low packet rate ({pps:.0f} pps)"
        int_contrib = int_score * int_weight
        total_risk += int_contrib
        factor_contributions.append(RiskFactorContribution(
            name="Traffic Intensity",
            raw_value=pps,
            normalized_score=round(int_score, 2),
            weight=int_weight,
            contribution=round(int_contrib, 2),
            explanation=int_desc
        ))

        # 4. Asset Criticality Factor
        asset_cfg = factors_cfg.get("asset_criticality", {})
        asset_weight = float(asset_cfg.get("weight", 0.15))
        default_crit = float(asset_cfg.get("default_score", 50))
        asset_score = float(context.configured.asset_criticality) if context.configured.asset_criticality is not None else default_crit
        asset_contrib = asset_score * asset_weight
        total_risk += asset_contrib
        crit_label = f" (Role: {context.configured.destination_role})" if context.configured.destination_role else ""
        factor_contributions.append(RiskFactorContribution(
            name="Asset Criticality",
            raw_value=context.configured.asset_criticality,
            normalized_score=round(asset_score, 2),
            weight=asset_weight,
            contribution=round(asset_contrib, 2),
            explanation=f"Target asset importance score is {asset_score}{crit_label}."
        ))

        # 5. Recurrence / Frequency Factor
        rec_cfg = factors_cfg.get("recurrence", {})
        rec_weight = float(rec_cfg.get("weight", 0.15))
        repeat_count = context.derived.repeated_detections_count
        if repeat_count >= 10:
            rec_score = 100.0
        elif repeat_count >= 3:
            rec_score = 60.0
        elif repeat_count > 1:
            rec_score = 30.0
        else:
            rec_score = 0.0
        rec_contrib = rec_score * rec_weight
        total_risk += rec_contrib
        factor_contributions.append(RiskFactorContribution(
            name="Threat Recurrence",
            raw_value=repeat_count,
            normalized_score=round(rec_score, 2),
            weight=rec_weight,
            contribution=round(rec_contrib, 2),
            explanation=f"Source IP involved in {repeat_count} repeated event(s)."
        ))

        # Normalize and clamp final risk score between 0.0 and 100.0
        final_risk = min(100.0, max(0.0, total_risk))

        # Determine Severity Category
        if final_risk >= 81.0:
            severity = RiskSeverity.CRITICAL
        elif final_risk >= 61.0:
            severity = RiskSeverity.HIGH
        elif final_risk >= 41.0:
            severity = RiskSeverity.MEDIUM
        elif final_risk >= 21.0:
            severity = RiskSeverity.LOW
        else:
            severity = RiskSeverity.INFORMATIONAL

        explanation = (
            f"{attack_type} detected with {context.observed.confidence * 100:.1f}% confidence on {context.observed.destination_ip}. "
            f"Calculated risk score is {final_risk:.1f} ({severity.value}) based on weighted evidence."
        )

        self.audit.log(
            event_type="RISK_CALCULATED",
            details=f"Risk Score: {final_risk:.1f} ({severity.value}) for {attack_type}",
            incident_id=incident_id,
            event_id=event_id,
            component="RISK_ENGINE"
        )

        return RiskAssessment(
            risk_score=round(final_risk, 2),
            severity=severity,
            factors=factor_contributions,
            summary_explanation=explanation
        )
