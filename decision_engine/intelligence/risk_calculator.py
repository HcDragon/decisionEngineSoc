class RiskCalculator:
    # Weights
    W1 = 0.35  # Severity
    W2 = 0.25  # Confidence
    W3 = 0.20  # Asset
    W4 = 0.10  # Intel
    W5 = 0.10  # Frequency

    SEVERITY_MAP = {
        "UDP Flood": 80,
        "SYN Flood": 90,
        "DoS SYN Flood": 90,
        "Brute Force": 70,
        "Dictionary Brute Force": 70,
        "Benign": 0,
        "Benign Traffic": 0,
        "DNS Flood": 85,
        "DoS DNS Flood": 85,
        "ICMP Flood": 60,
        "DoS ICMP Flood": 60,
        "DoS UDP Flood": 80
    }

    @classmethod
    def get_base_severity(cls, attack_type: str) -> float:
        return cls.SEVERITY_MAP.get(attack_type, 50.0)

    @classmethod
    def get_frequency_modifier(cls, packet_count: int) -> float:
        if packet_count > 1000:
            return 100.0
        elif packet_count > 500:
            return 50.0
        return 0.0

    @classmethod
    def calculate_risk(cls, attack_type: str, confidence: float, asset_criticality: float, threat_intel: float, packet_count: int = 0) -> float:
        base_severity = cls.get_base_severity(attack_type)
        freq_mod = cls.get_frequency_modifier(packet_count)

        risk = (cls.W1 * base_severity) + \
               (cls.W2 * confidence) + \
               (cls.W3 * asset_criticality) + \
               (cls.W4 * threat_intel) + \
               (cls.W5 * freq_mod)

        return min(risk, 100.0)
