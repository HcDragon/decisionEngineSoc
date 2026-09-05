from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class VerificationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    PENDING = "PENDING"

class VerificationResult(BaseModel):
    """
    Verification of whether a response action achieved its intended security outcome.
    Distinguishes execution success from security outcome success.
    """
    verification_id: str = Field(default_factory=lambda: f"VER-{uuid.uuid4().hex[:8]}")
    incident_id: str
    target: str
    status: VerificationStatus
    baseline_pps: float
    observed_pps: float
    reduction_percentage: float
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)
