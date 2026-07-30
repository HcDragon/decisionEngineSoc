class PolicyEngine:
    """
    Evaluates business logic thresholds to determine Priority, Severity Label, and Automation Level.
    """
    def evaluate(self, risk_score: float, attack_type: str):
        if risk_score <= 20:
            return "P4", "LOW", 0
        elif risk_score <= 50:
            return "P3", "MEDIUM", 1
        elif risk_score <= 75:
            # Check for specific rules like Brute Force semi-auto
            if attack_type == "Dictionary Brute Force":
                return "P2", "HIGH", 4
            return "P2", "HIGH", 2
        else:
            return "P1", "CRITICAL", 5
