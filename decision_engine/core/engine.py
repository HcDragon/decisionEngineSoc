import uuid
from datetime import datetime
from decision_engine.context.enricher import ContextEnricher
from decision_engine.intelligence.risk_calculator import RiskCalculator
from decision_engine.playbooks.registry import PlaybookSelector
from decision_engine.core.rules_engine import RulesEngine, IncidentContext

class DecisionManager:
    def __init__(self):
        self.rules_engine = RulesEngine()

    def process_prediction(self, prediction: dict) -> dict:
        """
        Accepts a dictionary with: attack_type, confidence, source_ip, destination_ip, packet_count.
        Returns a dictionary containing the decision.
        """
        attack_type = prediction.get("attack_type", "Unknown")
        confidence = prediction.get("confidence", 0.0)
        src_ip = prediction.get("source_ip", "")
        dest_ip = prediction.get("destination_ip", "")
        packet_count = prediction.get("packet_count", 0)

        # 1. Contextualize
        asset_crit = ContextEnricher.get_asset_criticality(dest_ip)
        threat_intel = ContextEnricher.get_threat_intel_score(src_ip)

        # 2. Risk Calculation
        risk_score = RiskCalculator.calculate_risk(
            attack_type=attack_type,
            confidence=confidence,
            asset_criticality=asset_crit,
            threat_intel=threat_intel,
            packet_count=packet_count
        )

        # 3. Determine Severity and Priority based on Risk Score thresholds
        severity = "LOW"
        priority = "P4"
        if risk_score > 75:
            severity = "CRITICAL"
            priority = "P1"
        elif risk_score > 50:
            severity = "HIGH"
            priority = "P2"
        elif risk_score > 20:
            severity = "MEDIUM"
            priority = "P3"

        # 4. Playbook Selection
        playbook_data = PlaybookSelector.get_playbook(attack_type)

        # 5. Rule Engine (Automation Level)
        ctx = IncidentContext(
            attack_type=attack_type,
            confidence=confidence,
            risk_score=risk_score,
            asset_criticality=asset_crit,
            source_ip=src_ip
        )
        auto_level = self.rules_engine.evaluate(ctx)

        # 6. Formulate Output
        status = "OPEN"
        if auto_level == 5:
            status = "AUTO_MITIGATED"
        elif auto_level == 0:
            status = "DROPPED"

        return {
            "incident_id": f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
            "attack_type": attack_type,
            "confidence": confidence,
            "risk_score": risk_score,
            "severity": severity,
            "priority": priority,
            "recommended_action": playbook_data["action"],
            "playbook": playbook_data["playbook_id"],
            "automation_level": f"Level {auto_level}",
            "incident_status": status,
            "analyst_required": auto_level < 5,
            "generated_time": datetime.utcnow().isoformat()
        }

