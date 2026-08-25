from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional
import uuid
from models.enums import AttackType, Severity, PlaybookID, IncidentStatus

class TrafficPrediction(BaseModel):
    timestamp: str
    attack_type: str
    confidence: float
    src_ip: str
    dest_ip: str
    src_port: int
    dest_port: int
    protocol: str
    packet_count: int
    flow_duration: float
    asset_criticality: Optional[str] = None
    historical_incidents: Optional[int] = 0

class DecisionResponse(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attack_type: str
    confidence: float
    risk_score: float
    severity: Severity
    priority: str
    policy_id: str
    recommended_action: str
    playbook: str
    actions: List[str]
    reasons: List[str]
    automation_level: int
    incident_status: IncidentStatus
    analyst_required: bool
    generated_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    src_ip: str
