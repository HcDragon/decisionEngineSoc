from api.schemas import TrafficPrediction, DecisionResponse
from context.asset_db import AssetDB
from context.threat_intel import ThreatIntel
from intelligence.risk_calculator import RiskCalculator
from intelligence.policy_engine import PolicyEngine
from playbooks.selector import PlaybookSelector
from models.enums import IncidentStatus
import uuid

class DecisionManager:
    """
    Core orchestrator of the Smart SOC Manager Decision Engine.
    """
    def __init__(self):
        self.asset_db = AssetDB()
        self.threat_intel = ThreatIntel()
        self.risk_calc = RiskCalculator()
        self.policy = PolicyEngine()
        self.playbook_selector = PlaybookSelector()
        
    def process(self, prediction: TrafficPrediction) -> DecisionResponse:
        # Context Enrichment
        asset_crit = self.asset_db.get_criticality(prediction.flow_context.dest_ip)
        threat_score = self.threat_intel.get_reputation(prediction.flow_context.src_ip)
        
        # Adjust confidence scaling (assuming model returns 0.0 - 1.0)
        conf_val = prediction.confidence
        if conf_val > 1.0: # Fallback if model gives 0-100
            conf_val = conf_val / 100.0

        # Calculate Risk
        risk_score = self.risk_calc.calculate_risk(
            attack_type=prediction.attack_type,
            confidence=conf_val,
            asset_criticality=asset_crit,
            threat_intel_score=threat_score,
            packet_count=prediction.flow_context.packet_count
        )
        
        # Policy & Automation Level
        priority, severity, auto_lvl = self.policy.evaluate(risk_score, prediction.attack_type)
        
        # Select Playbook
        pb_id = self.playbook_selector.select(prediction.attack_type)
        
        # Determine incident status based on automation level
        if auto_lvl >= 4:
            status = IncidentStatus.AUTO_MITIGATED
            analyst_req = False
            rec_action = "Automatically Applied Playbook Mitigations."
        elif auto_lvl >= 2:
            status = IncidentStatus.PENDING_APPROVAL
            analyst_req = True
            rec_action = "Requires Analyst Approval to Execute Playbook."
        else:
            status = IncidentStatus.LOGGED
            analyst_req = False
            rec_action = "Logged. No Action Taken."
            
        return DecisionResponse(
            incident_id=f"INC-{str(uuid.uuid4())[:8]}",
            attack_type=prediction.attack_type,
            confidence=round(conf_val * 100, 2),
            risk_score=round(risk_score, 2),
            severity=severity,
            priority=priority,
            recommended_action=rec_action,
            playbook=pb_id,
            automation_level=auto_lvl,
            incident_status=status,
            analyst_required=analyst_req,
            src_ip=prediction.flow_context.src_ip
        )
