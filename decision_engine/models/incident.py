from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class IncidentState(str, Enum):
    DETECTED = "DETECTED"
    TRIAGING = "TRIAGING"
    RISK_ASSESSED = "RISK_ASSESSED"
    POLICY_MATCHED = "POLICY_MATCHED"
    RESPONSE_STARTED = "RESPONSE_STARTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    CONTAINED = "CONTAINED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"

class IncidentRecord(BaseModel):
    """
    Comprehensive stateful incident entity tracking the complete SOAR lifecycle.
    """
    model_config = {"extra": "ignore"}

    incident_id: str = Field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:8]}")
    event_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    source_ip: str
    destination_ip: str
    source_port: int = 0
    destination_port: int = 80
    protocol: str = "TCP"
    
    attack_type: str
    confidence: float
    risk_score: float = 0.0
    severity: str = "LOW"
    
    policy_id: str = "UNKNOWN"
    playbook_id: str = "UNKNOWN"
    automation_level: int = 0
    
    current_state: IncidentState = IncidentState.DETECTED
    incident_status: str = "LOGGED" # Backward compatibility alias
    recommended_action: str = ""
    
    actions_taken: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    event_count: int = 1 # Number of correlated/deduplicated threat events
    
    analyst_required: bool = False
    is_mitigated: bool = False
    
    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)
