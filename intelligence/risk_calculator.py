from core.config import WEIGHT_SEVERITY, WEIGHT_CONFIDENCE, WEIGHT_ASSET, WEIGHT_INTEL, WEIGHT_FREQUENCY, BASE_SEVERITIES
from typing import Tuple, List

class RiskCalculator:
    def __init__(self):
        pass
        
    def map_criticality(self, asset_criticality) -> int:
        if isinstance(asset_criticality, int):
            return asset_criticality
        crit_str = str(asset_criticality).lower()
        if "critical" in crit_str or "tier 1" in crit_str: return 100
        if "high" in crit_str or "tier 2" in crit_str: return 75
        if "low" in crit_str or "workstation" in crit_str: return 25
        return 50 # Default Medium

    def calculate_risk(self, attack_type: str, confidence: float, asset_criticality, threat_intel_score: int, packet_count: int, historical_incidents: int = 0) -> Tuple[float, List[str]]:
        """
        Calculates Risk Score (0-100) based on mathematical formulation from SDD Chapter 6.
        Also returns explainable reasons.
        """
        reasons = []
        base_severity = BASE_SEVERITIES.get(attack_type, 50)
        if base_severity >= 80:
            reasons.append(f"High attack severity ({base_severity})")
            
        if confidence >= 0.90:
            reasons.append(f"High ML confidence ({confidence*100:.1f}%)")
            
        crit_val = self.map_criticality(asset_criticality)
        if crit_val >= 75:
            reasons.append(f"Target is a high-value/critical asset")
        
        if threat_intel_score > 0:
            reasons.append(f"Threat Intel reputation matched ({threat_intel_score})")
        
        # Frequency Modifier (0-100 based on packets and incidents)
        freq_mod = 0
        if historical_incidents > 5:
            freq_mod = 100
            reasons.append(f"Repeated historical incidents ({historical_incidents})")
        elif packet_count > 10000:
            freq_mod = 100
            reasons.append(f"High packet count ({packet_count})")
        elif historical_incidents > 0 or packet_count > 1000:
            freq_mod = 50
            
        risk = (
            (WEIGHT_SEVERITY * base_severity) +
            (WEIGHT_CONFIDENCE * (confidence * 100)) + 
            (WEIGHT_ASSET * crit_val) +
            (WEIGHT_INTEL * threat_intel_score) +
            (WEIGHT_FREQUENCY * freq_mod)
        )
        
        final_risk = min(max(risk, 0.0), 100.0) # Clamp between 0 and 100
        return final_risk, reasons
