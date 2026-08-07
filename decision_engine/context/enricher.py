# Mock databases
ASSET_DB = {
    "10.0.0.5": {"name": "Core Banking DB", "tier": 1, "criticality": 100},
    "10.0.0.10": {"name": "Internal Wiki", "tier": 3, "criticality": 50},
    "10.0.0.100": {"name": "Employee Laptop", "tier": 4, "criticality": 25},
}

THREAT_INTEL = {
    "192.168.1.100": {"reputation": "malicious", "score": 100},
    "203.0.113.5": {"reputation": "suspicious", "score": 50},
    "198.51.100.1": {"reputation": "unknown", "score": 0},
}

class ContextEnricher:
    @staticmethod
    def get_asset_criticality(ip: str) -> float:
        """Returns criticality score 0-100. Defaults to 25 if not found."""
        return ASSET_DB.get(ip, {}).get("criticality", 25.0)

    @staticmethod
    def get_threat_intel_score(ip: str) -> float:
        """Returns threat intel score 0-100. Defaults to 0 if not found."""
        return THREAT_INTEL.get(ip, {}).get("score", 0.0)
