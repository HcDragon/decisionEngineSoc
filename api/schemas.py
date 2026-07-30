from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
import uuid
from models.enums import AttackType, Severity, PlaybookID, IncidentStatus

class NetworkFlow(BaseModel):
    timestamp: str
    src_ip: str
    dest_ip: str
    src_port: int
    dest_port: int
    protocol: str
    packet_count: int
    flow_duration: float

class TrafficPrediction(BaseModel):
    attack_type: str
    confidence: float
    flow_context: NetworkFlow

class DecisionResponse(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attack_type: str
    confidence: float
    risk_score: float
    severity: Severity
    priority: str
    recommended_action: str
    playbook: PlaybookID
    automation_level: int
    incident_status: IncidentStatus
    analyst_required: bool
    generated_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    src_ip: str
