from dataclasses import dataclass
from typing import Callable, List

@dataclass
class IncidentContext:
    attack_type: str
    confidence: float
    risk_score: float
    asset_criticality: float
    source_ip: str

@dataclass
class Rule:
    name: str
    condition: Callable[[IncidentContext], bool]
    automation_level: int
    priority: int  # Higher priority evaluated first

class RulesEngine:
    def __init__(self):
        self.rules: List[Rule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        # Whitelist override (Exception handling logic)
        self.add_rule(Rule(
            name="Whitelist Override",
            condition=lambda ctx: ctx.source_ip == "10.0.0.100", # Example whitelisted IP
            automation_level=1,
            priority=100
        ))
        
        # Level 0: Benign
        self.add_rule(Rule(
            name="Benign Traffic",
            condition=lambda ctx: "Benign" in ctx.attack_type,
            automation_level=0,
            priority=30
        ))

        # Level 5: High Confidence, High Risk, Non-Critical Asset
        self.add_rule(Rule(
            name="Fully Auto Block",
            condition=lambda ctx: ctx.confidence > 90 and ctx.risk_score > 80 and ctx.asset_criticality < 75,
            automation_level=5,
            priority=20
        ))

        # Level 4: High Confidence, High Risk, Critical Asset
        self.add_rule(Rule(
            name="Semi-Auto Block",
            condition=lambda ctx: ctx.confidence > 90 and ctx.risk_score > 80 and ctx.asset_criticality >= 75,
            automation_level=4,
            priority=20
        ))
        
        # Level 3: High Confidence, Low Risk
        self.add_rule(Rule(
            name="Recommend Action",
            condition=lambda ctx: ctx.confidence > 90 and ctx.risk_score <= 80,
            automation_level=3,
            priority=15
        ))
        
        # Level 2: Low Confidence
        self.add_rule(Rule(
            name="Notify Analyst",
            condition=lambda ctx: ctx.confidence <= 90,
            automation_level=2,
            priority=10
        ))

        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def add_rule(self, rule: Rule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(self, context: IncidentContext) -> int:
        for rule in self.rules:
            if rule.condition(context):
                return rule.automation_level
        
        return 1 # Default log only
