from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone
import uuid

class ActionType(str, Enum):
    LOG_EVENT = "LOG_EVENT"
    CREATE_INCIDENT = "CREATE_INCIDENT"
    NOTIFY_ANALYST = "NOTIFY_ANALYST"
    BLOCK_IP_SIMULATION = "BLOCK_IP_SIMULATION"
    RATE_LIMIT_SIMULATION = "RATE_LIMIT_SIMULATION"
    ICMP_FILTER_SIMULATION = "ICMP_FILTER_SIMULATION"
    RESET_CREDENTIALS_SIMULATION = "RESET_CREDENTIALS_SIMULATION"
    ISOLATE_HOST_SIMULATION = "ISOLATE_HOST_SIMULATION"
    MONITOR_SOURCE = "MONITOR_SOURCE"
    MONITOR_TRAFFIC = "MONITOR_TRAFFIC"
    VERIFY_MITIGATION = "VERIFY_MITIGATION"
    RESOLVE_OR_ESCALATE = "RESOLVE_OR_ESCALATE"
    ESCALATE_INCIDENT = "ESCALATE_INCIDENT"

class ActionStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WAITING_APPROVAL = "WAITING_APPROVAL"

class ExecutionMode(str, Enum):
    SIMULATION = "SIMULATION"
    LIVE = "LIVE"

class ActionResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:8]}")
    action: str
    target: str
    status: ActionStatus
    mode: ExecutionMode = ExecutionMode.SIMULATION
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)

class ActiveMitigationState(BaseModel):
    action_id: str
    incident_id: str
    action_type: str
    target: str
    status: str = "ACTIVE" # ACTIVE, EXPIRED, ROLLED_BACK
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    verification_required: bool = True
