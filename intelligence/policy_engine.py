import os
import yaml
from typing import Dict, Any, Tuple

class PolicyEngine:
    """
    Evaluates business logic thresholds against YAML policies to determine Action mapping.
    """
    def __init__(self, policies_dir: str = None):
        self.policies = []
        if policies_dir is None:
            # Locate project root dynamically
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidate = os.path.join(base_dir, "policies")
            if os.path.exists(candidate):
                policies_dir = candidate
            elif os.path.exists("policies"):
                policies_dir = "policies"
            else:
                policies_dir = "policies"
        self.load_policies(policies_dir)

    def load_policies(self, policies_dir: str):
        if not os.path.exists(policies_dir):
            return
        for filename in os.listdir(policies_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(policies_dir, filename)
                with open(filepath, "r") as f:
                    try:
                        policy = yaml.safe_load(f)
                        if policy.get("enabled", False):
                            self.policies.append(policy)
                    except Exception as e:
                        print(f"Error loading policy {filename}: {e}")

    def evaluate(self, risk_score: float, attack_type: str, confidence: float) -> Tuple[Dict, bool]:
        """
        Returns (Matched Policy Dict, bool: True if exact match else False (fallback))
        """
        # Find all matching policies
        matches = []
        for policy in self.policies:
            cond = policy.get("conditions", {})
            p_attack = cond.get("attack_type")
            p_min_conf = cond.get("min_confidence", 0.0)
            p_min_risk = cond.get("min_risk", 0.0)

            # Condition matching logic
            if p_attack and p_attack != attack_type:
                continue
            if confidence < p_min_conf:
                continue
            if risk_score < p_min_risk:
                continue
                
            matches.append(policy)

        if matches:
            # Sort matches by Priority (P1 > P2 > P3 etc)
            # Higher automation level could also be a tie-breaker.
            # Here we just pick the first one after sorting.
            matches.sort(key=lambda x: x.get("decision", {}).get("priority", "P4"))
            return matches[0], True
            
        # Fallback if no policy matches
        return {
            "policy_id": "DEFAULT-000",
            "name": "Default Fallback Policy",
            "decision": {
                "severity": "LOW",
                "priority": "P4",
                "automation_level": 1,
                "analyst_required": True
            },
            "playbook": {"id": "PB-DEFAULT"},
            "actions": ["NOTIFY_ANALYST", "REVIEW_REQUIRED"]
        }, False
