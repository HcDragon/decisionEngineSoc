from pydantic import BaseModel, Field
from typing import List, Optional, Any
from enum import Enum
from datetime import datetime, timezone
import uuid

class DecisionType(str, Enum):
    ALLOW = "ALLOW"
    MONITOR = "MONITOR"
    LOG = "LOG"
    NOTIFY = "NOTIFY"
    RECOMMEND = "RECOMMEND"
    CONTAIN = "CONTAIN"
    ESCALATE = "ESCALATE"
    RESOLVE = "RESOLVE"

class AutomationLevel(int, Enum):
    LEVEL_0_LOG_ONLY = 0
    LEVEL_1_NOTIFY_ANALYST = 1
    LEVEL_2_RECOMMEND_RESPONSE = 2
    LEVEL_3_SEMI_AUTOMATIC = 3
    LEVEL_4_AUTOMATIC_WITH_NOTIFICATION = 4
    LEVEL_5_FULLY_AUTOMATED = 5

class SecurityDecision(BaseModel):
    """
    Final security decision produced by the Decision Manager.
    """
    decision_id: str = Field(default_factory=lambda: f"DEC-{uuid.uuid4().hex[:8]}")
    incident_id: str
    event_id: str
    decision: DecisionType
    risk_score: float
    severity: str
    policy_id: str
    playbook_id: str
    automation_level: int
    analyst_required: bool
    recommended_action: str
    actions: List[str]
    reasons: List[str]
    explanation: str
    src_ip: Optional[str] = None
    attack_type: Optional[str] = None
    incident_status: Optional[str] = "LOGGED"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)
