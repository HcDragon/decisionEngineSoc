class AssetDB:
    """
    Mock integration for an Asset Database (CMDB).
    Returns criticality on a scale of 0 to 100.
    100 = Tier 1 Asset, 75 = Tier 2, 50 = Tier 3, 25 = Workstation.
    """
    def __init__(self):
        # Format: {IP: Criticality Score}
        self.assets = {
            "10.0.0.5": 100,  # Core Database
            "10.0.0.10": 75,  # Web Server
            "10.0.0.50": 25,  # Employee Desktop
        }

    def get_criticality(self, ip: str) -> int:
        # Default to 50 (medium importance) if not found
        return self.assets.get(ip, 50)
