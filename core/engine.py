from api.schemas import TrafficPrediction, DecisionResponse
from context.asset_db import AssetDB
from context.threat_intel import ThreatIntel
from intelligence.risk_calculator import RiskCalculator
from intelligence.policy_engine import PolicyEngine
from playbooks.selector import PlaybookSelector
from core.executor import SimulationExecutor
from models.enums import IncidentStatus
from datetime import datetime, timezone
from typing import Union, Dict, Any
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
        self.executor = SimulationExecutor()
        
    def process(self, prediction: TrafficPrediction) -> DecisionResponse:
        # Context Enrichment (Handling missing/optional fields)
        asset_crit = prediction.asset_criticality if prediction.asset_criticality else self.asset_db.get_criticality(prediction.dest_ip)
        threat_score = self.threat_intel.get_reputation(prediction.src_ip)
        
        # Adjust confidence scaling (assuming model returns 0.0 - 1.0)
        conf_val = prediction.confidence
        if conf_val > 1.0: # Fallback if model gives 0-100
            conf_val = conf_val / 100.0

        # Calculate Risk and get reasons
        risk_score, risk_reasons = self.risk_calc.calculate_risk(
            attack_type=prediction.attack_type,
            confidence=conf_val,
            asset_criticality=asset_crit,
            threat_intel_score=threat_score,
            packet_count=prediction.packet_count,
            historical_incidents=prediction.historical_incidents or 0
        )
        
        # Policy Evaluation
        policy_match, is_exact = self.policy.evaluate(risk_score, prediction.attack_type, conf_val)
        
        decision_info = policy_match.get("decision", {})
        priority = decision_info.get("priority", "P4")
        severity = decision_info.get("severity", "LOW")
        auto_lvl = decision_info.get("automation_level", 0)
        
        # Select Playbook & Actions
        playbook_id = policy_match.get("playbook", {}).get("id", "UNKNOWN")
        actions_list = policy_match.get("actions", [])
        
        # Reasons
        reasons = risk_reasons
        reasons.append(f"Policy '{policy_match.get('policy_id')}' matched" if is_exact else "No exact policy matched, used default fallback")
        
        # Determine incident status based on automation level
        if auto_lvl >= 5:
            status = IncidentStatus.AUTO_MITIGATED
            analyst_req = False
            rec_action = "Automatically Applied Playbook Mitigations."
            self.executor.execute_actions(actions_list, prediction.src_ip)
        elif auto_lvl >= 2:
            status = IncidentStatus.PENDING_APPROVAL
            analyst_req = True
            rec_action = "Requires Analyst Approval to Execute Playbook."
        else:
            status = IncidentStatus.LOGGED
            analyst_req = False
            rec_action = "Logged. No Action Taken."
            self.executor.execute_actions(["LOG_ONLY"], prediction.src_ip)
            
        return DecisionResponse(
            incident_id=f"INC-{str(uuid.uuid4())[:8]}",
            attack_type=prediction.attack_type,
            confidence=round(conf_val * 100, 2),
            risk_score=round(risk_score, 2),
            severity=severity,
            priority=priority,
            policy_id=policy_match.get("policy_id", "UNKNOWN"),
            recommended_action=rec_action,
            playbook=playbook_id,
            actions=actions_list,
            reasons=reasons,
            automation_level=auto_lvl,
            incident_status=status,
            analyst_required=analyst_req,
            src_ip=prediction.src_ip
        )

    def process_prediction(self, prediction: Union[Dict[str, Any], TrafficPrediction]) -> DecisionResponse:
        """
        Convenience method to process either a raw dictionary or a TrafficPrediction model.
        Supports standard dictionary keys like 'source_ip' / 'src_ip', 'destination_ip' / 'dest_ip'.
        """
        if isinstance(prediction, dict):
            src_ip = prediction.get("source_ip") or prediction.get("src_ip", "192.168.1.100")
            dest_ip = prediction.get("destination_ip") or prediction.get("dest_ip", "10.0.0.5")
            attack_type = prediction.get("attack_type", "Benign Traffic")
            if attack_type == "Benign":
                attack_type = "Benign Traffic"
            confidence = float(prediction.get("confidence", 95.0))
            packet_count = int(prediction.get("packet_count", 100))
            timestamp = prediction.get("timestamp", datetime.now(timezone.utc).isoformat())
            src_port = int(prediction.get("src_port", 0))
            dest_port = int(prediction.get("dest_port", 80))
            protocol = prediction.get("protocol", "TCP")
            flow_duration = float(prediction.get("flow_duration", 1.0))
            asset_crit = prediction.get("asset_criticality")
            hist_inc = prediction.get("historical_incidents", 0)

            prediction_obj = TrafficPrediction(
                timestamp=timestamp,
                attack_type=attack_type,
                confidence=confidence,
                src_ip=src_ip,
                dest_ip=dest_ip,
                src_port=src_port,
                dest_port=dest_port,
                protocol=protocol,
                packet_count=packet_count,
                flow_duration=flow_duration,
                asset_criticality=asset_crit,
                historical_incidents=hist_inc
            )
            return self.process(prediction_obj)
        return self.process(prediction)
