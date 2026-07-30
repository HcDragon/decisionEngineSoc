class ThreatIntel:
    """
    Mock integration for a Threat Intelligence Platform.
    Returns reputation score on a scale of 0 to 100.
    100 = Known Malicious, 50 = Suspicious, 0 = Unknown/Safe.
    """
    def __init__(self):
        self.malicious_ips = {
            "203.0.113.50": 100,
            "198.51.100.22": 100
        }
        self.suspicious_ips = {
            "192.168.1.200": 50
        }

    def get_reputation(self, ip: str) -> int:
        if ip in self.malicious_ips:
            return 100
        elif ip in self.suspicious_ips:
            return 50
        return 0
