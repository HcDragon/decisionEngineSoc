from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PolicyConditions(BaseModel):
    attack_type: Optional[List[str]] = None
    confidence: Optional[Dict[str, float]] = None # {"minimum": 0.85}
    risk: Optional[Dict[str, float]] = None       # {"minimum": 70.0}

class PolicyDefinition(BaseModel):
    policy_id: str
    name: str
    description: Optional[str] = None
    enabled: bool = True
    priority: int = 50 # 100=Critical, 75=High, 50=Standard, 25=Monitor, 10=Fallback
    conditions: PolicyConditions = Field(default_factory=PolicyConditions)
    decision: str = "CONTAIN"
    severity: str = "HIGH"
    automation_level: int = 4
    playbook_id: str = "PB-DEFAULT"
    cooldown_seconds: int = 300
    notification_required: bool = True

class PolicyMatchResult(BaseModel):
    selected_policy: PolicyDefinition
    all_matched_policies: List[PolicyDefinition]
    selection_reason: str
