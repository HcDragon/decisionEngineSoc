from pydantic import BaseModel, Field
from typing import List, Any
from enum import Enum

class RiskSeverity(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskFactorContribution(BaseModel):
    name: str
    raw_value: Any
    normalized_score: float # 0.0 - 100.0
    weight: float
    contribution: float     # normalized_score * weight
    explanation: str

class RiskAssessment(BaseModel):
    """
    Mathematical and explainable risk evaluation result.
    """
    risk_score: float = Field(..., ge=0.0, le=100.0)
    severity: RiskSeverity
    factors: List[RiskFactorContribution]
    summary_explanation: str
