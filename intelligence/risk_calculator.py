from core.config import WEIGHT_SEVERITY, WEIGHT_CONFIDENCE, WEIGHT_ASSET, WEIGHT_INTEL, WEIGHT_FREQUENCY, BASE_SEVERITIES

class RiskCalculator:
    def __init__(self):
        pass

    def calculate_risk(self, attack_type: str, confidence: float, asset_criticality: int, threat_intel_score: int, packet_count: int) -> float:
        """
        Calculates Risk Score (0-100) based on mathematical formulation from SDD Chapter 6.
        """
        base_severity = BASE_SEVERITIES.get(attack_type, 50)
        
        # Frequency Modifier (0-100 based on packets)
        if packet_count > 10000:
            freq_mod = 100
        elif packet_count > 1000:
            freq_mod = 50
        else:
            freq_mod = 0
            
        risk = (
            (WEIGHT_SEVERITY * base_severity) +
            (WEIGHT_CONFIDENCE * (confidence * 100)) +  # Confidence is usually 0.0 to 1.0, wait, it's 0-100 in our inputs
            (WEIGHT_ASSET * asset_criticality) +
            (WEIGHT_INTEL * threat_intel_score) +
            (WEIGHT_FREQUENCY * freq_mod)
        )
        
        return min(max(risk, 0.0), 100.0) # Clamp between 0 and 100
